"""007：真實瀏覽器中「同一瀏覽器共用學生身分、分頁同步」的端對端測試。

每個「瀏覽器」是一個獨立的 CDP browser context（cookie 與儲存空間分開）。學生身分
一律由頁面實際加入取得，不注入（research R8）；同一個 context 的分頁就是同一個瀏覽器
的多個分頁。2 秒內的同步要求（FR-010、SC-003）以 `wait_for(..., timeout=2.0)` 驗證，
計時從觸發操作的那一頁完成更新之後開始，所以比實際延遲更嚴格。
"""

from tests.browser.test_pages import assert_no_script_errors
from tests.browser.test_teacher_restore import (
    close,
    create_on_teacher_page,
    import_and_open_joining,
)

ALREADY = "這個瀏覽器已是第 3 組成員，請先離開本組。"
SYNC_SECONDS = 2.0
SHOWS_GROUP = "document.getElementById('student-info').hidden === false"
SHOWS_JOIN = "document.getElementById('student-join').hidden === false"


def _group_text(tab) -> str:
    return tab.text("#student-group")


def _student_page(tab, world, with_code: bool = False) -> None:
    query = f"?code={world.code}" if with_code else ""
    tab.goto(f"{world.server.base}/student.html{query}")
    # 載入時先確保瀏覽器金鑰；完成後加入按鈕才可以按
    tab.wait_for("document.querySelector('#student-join button').disabled === false")


def _submit_join(tab, code: str, group: int) -> None:
    tab.eval(f"document.getElementById('join-code').value = '{code}', true")
    tab.eval(f"document.getElementById('join-number').value = '{group}', true")
    tab.eval("document.querySelector('#student-join').requestSubmit(), true")


def _join(tab, world, group: int) -> None:
    _student_page(tab, world)
    _submit_join(tab, world.code, group)
    tab.wait_for(SHOWS_GROUP)


def _teacher_groups(world) -> set[int]:
    snapshot = world.http.get(
        f"/api/activities/{world.code}/snapshot", headers=world.headers
    ).json()
    return {g["number"] for g in snapshot["groups"]}


def _tabs(browser, context, count: int):
    return [browser.new_page(context) for _ in range(count)]


def _close_all(browser, tabs) -> None:
    for tab in tabs:
        close(browser, tab)


# ── US1 ──


def test_second_tab_shows_same_group(browser, world):
    """Scenario: 007 US1-AS1"""
    world.create()
    context = browser.new_context()
    a, b = _tabs(browser, context, 2)
    try:
        _join(a, world, 3)
        _student_page(b, world, with_code=True)
        b.wait_for(SHOWS_GROUP)
        assert _group_text(b) == "第 3 組"
        assert b.eval("document.getElementById('student-join').hidden") is True
        assert b.text("#student-credential") == a.text("#student-credential")
        assert_no_script_errors(a)
        assert_no_script_errors(b)
    finally:
        _close_all(browser, (a, b))


def test_second_tab_join_other_group_shows_message(browser, world):
    """Scenario: 007 US1-AS3

    同一瀏覽器的另一個分頁加入第 5 組：顯示「已是第 3 組成員」並切到第 3 組畫面，
    第 5 組沒有被建立。
    """
    world.create()
    context = browser.new_context()
    a, b = _tabs(browser, context, 2)
    try:
        _join(a, world, 3)
        _student_page(b, world)
        _submit_join(b, world.code, 5)
        b.wait_for(SHOWS_GROUP)
        assert _group_text(b) == "第 3 組"
        assert b.text("#student-error") == ALREADY
        assert _teacher_groups(world) == {3}
        assert_no_script_errors(b)
    finally:
        _close_all(browser, (a, b))


def test_reopen_by_entering_code_restores_group(browser, world):
    """Scenario: 007 US1-AS5

    關閉所有分頁（context 保留，等於瀏覽器的 cookie 還在）後重新打開：在加入畫面
    輸入代碼與任意組號，或以帶代碼的網址進入，都恢復為第 3 組。
    """
    world.create()
    context = browser.new_context()
    (first,) = _tabs(browser, context, 1)
    _join(first, world, 3)
    close(browser, first)
    c, d = _tabs(browser, context, 2)
    try:
        _student_page(c, world)
        _submit_join(c, world.code, 1)
        c.wait_for(SHOWS_GROUP)
        assert _group_text(c) == "第 3 組"
        _student_page(d, world, with_code=True)
        d.wait_for(SHOWS_GROUP)
        assert _group_text(d) == "第 3 組"
        assert _teacher_groups(world) == {3}
    finally:
        _close_all(browser, (c, d))


def test_wrong_code_in_url_shows_not_found(browser, world):
    """spec Edge Case：網址帶不存在的代碼時顯示「找不到」，不是「活動已失效」。"""
    (tab,) = _tabs(browser, browser.new_context(), 1)
    try:
        tab.goto(f"{world.server.base}/student.html?code=ZZZZZZ")
        tab.wait_for("document.getElementById('student-error').hidden === false")
        assert tab.text("#student-error") == "找不到這個活動代碼，請確認後再輸入。"
        assert tab.eval(SHOWS_JOIN) is True
        assert tab.eval("document.getElementById('sync-banner').hidden") is True
        assert_no_script_errors(tab)
    finally:
        close(browser, tab)


