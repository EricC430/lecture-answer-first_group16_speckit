"""007：同一瀏覽器共用學生身分（只走學生實際使用的 cookie 路徑）。

每個「瀏覽器」是一個獨立的 `TestClient`（各自的 cookie jar），學生請求一律**不帶
Bearer**（research R8）；Bearer 只用於老師請求。
"""

import asyncio

from fastapi.testclient import TestClient

from lecture_quiz.app.activity.secrets_gen import new_browser_key
from tests.conftest import (
    call,
    create_activity,
    create_joinable,
    new_browser_client,
    seed_questions,
    service_of,
)

ALREADY = "這個瀏覽器已是第 {n} 組成員，請先離開本組。"


def _join(browser: TestClient, code: str, number: int, credential=None):
    return browser.post(
        f"/api/activities/{code}/groups/join",
        json={"groupNumber": number, "credential": credential},
    )


def _snapshot(browser: TestClient, code: str):
    return browser.get(f"/api/activities/{code}/snapshot")


def _teacher_groups(client, teacher) -> dict[int, dict]:
    snapshot = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()
    return {g["number"]: g for g in snapshot["groups"]}


def _open_round_with_blanks(client, max_groups: int = 6):
    """建立活動、題目（每題 1 格）並開放加入；回傳老師身分。"""
    teacher = create_activity(client, max_groups)
    seed_questions(client, teacher, 3, blanks=[1, 1, 1])
    response = client.post(
        f"/api/activities/{teacher.code}/open-joining",
        json={},
        headers=teacher.headers,
    )
    assert response.status_code == 200, response.text
    return teacher


def _open_round(client, teacher):
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201, response.text


def _submit(browser, code, question, answers, **extra):
    return browser.post(
        f"/api/activities/{code}/submissions",
        json={
            "roundNumber": 1,
            "questionNumber": question,
            "answers": answers,
            **extra,
        },
    )


# ── US1：同一瀏覽器只能代表一個組別 ──


def test_same_browser_restores_group_in_new_tab(client):
    """Scenario: 007 US1-AS1

    同一個瀏覽器（同一個 cookie jar）加入第 3 組後，新分頁只靠 cookie 就是第 3 組。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    joined = _join(browser, teacher.code, 3)
    assert joined.status_code == 200
    snapshot = _snapshot(browser, teacher.code)
    assert snapshot.status_code == 200
    own = snapshot.json()["ownGroup"]
    assert own["number"] == 3
    assert own["credential"] == joined.json()["credential"]


def test_other_browser_joins_same_group_with_credential(client):
    """Scenario: 007 US1-AS2"""
    teacher = create_joinable(client)
    first = new_browser_client(client)
    credential = _join(first, teacher.code, 3).json()["credential"]
    second = new_browser_client(client)
    assert _join(second, teacher.code, 3, credential).status_code == 200
    assert _snapshot(second, teacher.code).json()["ownGroup"]["number"] == 3
    assert _teacher_groups(client, teacher)[3]["deviceCount"] == 2


def test_member_browser_join_other_group_rejected(client):
    """Scenario: 007 US1-AS3

    已是第 3 組的瀏覽器加入第 5 組：409，第 5 組不被建立、不發憑證。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    rejected = _join(browser, teacher.code, 5)
    assert rejected.status_code == 409
    assert rejected.json()["error"] == {
        "code": "ALREADY_IN_GROUP",
        "message": ALREADY.format(n=3),
    }
    assert set(_teacher_groups(client, teacher)) == {3}
    assert _snapshot(browser, teacher.code).json()["ownGroup"]["number"] == 3


