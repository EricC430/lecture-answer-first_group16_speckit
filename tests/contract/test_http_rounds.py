"""T044：開輪端點契約（contracts/http-api.md #6）。"""

from tests.conftest import seed_questions


def test_open_round_returns_201_contract(client, teacher):
    seed_questions(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": [1, 2], "fairMode": False, "countdownSeconds": 60},
        headers=teacher.headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"roundNumber", "deadline", "version"}
    assert body["roundNumber"] == 1
    assert body["deadline"] == "2026-11-21T09:01:00+08:00"
    assert body["version"] == 3


def test_open_round_without_countdown_has_null_deadline(client, teacher):
    seed_questions(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201
    assert response.json()["deadline"] is None


def test_fractional_countdown_is_invalid_countdown(client, teacher):
    seed_questions(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"countdownSeconds": 2.5},
        headers=teacher.headers,
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_COUNTDOWN"
    assert error["message"] == "倒數秒數須為 1～3600 的整數。"


def test_malformed_body_is_invalid_request(client, teacher):
    seed_questions(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": "1,2"},
        headers=teacher.headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "questionNumbers" in response.json()["error"]["message"]


def test_no_questions_is_409(client, teacher):
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "請先成功匯入學習單，再開始搶答。"
