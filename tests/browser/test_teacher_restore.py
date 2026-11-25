"""老師頁在網址沒有 `?code=` 時找回老師身分（001 US1-AS2、FR-003；Issue #29）。

人工驗證時實際遇到：直接開 `teacher.html` 只看到建立表單，按建立又被 C7 拒絕，
畫面上沒有方法回到存續中的活動；以及同一個瀏覽器的學生分頁離開本組後，老師身分被刪除。

活動一律從老師頁的「建立活動」按鈕建立（PR #30 審查）：測試不自行寫入老師 token 或
`teacher:last`，驗證的是頁面建立活動時實際存下的身分。同一個瀏覽器的分頁共用
localStorage，所以「另開分頁」就是同一位老師在同一個瀏覽器開新分頁。
"""

from tests.browser.test_pages import assert_no_script_errors


def fresh_tab(browser):
    """在同一個瀏覽器開新分頁，第一次載入前清空這個來源的 localStorage。

    清空只做一次（以分頁的 sessionStorage 記錄），之後重新整理不會再清，
    才能驗證頁面自己寫入或清除的內容。
    """
    tab = browser.new_page()
    tab.add_init_script(
        "if (!sessionStorage.getItem('test:fresh')) {"
        "sessionStorage.setItem('test:fresh', '1'); localStorage.clear(); }"
    )
    return tab


def new_tab(browser):
    """在同一個瀏覽器開新分頁，不動任何儲存內容（共用老師身分）。"""
    return browser.new_page()


def close(browser, tab) -> None:
    """關閉分頁。"""
    browser.call("Target.closeTarget", {"targetId": tab.target_id})


def create_on_teacher_page(tab, world, max_groups: int = 3) -> None:
    """在老師頁按「建立活動」，並把頁面實際存下的代碼與老師 token 交給 `world`。"""
    tab.goto(f"{world.server.base}/teacher.html")
    tab.wait_for("document.getElementById('activity-create').hidden === false")
    tab.eval(
        f"document.getElementById('create-max-groups').value = '{max_groups}', true"
    )
    tab.click("#create-activity")
    tab.wait_for("document.getElementById('activity-info').hidden === false")
    world.code = tab.text("#activity-code")
    assert tab.eval("location.search") == f"?code={world.code}"
    assert tab.eval("localStorage.getItem('teacher:last')") == world.code
    token = tab.eval(f"localStorage.getItem('teacher:{world.code}')")
    assert token, "建立活動後老師頁沒有存下老師 token"
    world.teacher_token = token


def import_and_open_joining(world) -> None:
    """前置：以頁面存下的老師 token 匯入題目並開放加入（匯入不在本檔驗證範圍）。"""
    put = world.api("PUT", "/import/source", {"spreadsheetId": "sheet-1", "sheetId": 0})
    assert put.status_code == 200, put.text
    assert world.api("POST", "/import").status_code == 200
    assert world.api("POST", "/open-joining").status_code == 200


def join_on_student_page(tab, world, group: int) -> None:
    """在學生頁輸入活動代碼與組號加入。"""
    tab.goto(f"{world.server.base}/student.html")
    tab.eval(f"document.getElementById('join-code').value = '{world.code}', true")
    tab.eval(f"document.getElementById('join-number').value = '{group}', true")
    tab.eval("document.querySelector('#student-join').requestSubmit(), true")
    tab.wait_for("document.getElementById('student-info').hidden === false")


def test_teacher_page_without_code_returns_to_last_activity(browser, world):
    """Scenario: US1-AS2（同一個瀏覽器開新分頁進入老師頁面，老師身分恢復）。"""
    creator = fresh_tab(browser)
    other = new_tab(browser)
    try:
        create_on_teacher_page(creator, world)

        other.goto(f"{world.server.base}/teacher.html")
        other.wait_for("document.getElementById('activity-info').hidden === false")

        assert other.text("#activity-code") == world.code
        assert other.eval("location.search") == f"?code={world.code}"
        assert not other.visible("#activity-create")
        # 可以控制該活動：準備中的活動顯示「取消活動」
        other.wait_for("document.getElementById('cancel-activity').hidden === false")
        assert_no_script_errors(other)
    finally:
        close(browser, other)
        close(browser, creator)


