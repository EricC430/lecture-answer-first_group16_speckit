"""T060：WebSocket 同步契約（contracts/sync-websocket.md）。"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import (
    FakeClock,
    ManualScheduler,
    create_activity,
    create_joinable,
    join_group,
    make_app,
    new_browser_client,
)

COMMON_FIELDS = {
    "type",
    "role",
    "code",
    "version",
    "changedAt",
    "stage",
    "roundNumber",
    "openQuestions",
    "deadline",
    "fairMode",
    "unsolvedQuestions",
}


@pytest.fixture
def fast_client():
    app = make_app(
        FakeClock(), ManualScheduler(), ws_auth_timeout=0.3, ws_ping_interval=0.2
    )
    with TestClient(app) as c:
        yield c


def _connect(client, code, token):
    ws = client.websocket_connect(f"/ws/activities/{code}")
    session = ws.__enter__()
    session.send_json({"type": "auth", "token": token})
    return ws, session


def _close_code(session):
    with pytest.raises(WebSocketDisconnect) as exc:
        session.receive_json()
    return exc.value.code


def test_teacher_receives_snapshot_with_teacher_fields(client):
    teacher = create_activity(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": teacher.token})
        snap = ws.receive_json()
    assert COMMON_FIELDS <= set(snap)
    assert set(snap) == COMMON_FIELDS | {
        "groups",
        "maxGroups",
        "questionNumbers",
        "revision",
    }
    assert snap["role"] == "teacher"
    assert snap["version"] == 1


def test_student_receives_only_own_group(client):
    teacher = create_joinable(client)
    device = join_group(client, teacher.code, 1)
    join_group(client, teacher.code, 2)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": device})
        snap = ws.receive_json()
    assert set(snap) == COMMON_FIELDS | {"ownGroup"}
    assert snap["role"] == "student"
    own = snap["ownGroup"]
    assert set(own) == {"number", "credential", "successCount"}
    assert own["number"] == 1 and own["successCount"] == 0
    assert "groups" not in snap


def test_first_message_must_be_auth(client):
    teacher = create_activity(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "hello"})
        assert _close_code(ws) == 4400


def test_missing_auth_within_timeout_closes(fast_client):
    teacher = create_activity(fast_client)
    with fast_client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        assert _close_code(ws) == 4408


def test_ping_is_sent_periodically(fast_client):
    teacher = create_activity(fast_client)
    with fast_client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": teacher.token})
        assert ws.receive_json()["type"] == "snapshot"
        assert ws.receive_json() == {"type": "ping"}


def test_unknown_activity_gets_gone_and_4410(client):
    with client.websocket_connect("/ws/activities/ZZZZZZ") as ws:
        ws.send_json({"type": "auth", "token": "whatever"})
        assert ws.receive_json() == {"type": "gone"}
        assert _close_code(ws) == 4410


def test_invalid_token_gets_unauthorized_and_4401(client):
    teacher = create_activity(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": "not-a-real-token"})
        assert ws.receive_json() == {"type": "unauthorized", "reason": "INVALID_TOKEN"}
        assert _close_code(ws) == 4401


def test_state_change_is_pushed_and_extra_messages_ignored(client, caplog):
    teacher = create_joinable(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": teacher.token})
        assert ws.receive_json()["version"] == 3
        ws.send_json({"type": "auth", "token": "ignored-after-auth"})
        join_group(client, teacher.code, 1)
        snap = ws.receive_json()
    # 老師收到新快照：version 不變（學生不可見的變更），revision 加 1（FR-030）
    assert snap["version"] == 3
    assert snap["revision"] == 4
    assert [g["number"] for g in snap["groups"]] == [1]
    assert any("多餘訊息" in r.getMessage() for r in caplog.records)
    assert all("ignored-after-auth" not in r.getMessage() for r in caplog.records)


# ── 007：auth 不帶 token 時讀握手 cookie（contracts/http-and-sync-changes.md §4）──


def _join_by_cookie(browser, code, number):
    response = browser.post(
        f"/api/activities/{code}/groups/join", json={"groupNumber": number}
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("auth", [{"type": "auth"}, {"type": "auth", "token": None}])
def test_auth_without_token_uses_cookie(client, auth):
    """Scenario: 007 US1-AS1（同一瀏覽器的新分頁以 cookie 恢復身分）"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    _join_by_cookie(browser, teacher.code, 3)
    with browser.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json(auth)
        snap = ws.receive_json()
    assert snap["role"] == "student"
    assert snap["ownGroup"]["number"] == 3


def test_auth_without_token_and_without_cookie_is_unauthorized(client):
    teacher = create_joinable(client)
    browser = TestClient(client.app)  # 完全沒有 cookie
    with browser.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth"})
        assert ws.receive_json() == {"type": "unauthorized", "reason": "INVALID_TOKEN"}
        assert _close_code(ws) == 4401


def test_auth_with_cookie_of_non_member_is_unauthorized(client):
    teacher = create_joinable(client)
    browser = new_browser_client(client)  # 有金鑰，但沒有加入任何組
    with browser.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth"})
        assert ws.receive_json() == {"type": "unauthorized", "reason": "INVALID_TOKEN"}
        assert _close_code(ws) == 4401


def test_auth_with_non_string_token_is_bad_first_message(client):
    teacher = create_joinable(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": 123})
        assert _close_code(ws) == 4400


def test_teacher_token_still_wins_over_student_cookie(client):
    """007 US3：同一瀏覽器有學生 cookie 時，老師以 token 驗證仍拿到老師快照。"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    _join_by_cookie(browser, teacher.code, 1)
    with browser.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": teacher.token})
        snap = ws.receive_json()
    assert snap["role"] == "teacher"
