"""T061：US6 所有畫面同步、斷線與重啟有明確提示。"""

import json

from fastapi.testclient import TestClient

from tests.conftest import (
    FakeClock,
    ManualScheduler,
    join_group,
    make_app,
    seed_questions,
)


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    first = ws.receive_json()
    return ctx, ws, first


def _post(client, teacher, path, body=None):
    return client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )


def test_close_reaches_all_three_pages_with_same_version(client, teacher):
    """Scenario: US6-AS1

    老師與兩組共 3 條連線；關輪後都收到相同的 version 與 roundNumber，且有 changedAt。
    """
    seed_questions(client, teacher)
    a = join_group(client, teacher.code, 1)
    b = join_group(client, teacher.code, 2)
    _post(client, teacher, "/rounds", {"questionNumbers": [1, 2]})
    conns = [_connect(client, teacher.code, t) for t in (teacher.token, a, b)]
    try:
        closed = _post(client, teacher, "/rounds/current/close").json()
        snaps = [ws.receive_json() for _, ws, _ in conns]
    finally:
        for ctx, _, _ in conns:
            ctx.__exit__(None, None, None)
    assert {s["version"] for s in snaps} == {closed["version"]}
    assert {s["roundNumber"] for s in snaps} == {1}
    assert {s["stage"] for s in snaps} == {"RESULT_PENDING"}
    assert all(s["changedAt"] for s in snaps)


class _BrokenSocket:
    async def send_json(self, message):
        raise ConnectionResetError("模擬斷線")

    async def close(self, code=1000):
        pass


def test_failed_connection_does_not_affect_others(client, teacher):
    """Scenario: US6-AS2

    某條連線推送失敗時，只關閉那條連線；其他連線照常收到更新，狀態照常變更。
    （前端「同步中斷」畫面由 quickstart 第 17 步人工驗證。）
    """
    from lecture_quiz.adapters.web.ws_sync import _Connection
    from lecture_quiz.app.activity.secrets_gen import hash_token
    from lecture_quiz.core.activity.commands import Device

    seed_questions(client, teacher)
    device = join_group(client, teacher.code, 1)
    hub = client.app.state.sync_hub
    ctx, ws, _ = _connect(client, teacher.code, teacher.token)
    try:
        broken = _Connection(_BrokenSocket(), Device(hash_token(device)))
        hub._connections[teacher.code].add(broken)
        response = _post(client, teacher, "/rounds", {})
        assert response.status_code == 201
        assert ws.receive_json()["stage"] == "ROUND_OPEN"
        assert broken not in hub._connections[teacher.code]
        assert hub.connection_count(teacher.code) == 1
    finally:
        ctx.__exit__(None, None, None)


def test_reconnect_gets_latest_snapshot_first(client, teacher):
    """Scenario: US6-AS3

    斷線期間發生變更，重連後第一則 snapshot 就是最新版本。
    """
    seed_questions(client, teacher)
    device = join_group(client, teacher.code, 1)
    ctx, _, first = _connect(client, teacher.code, device)
    ctx.__exit__(None, None, None)  # 斷線
    opened = _post(client, teacher, "/rounds", {}).json()
    ctx, _, latest = _connect(client, teacher.code, device)
    ctx.__exit__(None, None, None)
    assert latest["version"] == opened["version"] > first["version"]
    assert latest["stage"] == "ROUND_OPEN"


def test_restart_makes_old_identities_gone(client, teacher):
    """Scenario: US6-AS4

    後端重啟（建立新的 app）後，舊老師 token 與舊裝置 token 的 WebSocket 都收到 gone，
    HTTP snapshot 回 410，不顯示任何舊資料（SC-007）。
    """
    device = join_group(client, teacher.code, 1)
    with TestClient(make_app(FakeClock(), ManualScheduler())) as restarted:
        for token in (teacher.token, device):
            with restarted.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
                ws.send_json({"type": "auth", "token": token})
                assert ws.receive_json() == {"type": "gone"}
            response = restarted.get(
                f"/api/activities/{teacher.code}/snapshot",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 410
            assert (
                response.json()["error"]["message"]
                == "活動已失效，請重新建立或加入活動。"
            )
            assert "ownGroup" not in response.text
        stale = restarted.post(
            f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
        )
        assert stale.status_code == 410


def test_student_messages_never_contain_other_groups(client, teacher):
    """Scenario: US6-AS5

    搶答中學生收到的每一則訊息與回應，都不含其他組的組號、憑證、提交狀態或組別清單（SC-009）。
    """
    seed_questions(client, teacher)
    mine = join_group(client, teacher.code, 1)
    ctx, ws, first = _connect(client, teacher.code, mine)
    try:
        received = [first]
        join_group(client, teacher.code, 2)
        received.append(ws.receive_json())
        _post(client, teacher, "/rounds", {})
        received.append(ws.receive_json())
        received.append(
            client.get(
                f"/api/activities/{teacher.code}/snapshot",
                headers={"Authorization": f"Bearer {mine}"},
            ).json()
        )
    finally:
        ctx.__exit__(None, None, None)
    assert received[-2]["stage"] == "ROUND_OPEN"
    teacher_view = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()
    other_credential = teacher_view["groups"][1]["credential"]
    for message in received:
        text = json.dumps(message, ensure_ascii=False)
        assert other_credential not in text
        assert "groups" not in message
        assert "hasSubmissions" not in text
        assert "deviceCount" not in text
        assert message["ownGroup"]["number"] == 1
