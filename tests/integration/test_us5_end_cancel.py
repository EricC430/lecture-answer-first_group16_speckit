"""T066：US5 老師結束或取消活動並看到未成功題。"""

from types import MappingProxyType

from lecture_quiz.app.activity.secrets_gen import new_browser_key
from lecture_quiz.core.activity.commands import FinalizeOutcome
from tests.conftest import call, join_group, open_joining, service_of


def _post(client, teacher, path, body=None):
    return client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )


def _finalize_with_solved(client, teacher, solved):
    """模擬 004 的定案結果（001 的 HTTP 定案不標記成功題）。"""
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)
    outcome = FinalizeOutcome(frozenset(solved), MappingProxyType({}))
    result = call(client, service.finalize, teacher.code, requester, outcome)
    assert result.ok, result


def _to_final(client, teacher, solved=(1, 2)):
    if service_of(client).get(teacher.code).stage.value == "PREPARING":
        open_joining(client, teacher, 3)
    _post(client, teacher, "/rounds", {"questionNumbers": [1, 2, 3]})
    _post(client, teacher, "/rounds/current/close")
    _finalize_with_solved(client, teacher, solved)


def test_end_shows_unsolved_on_all_pages(client, teacher):
    """Scenario: US5-AS1

    定案後第 3 題無人成功 → 結束：回應與所有頁面的快照都列出未成功題（含第 3 題）。
    """
    open_joining(client, teacher, 3)
    device = join_group(client, teacher.code, 1)
    _to_final(client, teacher)
    with (
        client.websocket_connect(f"/ws/activities/{teacher.code}") as t_ws,
        client.websocket_connect(f"/ws/activities/{teacher.code}") as s_ws,
    ):
        t_ws.send_json({"type": "auth", "token": teacher.token})
        s_ws.send_json({"type": "auth", "token": device})
        t_ws.receive_json()
        s_ws.receive_json()
        response = _post(client, teacher, "/end")
        assert response.status_code == 200
        assert response.json()["unsolvedQuestions"] == [3]
        for ws in (t_ws, s_ws):
            snap = ws.receive_json()
            assert snap["stage"] == "ENDED"
            assert snap["unsolvedQuestions"] == [3]


def test_export_view_available_after_end(client, teacher):
    """Scenario: US5-AS2

    已結束仍可匯出；未成功題標示為未成功，不視為答對。
    """
    _to_final(client, teacher)
    _post(client, teacher, "/end")
    service = service_of(client)
    view = service.export_view(
        teacher.code, service.resolve_requester(teacher.code, teacher.token)
    )
    assert view.ok
    assert view.value.unsolved_questions == (3,)
    assert 3 not in view.value.solved_questions
    student = service.export_view(
        teacher.code, service.resolve_requester(teacher.code, None)
    )
    assert student.rejection.value == "NOT_TEACHER"


def test_end_during_round_or_pending_rejected(client, teacher):
    """Scenario: US5-AS3

    搶答中或結果未定案時結束被拒，說明「請先關輪並確認定案」，階段不變。
    """
    open_joining(client, teacher)
    _post(client, teacher, "/rounds", {})
    for expected_stage in ("ROUND_OPEN", "RESULT_PENDING"):
        response = _post(client, teacher, "/end")
        assert response.status_code == 409
        assert "請先關輪並確認定案" in response.json()["error"]["message"]
        snap = client.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        ).json()
        assert snap["stage"] == expected_stage
        _post(client, teacher, "/rounds/current/close")


def test_cancel_while_preparing(client, teacher):
    """Scenario: US5-AS4

    開放加入階段（第一輪開始前）取消 → 已取消；之後控制操作被拒、學生畫面顯示已取消、
    不提供匯出。
    """
    open_joining(client, teacher)
    device = join_group(client, teacher.code, 1)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as s_ws:
        s_ws.send_json({"type": "auth", "token": device})
        s_ws.receive_json()
        assert _post(client, teacher, "/cancel").status_code == 200
        assert s_ws.receive_json()["stage"] == "CANCELLED"
    for path in ("/rounds", "/end", "/cancel"):
        response = _post(client, teacher, path)
        assert response.status_code == 409
        assert response.json()["error"]["message"] == "活動已取消，無法再進行這個操作。"
    service = service_of(client)
    export = service.export_view(
        teacher.code, service.resolve_requester(teacher.code, teacher.token)
    )
    assert not export.ok
    assert export.rejection.value == "STAGE_NOT_ALLOWED"


def test_ended_rejects_submission_and_join(client, teacher, fake_clock):
    """Scenario: US5-AS5

    已結束時提交被拒（accepts_submission 為 False），新組別加入也被拒並說明活動已結束。
    """
    _to_final(client, teacher)
    _post(client, teacher, "/end")
    service = service_of(client)
    assert service.accepts_submission(teacher.code, fake_clock.now()) is False
    joined = call(client, service.join, teacher.code, 2, browser_key=new_browser_key())
    assert not joined.ok
    assert joined.message == "活動已結束，無法加入。"


def test_end_while_preparing_rejected(client, teacher):
    """Scenario: US5-AS6

    準備中要求結束（不是取消）被拒，說明準備中只能取消活動。
    """
    response = _post(client, teacher, "/end")
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "準備中只能取消活動。"
