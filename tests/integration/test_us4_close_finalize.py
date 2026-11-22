"""T055：US4 關輪只發生一次，並先定案才能往下走。"""

from tests.conftest import call, seed_questions


def _post(client, teacher, path, body=None):
    return client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )


def _snapshot(client, teacher):
    return client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()


def _ws(client, teacher):
    ctx = client.websocket_connect(f"/ws/activities/{teacher.code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": teacher.token})
    ws.receive_json()
    return ctx, ws


def test_teacher_close(client, teacher, manual_scheduler):
    """Scenario: US4-AS1

    老師關輪 → 結果未定案，推送一次新快照，倒數排程被取消。
    """
    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"countdownSeconds": 60})
    ctx, ws = _ws(client, teacher)
    try:
        response = _post(client, teacher, "/rounds/current/close")
        assert response.status_code == 200
        snap = ws.receive_json()
        assert snap["stage"] == "RESULT_PENDING"
        assert snap["openQuestions"] == []
        assert snap["deadline"] is None
    finally:
        ctx.__exit__(None, None, None)
    assert teacher.code not in manual_scheduler.scheduled


def test_deadline_closes_round(client, teacher, manual_scheduler, fake_clock):
    """Scenario: US4-AS2

    到達開輪時固定的截止時間，系統自動關輪，行為與手動關輪相同。
    """
    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"countdownSeconds": 60})
    assert teacher.code in manual_scheduler.scheduled
    fake_clock.advance(60)
    call(client, manual_scheduler.fire, teacher.code)
    snap = _snapshot(client, teacher)
    assert snap["stage"] == "RESULT_PENDING"
    assert snap["roundNumber"] == 1


def test_simultaneous_close_and_deadline(client, teacher, manual_scheduler, fake_clock):
    """Scenario: US4-AS3

    老師關輪與倒數截止同時發生：只有一份結果，輪次數不變，較晚的不改變任何狀態。
    """
    import asyncio

    from tests.conftest import service_of

    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"countdownSeconds": 60})
    fake_clock.advance(60)
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)

    async def race():
        return await asyncio.gather(
            service.close_round(teacher.code, requester),
            manual_scheduler.fire(teacher.code),
        )

    version_before = _snapshot(client, teacher)["version"]
    call(client, race)
    snap = _snapshot(client, teacher)
    assert snap["version"] == version_before + 1
    assert snap["roundNumber"] == 1
    again = _post(client, teacher, "/rounds/current/close")
    assert again.json()["alreadyClosed"] is True


def test_no_auto_finalize(client, teacher, manual_scheduler, fake_clock):
    """Scenario: US4-AS4

    結果未定案時，即使時間經過、倒數再次觸發，也不會自動定案或開下一輪。
    """
    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"countdownSeconds": 10})
    _post(client, teacher, "/rounds/current/close")
    fake_clock.advance(3600)
    call(client, manual_scheduler.fire, teacher.code)
    snap = _snapshot(client, teacher)
    assert snap["stage"] == "RESULT_PENDING"
    assert snap["roundNumber"] == 1


def test_open_next_round_before_finalize_rejected(client, teacher):
    """Scenario: US4-AS5

    結果未定案時開下一輪被拒，說明「請先確認定案本輪結果」。
    """
    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"questionNumbers": [1]})
    _post(client, teacher, "/rounds/current/close")
    response = _post(client, teacher, "/rounds", {"questionNumbers": [2]})
    assert response.status_code == 409
    assert "請先確認定案本輪結果" in response.json()["error"]["message"]
    assert _snapshot(client, teacher)["stage"] == "RESULT_PENDING"


def test_finalize_then_next_round(client, teacher):
    """Scenario: US4-AS6

    定案後開下一輪：輪次編號加一；可選題目只包含尚未成功的題目
    （001 的定案不標記成功題，因此四題仍可選；選已成功題的拒絕由核心測試涵蓋）。
    """
    seed_questions(client, teacher)
    _post(client, teacher, "/rounds", {"questionNumbers": [1]})
    _post(client, teacher, "/rounds/current/close")
    assert _post(client, teacher, "/rounds/current/finalize").status_code == 200
    assert _snapshot(client, teacher)["stage"] == "RESULT_FINAL"
    second = _post(client, teacher, "/rounds", {"questionNumbers": [2, 3]})
    assert second.status_code == 201
    assert second.json()["roundNumber"] == 2
    snap = _snapshot(client, teacher)
    assert snap["openQuestions"] == [2, 3]
