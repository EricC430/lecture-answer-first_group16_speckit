"""T060：WebSocket 同步契約（contracts/sync-websocket.md）。"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.conftest import (
    FakeClock,
    ManualScheduler,
    create_activity,
    join_group,
    make_app,
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
    assert set(snap) == COMMON_FIELDS | {"groups", "maxGroups", "questionNumbers"}
    assert snap["role"] == "teacher"
    assert snap["version"] == 1


def test_student_receives_only_own_group(client):
    teacher = create_activity(client)
    device = join_group(client, teacher.code, "第一組")
    join_group(client, teacher.code, "第二組")
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": device})
        snap = ws.receive_json()
    assert set(snap) == COMMON_FIELDS | {"ownGroup"}
    assert snap["role"] == "student"
    assert snap["ownGroup"] == {"name": "第一組", "successCount": 0}
    assert "第二組" not in str(snap)


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
    teacher = create_activity(client)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": teacher.token})
        assert ws.receive_json()["version"] == 1
        ws.send_json({"type": "auth", "token": "ignored-after-auth"})
        join_group(client, teacher.code, "第一組")
        snap = ws.receive_json()
    assert snap["version"] == 2
    assert [g["name"] for g in snap["groups"]] == ["第一組"]
    assert any("多餘訊息" in r.getMessage() for r in caplog.records)
    assert all("ignored-after-auth" not in r.getMessage() for r in caplog.records)
