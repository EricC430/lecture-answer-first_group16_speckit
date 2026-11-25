"""T033：組別加入端點的契約（contracts/http-api.md #3；007 修訂見
specs/007-browser-identity-sync/contracts/http-and-sync-changes.md §3）。"""

from tests.conftest import create_joinable, new_browser_client, post_join

SESSION_REQUIRED_MESSAGE = "瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。"


def _join(client, code, body, token=None):
    """以瀏覽器金鑰（Bearer 路徑）加入；`token` 為 None 時模擬新瀏覽器。"""
    response, _ = post_join(client, code, body, token)
    return response


def test_join_returns_number_credential_version_without_token(client):
    """007 contracts §3：成功回應不含 deviceToken，也不設定 cookie。"""
    teacher = create_joinable(client)
    response = _join(client, teacher.code, {"groupNumber": 3})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"groupNumber", "credential", "version"}
    assert body["groupNumber"] == 3
    assert len(body["credential"]) == 6
    assert response.headers.get_list("set-cookie") == []
    # 加入組別不改變學生可見的狀態，version 不變（FR-030）
    assert body["version"] == 3


def test_join_by_cookie_without_bearer(client):
    """007：學生頁實際走的 cookie 路徑（不帶 Bearer）可以加入。"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    response = browser.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 2}
    )
    assert response.status_code == 200, response.text
    assert "deviceToken" not in response.json()


def test_join_without_browser_key_is_rejected_without_change(client):
    """007 FR-013：沒有 cookie 也沒有 Bearer 時回 BROWSER_SESSION_REQUIRED。"""
    teacher = create_joinable(client)
    client.cookies.clear()
    response = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 1}
    )
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "BROWSER_SESSION_REQUIRED",
        "message": SESSION_REQUIRED_MESSAGE,
    }
    snapshot = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()
    assert snapshot["groups"] == []


def test_code_is_case_and_space_insensitive(client):
    teacher = create_joinable(client)
    response = _join(client, f" {teacher.code.lower()} ", {"groupNumber": "1"})
    assert response.status_code == 200


def test_unknown_code_without_token_is_404(client):
    response = _join(client, "ZZZZZZ", {"groupNumber": 1})
    # Bearer 帶的是瀏覽器金鑰；加入端點判斷 404／410 時，瀏覽器金鑰不算「曾經有身分」
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_unknown_code_with_cookie_is_404(client):
    """007 research R4：帶著 cookie 打錯代碼，仍是「找不到」而不是「已失效」。"""
    browser = new_browser_client(client)
    response = browser.post(
        "/api/activities/ZZZZZZ/groups/join", json={"groupNumber": 1}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_device_already_in_group_gets_409(client):
    teacher = create_joinable(client)
    response, token = post_join(client, teacher.code, {"groupNumber": 1})
    assert response.status_code == 200
    again = _join(client, teacher.code, {"groupNumber": 2}, token=token)
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "ALREADY_IN_GROUP"
    assert error["message"] == "這個瀏覽器已是第 1 組成員，請先離開本組。"


def test_errors_do_not_leak_credentials(client):
    teacher = create_joinable(client)
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
