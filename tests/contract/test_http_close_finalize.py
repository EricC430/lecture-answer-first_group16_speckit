"""T054：關輪與定案端點契約（contracts/http-api.md #7、#8）。"""

from tests.conftest import seed_questions


def _open(client, teacher):
    seed_questions(client, teacher)
    client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )


def test_close_contract_and_already_closed(client, teacher):
    _open(client, teacher)
    first = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close", headers=teacher.headers
    )
    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"roundNumber", "version", "alreadyClosed"}
    assert body["alreadyClosed"] is False
    second = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close", headers=teacher.headers
    )
    assert second.status_code == 200
    assert second.json() == {
        "roundNumber": body["roundNumber"],
        "version": body["version"],
        "alreadyClosed": True,
    }


def test_finalize_contract(client, teacher):
    _open(client, teacher)
    closed = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close", headers=teacher.headers
    ).json()
    response = client.post(
        f"/api/activities/{teacher.code}/rounds/current/finalize",
        json={},
        headers=teacher.headers,
    )
    assert response.status_code == 200
    assert response.json() == {"version": closed["version"] + 1}


def test_close_without_round_is_409(client, teacher):
    response = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close", headers=teacher.headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "目前沒有進行中的輪次。"


def test_finalize_during_round_is_409(client, teacher):
    _open(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds/current/finalize",
        headers=teacher.headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "請先關輪，再確認定案。"