def test_forged_or_foreign_key_is_anonymous(client):
    """Scenario: 007 US1-AS4（SC-004）

    竄改的 cookie、其他活動的成員 cookie、格式錯誤的 cookie：查看本組資料、提交、
    離開本組都被拒，回應不含任何憑證或金鑰。
    """
    teacher = _open_round_with_blanks(client)
    member = new_browser_client(client)
    credential = _join(member, teacher.code, 1).json()["credential"]
    other_teacher = create_joinable(client)
    foreign = new_browser_client(client)
    assert _join(foreign, other_teacher.code, 1).status_code == 200
    _open_round(client, teacher)

    forged_key = new_browser_key()
    cases = {
        "forged": forged_key,
        "foreign": foreign.cookies.get("lq_browser"),
        "malformed": "not-a-key",
    }
    secrets = (credential, member.cookies.get("lq_browser"), teacher.token)
    for name, value in cases.items():
        browser = TestClient(client.app)
        browser.cookies.set("lq_browser", value)
        responses = [
            _snapshot(browser, teacher.code),
            _submit(browser, teacher.code, 1, ["答"]),
            browser.post(f"/api/activities/{teacher.code}/groups/leave", json={}),
        ]
        for response in responses:
            assert response.status_code in (401, 403), (name, response.text)
            for secret in secrets:
                assert secret not in response.text, name
            assert value not in response.text or name == "malformed", name


def test_key_persists_without_tab_state(client):
    """Scenario: 007 US1-AS5

    重開瀏覽器：分頁的狀態都沒了，只剩 cookie；仍恢復為第 3 組。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    reopened = TestClient(client.app)
    reopened.cookies.set("lq_browser", browser.cookies.get("lq_browser"))
    assert _snapshot(reopened, teacher.code).json()["ownGroup"]["number"] == 3


def test_submission_ignores_claimed_group(client):
    """Scenario: 007 US1-AS6

    本文自稱第 5 組，提交仍歸第 3 組（組別由後端依瀏覽器身分判定）。
    """
    teacher = _open_round_with_blanks(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    assert _join(new_browser_client(client), teacher.code, 5).status_code == 200
    _open_round(client, teacher)
    response = _submit(browser, teacher.code, 1, ["答"], groupNumber=5)
    assert response.status_code == 201, response.text
    ledger = client.app.state.submission_service._store.get(teacher.code)
    assert [s.group_number for s in ledger.submissions] == [3]


def test_ten_join_attempts_one_group(client):
    """Scenario: 007 US1-AS3（SC-001）

    同一個瀏覽器依序加入組號 1～10：只有第 1 次成功，其餘 9 次被拒且沒有新憑證。
    """
    teacher = create_joinable(client, max_groups=10)
    browser = new_browser_client(client)
    results = [_join(browser, teacher.code, n) for n in range(1, 11)]
    assert results[0].status_code == 200
    assert [r.status_code for r in results[1:]] == [409] * 9
    assert all("credential" not in r.json() for r in results[1:])
    assert set(_teacher_groups(client, teacher)) == {1}


def test_concurrent_joins_one_wins(client):
    """Scenario: 007 US1-AS3（SC-002、FR-007）

    直接呼叫服務層：HTTP 的身分解析在鎖外，競爭點就在服務層。同一把金鑰同時加入
    第 3 組與第 5 組，重複 20 次，每次恰好一個成功、組別數為 1，落敗者訊息含組號。
    """
    service = service_of(client)
    for _ in range(20):
        teacher = create_joinable(client)
        key = new_browser_key()

        async def race(code=teacher.code, key=key):
            return await asyncio.gather(
                service.join(code, 3, browser_key=key),
                service.join(code, 5, browser_key=key),
            )

        outcomes = call(client, race)
        winners = [o for o in outcomes if o.ok]
        losers = [o for o in outcomes if not o.ok]
        assert len(winners) == 1 and len(losers) == 1
        won = winners[0].value.group_number
        assert losers[0].message == ALREADY.format(n=won)
        assert set(_teacher_groups(client, teacher)) == {won}
        cancel = client.post(
            f"/api/activities/{teacher.code}/cancel", json={}, headers=teacher.headers
        )
        assert cancel.status_code == 200


def test_join_retry_with_same_key_returns_original(client):
    """verification P-01：同一瀏覽器以相同 Idempotency-Key 重送加入，回原結果。"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    headers = {"Idempotency-Key": "retry-1"}
    first = browser.post(
        f"/api/activities/{teacher.code}/groups/join",
        json={"groupNumber": 2},
        headers=headers,
    )
    again = browser.post(
        f"/api/activities/{teacher.code}/groups/join",
        json={"groupNumber": 2},
        headers=headers,
    )
    assert first.status_code == again.status_code == 200
    assert first.json() == again.json()


# ── US2：同一瀏覽器的分頁狀態同步（後端：同一雜湊的所有連線）──


