"""US2：關輪後老師與學生快照出現 `ranking`；搶答中沒有（FR-024、FR-030）。"""

import time

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    return ctx, ws, ws.receive_json()


def test_no_ranking_while_round_is_open(client):
    """Scenario: US7-AS1（搶答中老師與學生的快照都沒有 ranking）。"""
    teacher, devices = open_ranking_round(client)
    answer(client, teacher, devices, 1, 1)
    assert "ranking" not in snapshot(client, teacher.code, teacher.token)
    assert "ranking" not in snapshot(client, teacher.code, devices[1])
    assert "ranking" not in snapshot(client, teacher.code, devices[2])


def test_ranking_appears_in_both_roles_after_close_within_two_seconds(client):
    """Scenario: US2-AS1～AS5 整合面（關輪後 2 秒內兩種身分都取得 ranking）。"""
    teacher, devices = open_ranking_round(client)
    answer(client, teacher, devices, 2, 1, "乙")
    answer(client, teacher, devices, 1, 1, "甲")
    answer(client, teacher, devices, 1, 2, "甲二")
    t_ctx, t_ws, _ = _connect(client, teacher.code, teacher.token)
    s_ctx, s_ws, _ = _connect(client, teacher.code, devices[3])
    try:
        started = time.monotonic()
        close_round(client, teacher)
        t_snap = t_ws.receive_json()
        s_snap = s_ws.receive_json()
        assert time.monotonic() - started < 2
    finally:
        t_ctx.__exit__(None, None, None)
        s_ctx.__exit__(None, None, None)
    for snap in (t_snap, s_snap):
        rounds = snap["ranking"]["rounds"]
        assert len(rounds) == 1
        assert rounds[0]["resultVersion"] == 1 and rounds[0]["final"] is False
        questions = {q["questionNumber"]: q for q in rounds[0]["questions"]}
        assert questions[1]["successGroup"] == 2  # 乙先送出
        assert questions[2]["successGroup"] == 1
        assert questions[3]["successGroup"] is None  # 無人提交 → 未成功
    assert (
        "countAtProcessing"
        in t_snap["ranking"]["rounds"][0]["questions"][0]["entries"][0]
    )
    assert (
        "countAtProcessing"
        not in s_snap["ranking"]["rounds"][0]["questions"][0]["entries"][0]
    )
    # GET /snapshot 與推送一致
    assert snapshot(client, teacher.code, teacher.token)["ranking"] == t_snap["ranking"]
