"""T033：組別加入端點的契約（contracts/http-api.md #3）。"""

from tests.conftest import create_activity


def _join(client, code, body, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(
        f"/api/activities/{code}/groups/join", json=body, headers=headers
    )


def test_join_returns_device_token_number_credential_version(client):
    teacher = create_activity(client)
    response = _join(client, teacher.code, {"groupNumber": 3})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"deviceToken", "groupNumber", "credential", "version"}
    assert body["groupNumber"] == 3
    assert len(body["credential"]) == 6
    assert len(body["deviceToken"]) >= 40
    # 加入組別不改變學生可見的狀態，version 不變（FR-030）
    assert body["version"] == 1


def test_code_is_case_and_space_insensitive(client):
    teacher = create_activity(client)
    response = _join(client, f" {teacher.code.lower()} ", {"groupNumber": "1"})
    assert response.status_code == 200


def test_unknown_code_without_token_is_404(client):
    response = _join(client, "ZZZZZZ", {"groupNumber": 1})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_device_already_in_group_gets_409(client):
    teacher = create_activity(client)
    token = _join(client, teacher.code, {"groupNumber": 1}).json()["deviceToken"]
    again = _join(client, teacher.code, {"groupNumber": 2}, token=token)
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "ALREADY_IN_GROUP"
    assert "請先離開本組" in error["message"]


def test_errors_do_not_leak_credentials(client):
    teacher = create_activity(client)
    first = _join(client, teacher.code, {"groupNumber": 1}).json()
    wrong = _join(client, teacher.code, {"groupNumber": 1, "credential": "XXXXXX"})
    assert wrong.status_code == 403
    assert wrong.json()["error"]["code"] == "BAD_CREDENTIAL"
    assert first["credential"] not in wrong.text
    invalid = _join(client, teacher.code, {"groupNumber": 99})
    assert invalid.status_code == 400
    assert invalid.json()["error"] == {
        "code": "INVALID_GROUP_NUMBER",
        "message": "組號須為 1～6 的整數。",
    }