def _connect(browser: TestClient, code: str):
    """以 cookie 身分開一條同步連線（代表一個分頁）；回傳 (context, session)。"""
    context = browser.websocket_connect(f"/ws/activities/{code}")
    session = context.__enter__()
    session.send_json({"type": "auth"})
    first = session.receive_json()
    assert first["type"] == "snapshot", first
    return context, session


def _close_round(client, teacher):
    response = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close",
        json={},
        headers=teacher.headers,
    )
    assert response.status_code == 200, response.text


def test_leave_closes_all_tabs_of_browser(client):
    """Scenario: 007 US2-AS2

    同一瀏覽器的兩個分頁都收到 LEFT_GROUP；同組另一個瀏覽器不受影響。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    credential = _join(browser, teacher.code, 3).json()["credential"]
    other = new_browser_client(client)
    assert _join(other, teacher.code, 3, credential).status_code == 200
    tabs = [_connect(browser, teacher.code) for _ in range(2)]
    other_tab = _connect(other, teacher.code)
    try:
        left = browser.post(f"/api/activities/{teacher.code}/groups/leave", json={})
        assert left.status_code == 200, left.text
        for _, session in tabs:
            message = session.receive_json()
            while message["type"] != "unauthorized":
                message = session.receive_json()
            assert message == {"type": "unauthorized", "reason": "LEFT_GROUP"}
        assert _snapshot(other, teacher.code).json()["ownGroup"]["number"] == 3
        assert _teacher_groups(client, teacher)[3]["deviceCount"] == 1
    finally:
        for context, _ in (*tabs, other_tab):
            context.__exit__(None, None, None)


def test_leave_rejected_during_round_keeps_all_tabs(client):
    """Scenario: 007 US2-AS3"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    _open_round(client, teacher)
    rejected = browser.post(f"/api/activities/{teacher.code}/groups/leave", json={})
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "NO_GROUP_SWITCH_DURING_ROUND"
    assert _snapshot(browser, teacher.code).json()["ownGroup"]["number"] == 3


def test_group_delete_closes_all_tabs(client):
    """Scenario: 007 US2-AS4"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    tabs = [_connect(browser, teacher.code) for _ in range(2)]
    try:
        deleted = client.delete(
            f"/api/activities/{teacher.code}/groups/3", headers=teacher.headers
        )
        assert deleted.status_code == 200, deleted.text
        for _, session in tabs:
            message = session.receive_json()
            while message["type"] != "unauthorized":
                message = session.receive_json()
            assert message == {"type": "unauthorized", "reason": "GROUP_DELETED"}
    finally:
        for context, _ in tabs:
            context.__exit__(None, None, None)


def test_submission_state_reaches_other_tab(client):
    """Scenario: 007 US2-AS5

    分頁 A 提交後，同一瀏覽器的分頁 B 收到的快照顯示該題本組已送出。
    """
    teacher = _open_round_with_blanks(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 2).status_code == 200
    _open_round(client, teacher)
    context, tab_b = _connect(browser, teacher.code)
    try:
        assert _submit(browser, teacher.code, 2, ["答"]).status_code == 201
        message = tab_b.receive_json()
        while not message.get("submissions", {}).get("current", {}).get("own"):
            message = tab_b.receive_json()
        own = message["submissions"]["current"]["own"]
        assert [entry["questionNumber"] for entry in own] == [2]
    finally:
        context.__exit__(None, None, None)


def test_restart_makes_all_tabs_gone(client):
    """Scenario: 007 US2-AS6（FR-011）

    後端重啟（新的 app）：帶舊 cookie 的連線收到 gone，HTTP 取快照回 410。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 3).status_code == 200
    key = browser.cookies.get("lq_browser")
    from tests.conftest import make_app

    with TestClient(make_app()) as restarted:
        old_tab = TestClient(restarted.app)
        old_tab.cookies.set("lq_browser", key)
        with old_tab.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
            ws.send_json({"type": "auth"})
            assert ws.receive_json() == {"type": "gone"}
        snapshot = _snapshot(old_tab, teacher.code)
        assert snapshot.status_code == 410
        assert snapshot.json()["error"]["code"] == "ACTIVITY_GONE"