def test_document_cookie_hides_key(browser, world):
    """FR-008：瀏覽器金鑰是 HttpOnly，頁面程式碼讀不到；網址與畫面也沒有它。"""
    world.create()
    context = browser.new_context()
    (tab,) = _tabs(browser, context, 1)
    try:
        _join(tab, world, 2)
        assert "lq_browser" not in tab.eval("document.cookie")
        cookies = browser.call("Storage.getCookies", {"browserContextId": context})[
            "cookies"
        ]
        key = next(c["value"] for c in cookies if c["name"] == "lq_browser")
        assert next(c for c in cookies if c["name"] == "lq_browser")["httpOnly"]
        assert key not in tab.eval("location.href")
        assert key not in tab.text()
    finally:
        close(browser, tab)


# ── US2 ──


def test_join_in_one_tab_switches_other_tabs(browser, world):
    """Scenario: 007 US2-AS1（FR-010、SC-003）"""
    world.create()
    context = browser.new_context()
    a, b, c = _tabs(browser, context, 3)
    try:
        for tab in (a, b, c):
            _student_page(tab, world)
        _submit_join(a, world.code, 3)
        a.wait_for(SHOWS_GROUP)
        for tab in (b, c):
            tab.wait_for(SHOWS_GROUP, timeout=SYNC_SECONDS)
            assert _group_text(tab) == "第 3 組"
            assert tab.eval("location.search") == f"?code={world.code}"
            assert_no_script_errors(tab)
    finally:
        _close_all(browser, (a, b, c))


def test_leave_in_one_tab_resets_other_tabs(browser, world):
    """Scenario: 007 US2-AS2（SC-003）"""
    world.create()
    context = browser.new_context()
    a, b, c = _tabs(browser, context, 3)
    try:
        _join(a, world, 3)
        for tab in (b, c):
            _student_page(tab, world, with_code=True)
            tab.wait_for(SHOWS_GROUP)
        b.wait_for("document.getElementById('leave-group').disabled === false")
        b.click("#leave-group")
        for tab in (a, b, c):
            tab.wait_for(SHOWS_JOIN, timeout=SYNC_SECONDS + 1)
            tab.wait_for(
                "document.getElementById('student-error').textContent"
                ".includes('已離開本組')",
                timeout=SYNC_SECONDS,
            )
        assert _teacher_groups(world) == set()  # 從未提交、最後一個瀏覽器離開：釋放
    finally:
        _close_all(browser, (a, b, c))


def test_group_delete_resets_all_tabs(browser, world):
    """Scenario: 007 US2-AS4（SC-003）"""
    world.create()
    context = browser.new_context()
    a, b, c = _tabs(browser, context, 3)
    try:
        _join(a, world, 1)
        for tab in (b, c):
            _student_page(tab, world, with_code=True)
            tab.wait_for(SHOWS_GROUP)
        deleted = world.http.delete(
            f"/api/activities/{world.code}/groups/1", headers=world.headers
        )
        assert deleted.status_code == 200, deleted.text
        for tab in (a, b, c):
            tab.wait_for(SHOWS_JOIN, timeout=SYNC_SECONDS)
            tab.wait_for(
                "document.getElementById('student-error').textContent"
                ".includes('此組已被老師刪除')",
                timeout=SYNC_SECONDS,
            )
    finally:
        _close_all(browser, (a, b, c))


def test_missing_cookie_at_join_shows_message(browser, world):
    """FR-013：加入時瀏覽器沒有帶出身分 cookie，顯示提示，且不建立組別。

    CDP 沒有穩定的「封鎖 cookie」開關，這裡在頁面取得金鑰之後、按加入之前，清掉該
    瀏覽器的 cookie，模擬「瀏覽器沒有保存身分」。真的在瀏覽器設定中封鎖 cookie 的情況
    由 quickstart 人工步驟 13 驗證。
    """
    world.create()
    context = browser.new_context()
    (tab,) = _tabs(browser, context, 1)
    try:
        _student_page(tab, world)
        browser.call("Storage.clearCookies", {"browserContextId": context})
        _submit_join(tab, world.code, 2)
        tab.wait_for("document.getElementById('student-error').hidden === false")
        assert tab.text("#student-error") == (
            "瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。"
        )
        assert tab.eval(SHOWS_JOIN) is True
        assert _teacher_groups(world) == set()
    finally:
        close(browser, tab)


# ── US3 ──


def test_teacher_and_student_same_context(browser, world):
    """Scenario: 007 US3-AS1、US3-AS2

    同一個瀏覽器：老師頁建立活動，學生分頁加入第 1 組再離開；老師頁仍有控制權。
    """
    context = browser.new_context()
    teacher, student = _tabs(browser, context, 2)
    try:
        create_on_teacher_page(teacher, world)
        import_and_open_joining(world)
        _join(student, world, 1)
        assert world.api("POST", "/rounds").status_code == 201  # 頁面存下的老師 token
        assert world.api("POST", "/rounds/current/close").status_code == 200
        student.wait_for("document.getElementById('leave-group').disabled === false")
        student.click("#leave-group")
        student.wait_for(SHOWS_JOIN)
        teacher.call("Page.reload")
        teacher.wait_for("document.readyState === 'complete'")
        teacher.wait_for("document.getElementById('activity-info').hidden === false")
        assert teacher.text("#activity-code") == world.code
        assert_no_script_errors(teacher)
        assert_no_script_errors(student)
    finally:
        _close_all(browser, (teacher, student))
