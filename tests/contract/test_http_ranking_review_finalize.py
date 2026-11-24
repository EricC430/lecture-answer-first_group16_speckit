"""US6：`POST .../rounds/current/finalize` 的 HTTP 契約。"""

import pytest

from tests.integration.ranking_world import answer, close_round, open_ranking_round


def _post(client, teacher, body, headers=None):
    return client.post(
        f"/api/activities/{teacher.code}/rounds/current/finalize",
        json=body,
        headers=headers if headers is not None else teacher.headers,
    )


def _closed(client):
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    answer(client, teacher, devices, 1, 1)
    close_round(client, teacher)
    return teacher, devices


def test_finalize_success_and_repeat(client):
    teacher, _ = _closed(client)
    first = _post(client, teacher, {"resultVersion": 1})
    assert first.status_code == 200
    body = first.json()
    assert body["resultVersion"] == 1 and body["alreadyFinalized"] is False
    assert isinstance(body["version"], int)
    again = _post(client, teacher, {"resultVersion": 1})
    assert again.status_code == 200 and again.json()["alreadyFinalized"] is True


@pytest.mark.parametrize(
    "body", [{}, {"resultVersion": "1"}, {"resultVersion": 1.5}, [], None]
)
def test_bad_body_is_400(client, body):
    teacher, _ = _closed(client)
    response = _post(client, teacher, body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_error_codes(client):
    teacher, devices = _closed(client)
    student = {"Authorization": f"Bearer {devices[1]}"}
    r = _post(client, teacher, {"resultVersion": 1}, headers=student)
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_TEACHER"
    r = _post(client, teacher, {"resultVersion": 7})
    assert r.status_code == 409 and r.json()["error"]["code"] == "STALE_RESULT_VERSION"
    _post(client, teacher, {"resultVersion": 1})
    r = _post(client, teacher, {"resultVersion": 7})
    assert r.status_code == 409 and r.json()["error"]["code"] == "RESULT_ALREADY_FINAL"


def test_round_still_open(client):
    teacher, devices = open_ranking_round(client, groups=(1,), questions=1)
    r = _post(client, teacher, {"resultVersion": 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "ROUND_STILL_OPEN"


def test_only_one_finalize_handler_registered(client):
    paths = client.app.openapi()["paths"]
    matches = [p for p in paths if p.endswith("/rounds/current/finalize")]
    assert len(matches) == 1