def test_teacher_page_without_any_identity_shows_create_form(browser, world):
    """沒有任何老師身分的瀏覽器仍然只看到建立活動表單。"""
    tab = fresh_tab(browser)
    try:
        tab.goto(f"{world.server.base}/teacher.html")
        tab.wait_for("document.readyState === 'complete'")

        assert tab.visible("#activity-create")
        assert not tab.visible("#activity-info")
        assert tab.eval("location.search") == ""
        assert_no_script_errors(tab)
    finally:
        close(browser, tab)


def test_reload_after_new_activity_button_stays_on_create_form(browser, world):
    """取消活動、按「建立新活動」後，建立前重新整理：停在建立畫面，不回到舊活動。"""
    tab = fresh_tab(browser)
    try:
        create_on_teacher_page(tab, world)
        tab.wait_for("document.getElementById('cancel-activity').hidden === false")
        tab.click("#cancel-activity")
        tab.wait_for("document.getElementById('new-activity').hidden === false")

        tab.click("#new-activity")
        tab.wait_for("document.getElementById('activity-create').hidden === false")
        tab.call("Page.reload")
        tab.wait_for("document.readyState === 'complete'")
        tab.wait_for("document.getElementById('activity-create').hidden === false")

        assert not tab.visible("#activity-info")
        assert tab.eval("location.search") == ""
        # 建立新活動不會被已取消的舊活動擋住
        old = world.code
        tab.eval("document.getElementById('create-max-groups').value = '3', true")
        tab.click("#create-activity")
        tab.wait_for("document.getElementById('activity-info').hidden === false")
        assert tab.text("#activity-code") not in ("", old)
        assert_no_script_errors(tab)
    finally:
        close(browser, tab)


def test_student_leaving_in_same_browser_keeps_teacher_identity(browser, world):
    """同一個瀏覽器的學生分頁離開本組，不得刪掉老師身分（老師重新整理仍在活動裡）。

    人工驗證時實際遇到：老師與各組學生開在同一個瀏覽器的分頁，學生按「離開本組」後，
    老師頁重新整理就回到建立畫面，而且能再建立第二個活動（C7 被繞過）。
    """
    teacher = fresh_tab(browser)
    student = new_tab(browser)
    try:
        create_on_teacher_page(teacher, world)
        import_and_open_joining(world)

        join_on_student_page(student, world, 1)
        student.wait_for("document.getElementById('leave-group').disabled === false")
        student.click("#leave-group")
        student.wait_for("document.getElementById('student-join').hidden === false")

        token = teacher.eval(f"localStorage.getItem('teacher:{world.code}')")
        assert token == world.teacher_token
        teacher.call("Page.reload")
        teacher.wait_for("document.readyState === 'complete'")
        teacher.wait_for("document.getElementById('activity-info').hidden === false")
        assert teacher.text("#activity-code") == world.code
        assert_no_script_errors(teacher)
        assert_no_script_errors(student)
    finally:
        close(browser, student)
        close(browser, teacher)


def test_create_rejected_by_active_activity_switches_to_it(browser, world):
    """建立活動被 C7 拒絕時，直接回到存續中的活動，而不是卡在建立畫面。"""
    creator = fresh_tab(browser)
    other = new_tab(browser)
    try:
        create_on_teacher_page(creator, world)
        # 另一個分頁帶著沒有老師身分的代碼：停在建立表單並顯示需要老師身分
        other.goto(f"{world.server.base}/teacher.html?code=ZZZZZZ")
        other.wait_for("document.getElementById('activity-error').hidden === false")
        assert other.visible("#activity-create")

        other.click("#create-activity")
        other.wait_for("document.getElementById('activity-info').hidden === false")

        assert other.text("#activity-code") == world.code
        assert other.eval("location.search") == f"?code={world.code}"
        message = other.text("#activity-error")
        assert world.code in message
        assert "請先結束或取消它" in message  # FR-037
        assert_no_script_errors(other)
    finally:
        close(browser, other)
        close(browser, creator)
