"""003 HTTP 契約：送出答案的端點（contracts/http-api.md）。"""

import pytest

from tests.conftest import create_activity, join_group, seed_questions, submit


@pytest.fixture
def opened(client):
    """版面 A（2,2,1,1）、第 1、2 組各一台裝置、已開第 1 輪（不倒數）。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    assert (
        client.post(
            f"/api/activities/{teacher.code}/open-joining",
            json={},
            headers=teacher.headers,
        ).status_code
        == 200
    )
    devices = {n: join_group(client, teacher.code, n) for n in (1, 2)}
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201, response.text
    return teacher, devices


def _assert_safe(response, *secrets):
    text = response.text
    assert "Traceback" not in text and "\\lecture_quiz\\" not in text
    assert "/lecture_quiz/" not in text
    for secret in secrets:
        assert secret not in text


def test_accepted_returns_201_without_sequence(client, opened):
    """Scenario: US1-AS1（接受：201 與提交內容，不含接收序號）。"""
    teacher, devices = opened
    response = submit(client, teacher.code, devices[1], 1, 2, ["乙一", "乙二"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["result"] == "accepted"
    sub = body["submission"]
    assert set(sub) == {
        "roundNumber",
        "questionNumber",
        "groupNumber",
        "answers",
        "receivedAt",
    }
    assert sub["roundNumber"] == 1 and sub["questionNumber"] == 2
    assert sub["groupNumber"] == 1
    assert sub["answers"] == ["乙一", "乙二"]
    assert sub["receivedAt"].startswith("2026-11-21T09:00:00")


@pytest.mark.parametrize(
    ("question", "answers", "code", "fragment"),
    [
        (1, ["甲"], "WRONG_BLANK_COUNT", "需要 2 格"),
        (1, ["甲", "  "], "BLANK_EMPTY", "第 2 格尚未填寫"),
        (3, ["字" * 501], "ANSWER_TOO_LONG", "第 1 格超過 500 字"),
        (9, ["甲"], "QUESTION_NOT_OPEN", "不在本輪"),
        (3, "丙", "INVALID_ANSWER", "答案格式不正確"),
    ],
)
def test_invalid_content_is_400(client, opened, question, answers, code, fragment):
    """Scenario: US1-AS3、US1-AS4、US1-AS5（無效內容回 400，訊息可修正；SC-007）。"""
    teacher, devices = opened
    response = submit(client, teacher.code, devices[1], 1, question, answers)
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert fragment in error["message"]
    _assert_safe(response, devices[1], teacher.token)


@pytest.mark.parametrize(
    "body",
    [
        [1, 2],
        "text",
        {"roundNumber": 1, "questionNumber": 1},
        {"roundNumber": 1, "answers": ["a"]},
        {"questionNumber": 1, "answers": ["a"]},
    ],
)
def test_malformed_body_is_invalid_request(client, opened, body):
    teacher, devices = opened
    response = client.post(
        f"/api/activities/{teacher.code}/submissions",
        json=body,
        headers={"Authorization": f"Bearer {devices[1]}"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    _assert_safe(response, devices[1])


def test_not_in_group_and_gone(client, opened, manual_scheduler, fake_clock):
    """Edge：「不是學生裝置的請求」「活動已失效」（G1；SC-007）。"""
    teacher, devices = opened
    for headers in (
        {},
        {"Authorization": "Bearer not-a-token"},
        teacher.headers,
    ):
        response = client.post(
            f"/api/activities/{teacher.code}/submissions",
            json={"roundNumber": 1, "questionNumber": 3, "answers": ["丙"]},
            headers=headers,
        )
        assert response.status_code == 403, headers
        assert response.json()["error"]["code"] == "NOT_IN_GROUP"
        _assert_safe(response, teacher.token)

    from fastapi.testclient import TestClient

    from tests.conftest import make_app

    with TestClient(make_app(fake_clock, manual_scheduler)) as restarted:
        response = submit(restarted, teacher.code, devices[1], 1, 3, ["丙"])
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "ACTIVITY_GONE"
    _assert_safe(response, devices[1])