def test_stale_tab_action_after_leave_rejected(client):
    """FR-012：另一分頁已離開本組後，舊分頁的操作被拒，原組別資料不變。"""
    teacher = _open_round_with_blanks(client)
    browser = new_browser_client(client)
    credential = _join(browser, teacher.code, 1).json()["credential"]
    other = new_browser_client(client)
    assert _join(other, teacher.code, 1, credential).status_code == 200
    left = browser.post(f"/api/activities/{teacher.code}/groups/leave", json={})
    assert left.status_code == 200
    again = browser.post(f"/api/activities/{teacher.code}/groups/leave", json={})
    assert again.status_code in (401, 403), again.text
    _open_round(client, teacher)
    stale = _submit(browser, teacher.code, 1, ["答"])
    assert stale.status_code in (401, 403), stale.text
    ledger = client.app.state.submission_service._store.get(teacher.code)
    assert ledger is None or list(ledger.submissions) == []
    assert _teacher_groups(client, teacher)[1]["deviceCount"] == 1


# ── US3：老師與學生在同一瀏覽器 ──


def test_student_join_keeps_teacher_control(client):
    """Scenario: 007 US3-AS1

    同一個瀏覽器（同一個 cookie jar）：學生以 cookie 加入，老師以 Bearer 開輪成功。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 1).status_code == 200
    opened = browser.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert opened.status_code == 201, opened.text


def test_student_leave_or_delete_keeps_teacher(client):
    """Scenario: 007 US3-AS2"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 1).status_code == 200
    assert (
        browser.post(
            f"/api/activities/{teacher.code}/groups/leave", json={}
        ).status_code
        == 200
    )
    assert _join(browser, teacher.code, 1).status_code == 200
    deleted = browser.delete(
        f"/api/activities/{teacher.code}/groups/1", headers=teacher.headers
    )
    assert deleted.status_code == 200, deleted.text
    opened = browser.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert opened.status_code == 201, opened.text
    _close_round(client, teacher)
    assert (
        browser.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        ).json()["role"]
        == "teacher"
    )


TEACHER_ONLY = [
    ("post", "/open-joining", {}),
    ("post", "/rounds", {}),
    ("post", "/rounds/current/close", {}),
    ("post", "/rounds/current/finalize", {"resultVersion": 1}),
    ("post", "/end", {}),
    ("post", "/cancel", {}),
    ("delete", "/groups/1", None),
    ("post", "/import", {}),
    ("post", "/export/preview", {}),
    ("put", "/rounds/1/questions/1/groups/1/judgement", {"wrong": True}),
]


def test_cookie_only_cannot_do_teacher_ops(client):
    """Scenario: 007 US3-AS3（SC-005 的權限面）

    只帶學生 cookie，10 種老師專用操作全部被拒，活動版本不變。
    """
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join(browser, teacher.code, 1).status_code == 200
    before = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()["version"]
    for method, path, body in TEACHER_ONLY:
        url = f"/api/activities/{teacher.code}{path}"
        kwargs = {} if body is None else {"json": body}
        response = getattr(browser, method)(url, **kwargs)
        assert response.status_code in (401, 403), (path, response.text)
    after = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()["version"]
    assert after == before


def test_browser_key_never_logged_or_returned(client, caplog):
    """SC-007、FR-008：整個流程的日誌與回應本文都不含瀏覽器金鑰。"""
    caplog.set_level("INFO")
    teacher = _open_round_with_blanks(client)
    browser = TestClient(client.app)
    session = browser.post("/api/browser-session")
    key = session.cookies["lq_browser"]
    bodies = [session.text]
    bodies.append(_join(browser, teacher.code, 1).text)
    with browser.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth"})
        bodies.append(str(ws.receive_json()))
    _open_round(client, teacher)
    bodies.append(_submit(browser, teacher.code, 1, ["答"]).text)
    bodies.append(_snapshot(browser, teacher.code).text)
    _close_round(client, teacher)
    bodies.append(
        browser.post(f"/api/activities/{teacher.code}/groups/leave", json={}).text
    )
    assert caplog.records, "沒有擷取到任何日誌，測試沒有驗證到東西"
    assert any("browser-session" in r.getMessage() for r in caplog.records)
    assert key not in caplog.text
    for body in bodies:
        assert key not in body
