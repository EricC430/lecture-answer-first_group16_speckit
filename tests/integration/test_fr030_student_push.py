"""FR-030、SC-009：學生不會因他組的加入、離開、被刪除或提交而收到推送
（PR #15 第三次審查問題 2；jacky0407 2026-11-23 決定「學生版只推與自己有關的變更」）。

驗證方式：他組動作之後再做一次公開變更，學生收到的下一則訊息必須就是那次公開變更，
而且版本只比原本多 1（中間沒有任何推送，版本也沒有跳動）。
"""

from tests.conftest import call, join_group, open_joining, service_of


def _post(client, teacher, path, body=None):
    return client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    return ctx, ws, ws.receive_json()


def test_student_sees_no_trace_of_other_groups_activity(client, teacher):
    open_joining(client, teacher)
    mine = join_group(client, teacher.code, 1)
    _post(client, teacher, "/rounds", {})
    s_ctx, s_ws, first = _connect(client, teacher.code, mine)
    t_ctx, t_ws, t_first = _connect(client, teacher.code, teacher.token)
    try:
        # 他組在搶答中加入、第一次提交
        other = join_group(client, teacher.code, 2)
        join_group(client, teacher.code, 3)
        service = service_of(client)
        assert call(client, service.mark_group_submitted, teacher.code, 2).ok

        # 老師每次都收到新的 revision，但 version 不變
        revisions = [t_ws.receive_json() for _ in range(3)]
        assert {s["version"] for s in revisions} == {t_first["version"]}
        assert [s["revision"] for s in revisions] == sorted(
            {s["revision"] for s in revisions}
        )

        # 公開變更：學生的下一則訊息就是它，版本只多 1
        closed = _post(client, teacher, "/rounds/current/close").json()
        snap = s_ws.receive_json()
        assert snap["stage"] == "RESULT_PENDING"
        assert snap["version"] == first["version"] + 1 == closed["version"]
        assert t_ws.receive_json()["version"] == snap["version"]

        # 結果階段：他組離開、老師刪除另一個空組；學生仍不會收到任何訊息
        client.post(
            f"/api/activities/{teacher.code}/groups/leave",
            headers={"Authorization": f"Bearer {other}"},
        )
        deleted = client.delete(
            f"/api/activities/{teacher.code}/groups/3", headers=teacher.headers
        )
        assert deleted.status_code == 200
        assert [t_ws.receive_json()["version"] for _ in range(2)] == [
            snap["version"]
        ] * 2
        finalized = _post(client, teacher, "/rounds/current/finalize").json()
        after = s_ws.receive_json()
        assert after["stage"] == "RESULT_FINAL"
        assert after["version"] == snap["version"] + 1 == finalized["version"]
    finally:
        s_ctx.__exit__(None, None, None)
        t_ctx.__exit__(None, None, None)
