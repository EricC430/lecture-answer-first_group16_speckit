"""US6：文字安全、無倒數輪次與重新連線（FR-029～FR-033）。

後端不轉義、不過濾答案，原文保存與回傳；安全顯示由前端 `textContent` 負責
（靜態檢查見 `tests/architecture/test_static_text_safety.py`）。
"""

import pytest

from tests.conftest import create_activity, seed_questions, submit

MARKUP = "<b>粗體</b><script>alert(1)</script>"


def _post(client, teacher, path, body=None):
    response = client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


def _snapshot(client, code, token):
    return client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    return ctx, ws, ws.receive_json()


@pytest.fixture
def joined(client):
    """版面 A；第 1 組兩台裝置（a、b），已開放加入，尚未開輪。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    _post(client, teacher, "/open-joining")
    a = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 1}
    ).json()
    b = client.post(
        f"/api/activities/{teacher.code}/groups/join",
        json={"groupNumber": 1, "credential": a["credential"]},
    ).json()
    return teacher, a["deviceToken"], b["deviceToken"]


def test_markup_answer_is_kept_verbatim(client, joined):
    """Scenario: US6-AS1（OpenSpec「特殊文字答案」）。"""
    teacher, a, _ = joined
    _post(client, teacher, "/rounds")
    response = submit(client, teacher.code, a, 1, 3, [MARKUP])
    assert response.status_code == 201
    assert response.json()["submission"]["answers"] == [MARKUP]
    own = _snapshot(client, teacher.code, a)["submissions"]["current"]["own"]
    assert own[0]["answers"] == [MARKUP]
    board = _snapshot(client, teacher.code, teacher.token)
    q3 = next(
        q
        for q in board["submissions"]["current"]["questions"]
        if q["questionNumber"] == 3
    )
    assert q3["entries"][0]["answers"] == [MARKUP]


def test_round_without_countdown_accepts_until_teacher_closes(
    client, joined, fake_clock
):
    """Scenario: US6-AS3（OpenSpec「無倒數輪次」）。"""
    teacher, a, _ = joined
    _post(client, teacher, "/rounds")
    assert _snapshot(client, teacher.code, a)["deadline"] is None
    fake_clock.advance(3600)
    assert submit(client, teacher.code, a, 1, 4, ["一小時後"]).status_code == 201
    _post(client, teacher, "/rounds/current/close")
    late = submit(client, teacher.code, a, 1, 3, ["關輪後"])
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "ROUND_CLOSED"


def test_round_with_countdown_exposes_backend_deadline(client, joined):
    """Scenario: US6-AS2：學生快照帶後端截止時間，前端據此倒數。"""
    teacher, a, _ = joined
    opened = _post(client, teacher, "/rounds", {"countdownSeconds": 60})
    snapshot = _snapshot(client, teacher.code, a)
    assert snapshot["deadline"] == opened["deadline"] == "2026-11-21T09:01:00+08:00"


def test_reconnect_shows_submissions_made_while_disconnected(client, joined):
    """Scenario: US6-AS5（FR-033）：重新連線的第一份快照就有斷線期間本組的提交。"""
    teacher, a, b = joined
    _post(client, teacher, "/rounds")
    ctx, _, first = _connect(client, teacher.code, a)
    assert first["submissions"]["current"]["own"] == []
    ctx.__exit__(None, None, None)
    assert submit(client, teacher.code, b, 1, 1, ["乙", "丙"]).status_code == 201
    ctx, _, again = _connect(client, teacher.code, a)
    try:
        own = again["submissions"]["current"]["own"]
        assert [(s["questionNumber"], s["answers"]) for s in own] == [(1, ["乙", "丙"])]
    finally:
        ctx.__exit__(None, None, None)
