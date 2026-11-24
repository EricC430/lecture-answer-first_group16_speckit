"""US4：`PUT .../judgement` 的 HTTP 契約（contracts/http-api.md）。"""

import pytest

from tests.conftest import create_activity
from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
)


def _put(client, teacher, round_number, question, group, body, headers=None):
    return client.put(
        f"/api/activities/{teacher.code}/rounds/{round_number}/questions/"
        f"{question}/groups/{group}/judgement",
        json=body,
        headers=headers if headers is not None else teacher.headers,
    )


def _closed(client):
    teacher, devices = open_ranking_round(client, groups=(1, 2, 3), questions=2)
    answer(client, teacher, devices, 1, 1)
    answer(client, teacher, devices, 2, 1)
    close_round(client, teacher)
    return teacher, devices


def test_mark_wrong_returns_changed_version_and_affected(client):
    """Scenario: US4-AS8（本文多送 reason 被忽略）。"""
    teacher, _ = _closed(client)
    response = _put(client, teacher, 1, 1, 1, {"wrong": True, "reason": "不需要"})
    assert response.status_code == 200
    assert response.json() == {
        "changed": True,
        "resultVersion": 2,
        "affectedQuestions": [1],
    }
    again = _put(client, teacher, 1, 1, 1, {"wrong": True})
    assert again.json() == {
        "changed": False,
        "resultVersion": 2,
        "affectedQuestions": [],
    }


def test_non_winner_can_be_judged_through_api(client):
    """Scenario: US4-AS9 的 API 部分（API 不限於目前的搶答成功者）。"""
    teacher, _ = _closed(client)
    assert _put(client, teacher, 1, 1, 2, {"wrong": True}).status_code == 200


@pytest.mark.parametrize(
    "body",
    [None, [], {}, {"wrong": "true"}, {"wrong": 1}, {"wrong": None}],
)
def test_bad_body_is_invalid_request(client, body):
    """本文不是物件、缺 wrong、wrong 不是布林 → 400。"""
    teacher, _ = _closed(client)
    response = _put(client, teacher, 1, 1, 1, body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    "path",
    [
        "0/questions/1/groups/1",
        "1/questions/-1/groups/1",
        "1/questions/1/groups/0",
        "x/questions/1/groups/1",
    ],
)
def test_bad_path_numbers_are_invalid_request(client, path):
    """路徑上的輪次、題號、組號不是正整數 → 400。"""
    teacher, _ = _closed(client)
    response = client.put(
        f"/api/activities/{teacher.code}/rounds/{path}/judgement",
        json={"wrong": True},
        headers=teacher.headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_error_codes_and_statuses(client):
    """錯誤碼與狀態逐列照契約。"""
    teacher, devices = _closed(client)
    student = {"Authorization": f"Bearer {devices[1]}"}
    cases = [
        (
            _put(client, teacher, 1, 1, 1, {"wrong": True}, headers=student),
            403,
            "NOT_TEACHER",
        ),
        (
            _put(client, teacher, 1, 1, 1, {"wrong": True}, headers={}),
            403,
            "NOT_TEACHER",
        ),
        (_put(client, teacher, 9, 1, 1, {"wrong": True}), 404, "ROUND_NOT_FOUND"),
        (_put(client, teacher, 1, 2, 1, {"wrong": True}), 404, "SUBMISSION_NOT_FOUND"),
    ]
    for response, status, code in cases:
        assert response.status_code == status, response.text
        error = response.json()["error"]
        assert error["code"] == code
        for forbidden in ("Traceback", ".py", teacher.token):
            assert forbidden not in error["message"]


def test_unknown_activity_404_without_token_410_with_token(client):
    """活動不存在：不帶 token 404、帶 token 410。"""
    body = {"wrong": True}
    url = "/api/activities/ZZZ999/rounds/1/questions/1/groups/1/judgement"
    assert client.put(url, json=body).status_code == 404
    gone = client.put(url, json=body, headers={"Authorization": "Bearer abc"})
    assert gone.status_code == 410
    assert gone.json()["error"]["code"] == "ACTIVITY_GONE"


def test_round_still_open_and_no_round(client):
    """搶答中 409 ROUND_STILL_OPEN；還沒有輪次 409 NO_ROUND。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    answer(client, teacher, devices, 1, 1)
    open_response = _put(client, teacher, 1, 1, 1, {"wrong": True})
    assert open_response.status_code == 409
    assert open_response.json()["error"]["code"] == "ROUND_STILL_OPEN"
    fresh = create_activity(client)
    none = _put(client, fresh, 1, 1, 1, {"wrong": True})
    assert none.status_code == 409 and none.json()["error"]["code"] == "NO_ROUND"
