"""T045：US3 老師依條件開輪並固定本輪規則。"""

from tests.conftest import join_group, open_joining


def _open(client, teacher, body, key=None):
    headers = dict(teacher.headers)
    if key:
        headers["Idempotency-Key"] = key
    return client.post(
        f"/api/activities/{teacher.code}/rounds", json=body, headers=headers
    )


def _snapshot(client, teacher):
    return client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()


def test_open_panel_defaults(client, teacher):
    """Scenario: US3-AS1

    匯入四題後，快照列出四題且都是未成功題；不帶任何選項開輪時，四題全開、公平模式關、不倒數。
    """
    open_joining(client, teacher, 4)
    snap = _snapshot(client, teacher)
    assert snap["questionNumbers"] == [1, 2, 3, 4]
    body = _open(client, teacher, {}).json()
    assert body["deadline"] is None
    snap = _snapshot(client, teacher)
    assert snap["openQuestions"] == [1, 2, 3, 4]
    assert snap["fairMode"] is False


def test_open_two_questions_pushes_round_open_to_all(client, teacher):
    """Scenario: US3-AS2

    選兩題開輪：建立第 1 輪，所有 WebSocket 連線都收到 stage == ROUND_OPEN。
    """
    open_joining(client, teacher, 4)
    device = join_group(client, teacher.code, 1)
    with (
        client.websocket_connect(f"/ws/activities/{teacher.code}") as t_ws,
        client.websocket_connect(f"/ws/activities/{teacher.code}") as s_ws,
    ):
        t_ws.send_json({"type": "auth", "token": teacher.token})
        s_ws.send_json({"type": "auth", "token": device})
        t_ws.receive_json()
        s_ws.receive_json()
        response = _open(client, teacher, {"questionNumbers": [1, 2]})
        assert response.status_code == 201
        assert response.json()["roundNumber"] == 1
        for ws in (t_ws, s_ws):
            snap = ws.receive_json()
            assert snap["stage"] == "ROUND_OPEN"
            assert snap["openQuestions"] == [1, 2]
            assert snap["roundNumber"] == 1


def test_no_imported_questions(client, teacher):
    """Scenario: US3-AS3

    沒有題目時開輪被拒並說明「請先成功匯入學習單」，維持準備中。
    """
    response = _open(client, teacher, {})
    assert response.status_code == 409
    assert "請先成功匯入學習單" in response.json()["error"]["message"]
    assert _snapshot(client, teacher)["stage"] == "PREPARING"


def test_invalid_selection_rejected(client, teacher):
    """Scenario: US3-AS4

    選零題、選不存在的題目都被拒，狀態不變。
    「選已成功題」與「結果未定案時開新輪」需要定案與關輪，分別由核心測試
    `test_state_machine_open_round.py` 與 US4-AS5 的整合測試涵蓋。
    """
    open_joining(client, teacher, 4)
    before = _snapshot(client, teacher)
    for selection in ([], [9], [1, 1]):
        response = _open(client, teacher, {"questionNumbers": selection})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_SELECTION"
        assert (
            response.json()["error"]["message"] == "請至少選擇一題尚未有人答對的題目。"
        )
    assert _snapshot(client, teacher) == before


def test_rules_locked_during_round(client, teacher):
    """Scenario: US3-AS5

    搶答中再送開輪（試圖改題目、模式或截止時間）被拒，規則快照不變。
    """
    open_joining(client, teacher, 4)
    _open(client, teacher, {"questionNumbers": [1, 2], "fairMode": False})
    before = _snapshot(client, teacher)
    response = _open(
        client,
        teacher,
        {"questionNumbers": [3], "fairMode": True, "countdownSeconds": 10},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RULES_LOCKED"
    after = _snapshot(client, teacher)
    assert after == before


def test_countdown_range(client, teacher):
    """Scenario: US3-AS6

    秒數 0、負數、小數、非數字、空白、大於 3600 都被拒且不建立輪次；1 可以正常開輪。
    """
    open_joining(client, teacher, 4)
    for raw in (0, -5, 1.5, "abc", "", 3601):
        response = _open(client, teacher, {"countdownSeconds": raw})
        assert response.status_code == 400, raw
        assert response.json()["error"]["message"] == "倒數秒數須為 1～3600 的整數。"
    assert _snapshot(client, teacher)["roundNumber"] is None
    ok = _open(client, teacher, {"countdownSeconds": 1})
    assert ok.status_code == 201
    assert ok.json()["deadline"] == "2026-11-21T09:00:01+08:00"


def test_resent_open_creates_one_round(client, teacher, manual_scheduler):
    """Scenario: US3-AS7

    同一個 Idempotency-Key 重送開輪，只產生一個輪次，回應相同（SC-004）。
    """
    open_joining(client, teacher, 4)
    responses = [
        _open(
            client,
            teacher,
            {"questionNumbers": [1], "countdownSeconds": 30},
            key="open-1",
        )
        for _ in range(20)
    ]
    assert {r.status_code for r in responses} == {201}
    assert len({r.text for r in responses}) == 1
    snap = _snapshot(client, teacher)
    assert snap["roundNumber"] == 1
    assert manual_scheduler.scheduled == {
        teacher.code: manual_scheduler.last_deadline[teacher.code]
    }


def test_concurrent_open_with_same_key_applies_once(client, teacher):
    """同一個 key 並行開輪只套用一次（FR-033、PR #15 審查第 2 項）。"""
    import asyncio

    from tests.conftest import call, service_of

    open_joining(client, teacher, 4)
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)

    async def both():
        return await asyncio.gather(
            *(
                service.open_round(teacher.code, requester, (1,), False, None, "k")
                for _ in range(5)
            )
        )

    results = call(client, both)
    assert all(r == results[0] for r in results)
    assert results[0].ok
    assert len(service.get(teacher.code).rounds) == 1
