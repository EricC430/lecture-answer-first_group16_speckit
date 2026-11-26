"""T034：US2 學生以組號加入，多裝置同組並可恢復身分。"""

from tests.conftest import create_joinable, post_join


class _Joined:
    """加入回應；成功時 `json()` 另含 `browserKey`（這個瀏覽器的金鑰，Bearer 路徑）。"""

    def __init__(self, response, key):
        self._response = response
        self.status_code = response.status_code
        self.text = response.text
        self._key = key

    def json(self):
        body = self._response.json()
        if self.status_code == 200:
            body = {**body, "browserKey": self._key}
        return body


def _join(client, code, number, credential=None, token=None):
    """`token` 為 None 時模擬新瀏覽器；否則以該瀏覽器金鑰再加入（007）。"""
    body = {"groupNumber": number, "credential": credential}
    response, key = post_join(client, code, body, token)
    return _Joined(response, key)


def _snapshot(client, code, token):
    return client.get(
        f"/api/activities/{code}/snapshot", headers={"Authorization": f"Bearer {token}"}
    )


def test_join_with_fullwidth_number_creates_group(client):
    """Scenario: US2-AS1

    組號「 ０３ 」建立第 3 組，裝置取得第 3 組身分與 6 碼憑證。
    """
    teacher = create_joinable(client)
    body = _join(client, teacher.code, " ０３ ").json()
    assert body["groupNumber"] == 3
    snap = _snapshot(client, teacher.code, body["browserKey"]).json()
    assert snap["role"] == "student"
    assert snap["ownGroup"] == {
        "number": 3,
        "credential": body["credential"],
        "successCount": 0,
    }


def test_second_device_with_credential_shares_group(client):
    """Scenario: US2-AS2

    第二台裝置附上第一台畫面上的憑證加入，兩台快照的 ownGroup 相同，不建立第二組。
    """
    teacher = create_joinable(client)
    first = _join(client, teacher.code, 3).json()
    second = _join(client, teacher.code, 3, first["credential"]).json()
    snaps = [
        _snapshot(client, teacher.code, j["browserKey"]).json()["ownGroup"]
        for j in (first, second)
    ]
    assert snaps[0] == snaps[1]
    groups = _snapshot(client, teacher.code, teacher.token).json()["groups"]
    assert [(g["number"], g["deviceCount"]) for g in groups] == [(3, 2)]


def test_credentials_visible_to_own_group_and_teacher_only(client):
    """Scenario: US2-AS3

    本組裝置看得到本組憑證；其他組看不到；老師看得到每一組憑證。
    """
    teacher = create_joinable(client)
    a = _join(client, teacher.code, 3).json()
    b = _join(client, teacher.code, 2).json()
    b_snap = _snapshot(client, teacher.code, b["browserKey"])
    assert a["credential"] not in b_snap.text
    groups = _snapshot(client, teacher.code, teacher.token).json()["groups"]
    assert {g["number"]: g["credential"] for g in groups} == {
        2: b["credential"],
        3: a["credential"],
    }


def test_existing_number_without_credential_is_rejected(client):
    """Scenario: US2-AS4

    既有組號不附憑證時拒絕，訊息提示向同組同學查看憑證，不含憑證，不建立新組。
    """
    teacher = create_joinable(client)
    first = _join(client, teacher.code, 3).json()
    response = _join(client, teacher.code, 3)
    assert response.status_code == 403
    message = response.json()["error"]["message"]
    assert "向同組同學查看本組加入憑證" in message
    assert first["credential"] not in response.text
    groups = _snapshot(client, teacher.code, teacher.token).json()["groups"]
    assert [(g["number"], g["deviceCount"]) for g in groups] == [(3, 1)]


def test_invalid_code_number_or_credential_changes_nothing(client):
    """Scenario: US2-AS5

    不存在的代碼、超出範圍或格式錯誤的組號、錯誤憑證都被拒絕，組別資料不變。
    """
    teacher = create_joinable(client)
    first = _join(client, teacher.code, 1).json()
    before = _snapshot(client, teacher.code, teacher.token).json()
    assert _join(client, "ZZZZZZ", 1).status_code == 404
    for raw in ("", 0, 7, -1, 2.5, "三"):
        response = _join(client, teacher.code, raw)
        assert response.status_code == 400, raw
        assert response.json()["error"]["message"] == "組號須為 1～6 的整數。"
    wrong = _join(client, teacher.code, 1, "WRONG1")
    assert wrong.status_code == 403
    assert first["credential"] not in wrong.text
    after = _snapshot(client, teacher.code, teacher.token).json()
    assert after["groups"] == before["groups"]
    assert after["version"] == before["version"]


def test_join_rejected_after_cancel(client):
    """Scenario: US2-AS6

    活動已取消時加入被拒，訊息說明活動已取消。
    """
    teacher = create_joinable(client)
    client.post(
        f"/api/activities/{teacher.code}/cancel", json={}, headers=teacher.headers
    )
    response = _join(client, teacher.code, 1)
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "活動已取消，無法加入。"


def test_join_during_round_sees_current_stage(client):
    """Scenario: US2-AS7

    搶答中新組加入，立即看到搶答中與開放題目，成功次數為零。
    """
    teacher = create_joinable(client)
    client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": [1, 2]},
        headers=teacher.headers,
    )
    body = _join(client, teacher.code, 4).json()
    snap = _snapshot(client, teacher.code, body["browserKey"]).json()
    assert snap["stage"] == "ROUND_OPEN"
    assert snap["openQuestions"] == [1, 2]
    assert snap["ownGroup"]["successCount"] == 0


def test_identity_restored_over_websocket(client):
    """Scenario: US2-AS8

    以同一個裝置 token 重新連 WebSocket（模擬重新整理），取得原組別與憑證。
    """
    teacher = create_joinable(client)
    body = _join(client, teacher.code, 3).json()
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": body["browserKey"]})
        snap = ws.receive_json()
    assert snap["ownGroup"]["number"] == 3
    assert snap["ownGroup"]["credential"] == body["credential"]


def test_member_device_cannot_join_again(client):
    """Scenario: US2-AS9

    已在第 3 組的裝置再加入時回 409「請先離開本組」，身分不變。
    """
    teacher = create_joinable(client)
    body = _join(client, teacher.code, 3).json()
    again = _join(client, teacher.code, 2, token=body["browserKey"])
    assert again.status_code == 409
    assert (
        again.json()["error"]["message"] == "這個瀏覽器已是第 3 組成員，請先離開本組。"
    )
    snap = _snapshot(client, teacher.code, body["browserKey"]).json()
    assert snap["ownGroup"]["number"] == 3
