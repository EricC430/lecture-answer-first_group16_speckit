"""老師頁在網址沒有 `?code=` 時找回老師身分（001 US1-AS2、FR-003；Issue #29）。

人工驗證時實際遇到：直接開 `teacher.html` 只看到建立表單，按建立又被 C7 拒絕，
畫面上沒有方法回到存續中的活動。
"""

import json

from tests.browser.test_pages import assert_no_script_errors, open_student


def store_teacher(page, world) -> None:
    """在這個瀏覽器放入老師身分與「最後建立的活動」（和人工建立活動後相同）。

    只在分頁第一次載入時放入（init script 每次載入都會執行），重新整理時保留頁面
    自己寫入或清除的內容。
    """
    page.add_init_script(
        "if (!sessionStorage.getItem('test:seeded')) {"
        "sessionStorage.setItem('test:seeded', '1');"
        "localStorage.clear();"
        f"localStorage.setItem('teacher:{world.code}', "
        f"{json.dumps(world.teacher_token)});"
        f"localStorage.setItem('teacher:last', {json.dumps(world.code)});"
        "}"
    )


def test_teacher_page_without_code_returns_to_last_activity(page, world):
    """Scenario: US1-AS2（同一個瀏覽器開新分頁進入老師頁面，老師身分恢復）。"""
    world.create()
    store_teacher(page, world)

    page.goto(f"{world.server.base}/teacher.html")
    page.wait_for("document.getElementById('activity-info').hidden === false")

    assert page.text("#activity-code") == world.code
    assert page.eval("location.search") == f"?code={world.code}"
    assert not page.visible("#activity-create")
    # 可以控制該活動：開放加入的活動顯示取消按鈕
    page.wait_for("document.getElementById('cancel-activity').hidden === false")
    assert_no_script_errors(page)


def test_teacher_page_without_any_identity_shows_create_form(page, world):
    """沒有任何老師身分的瀏覽器仍然只看到建立活動表單。"""
    page.add_init_script("localStorage.clear();")
    page.goto(f"{world.server.base}/teacher.html")
    page.wait_for("document.readyState === 'complete'")

    assert page.visible("#activity-create")
    assert not page.visible("#activity-info")
    assert page.eval("location.search") == ""
    assert_no_script_errors(page)


def test_reload_after_new_activity_button_stays_on_create_form(page, world):
    """取消活動、按「建立新活動」後，建立前重新整理：停在建立畫面，不回到舊活動。"""
    world.create()
    store_teacher(page, world)
    page.goto(f"{world.server.base}/teacher.html?code={world.code}")
    page.wait_for("document.getElementById('cancel-activity').hidden === false")
    page.click("#cancel-activity")
    page.wait_for("document.getElementById('new-activity').hidden === false")

    page.click("#new-activity")
    page.wait_for("document.getElementById('activity-create').hidden === false")
    page.call("Page.reload")
    page.wait_for("document.readyState === 'complete'")
    page.wait_for("document.getElementById('activity-create').hidden === false")

    assert not page.visible("#activity-info")
    assert page.eval("location.search") == ""
    # 建立新活動不會被已取消的舊活動擋住
    page.eval("document.getElementById('create-max-groups').value = '3', true")
    page.click("#create-activity")
    page.wait_for("document.getElementById('activity-info').hidden === false")
    assert page.text("#activity-code") not in ("", world.code)
    assert_no_script_errors(page)


def test_student_leaving_in_same_browser_keeps_teacher_identity(page, browser, world):
    """同一個瀏覽器的學生分頁離開本組，不得刪掉老師身分（老師重新整理仍在活動裡）。

    人工驗證時實際遇到：老師與各組學生開在同一個瀏覽器的分頁，學生按「離開本組」後，
    老師頁重新整理就回到建立畫面，而且能再建立第二個活動（C7 被繞過）。
    """
    world.create()
    world.join(1)
    store_teacher(page, world)
    page.goto(f"{world.server.base}/teacher.html?code={world.code}")
    page.wait_for("document.getElementById('activity-info').hidden === false")

    student = browser.new_page()
    try:
        open_student(student, world, 1)
        student.wait_for("document.getElementById('leave-group').disabled === false")
        student.click("#leave-group")
        student.wait_for("document.getElementById('student-join').hidden === false")
    finally:
        browser.call("Target.closeTarget", {"targetId": student.target_id})

    assert page.eval(f"localStorage.getItem('teacher:{world.code}')") is not None
    page.call("Page.reload")
    page.wait_for("document.readyState === 'complete'")
    page.wait_for("document.getElementById('activity-info').hidden === false")
    assert page.text("#activity-code") == world.code
    assert_no_script_errors(page)


def test_create_rejected_by_active_activity_switches_to_it(page, world):
    """建立活動被 C7 拒絕時，直接回到存續中的活動，而不是卡在建立畫面。"""
    world.create()
    store_teacher(page, world)
    # 網址帶著一個這個瀏覽器沒有老師身分的代碼：停在建立表單並顯示需要老師身分
    page.goto(f"{world.server.base}/teacher.html?code=ZZZZZZ")
    page.wait_for("document.getElementById('activity-error').hidden === false")
    assert page.visible("#activity-create")

    page.click("#create-activity")
    page.wait_for("document.getElementById('activity-info').hidden === false")

    assert page.text("#activity-code") == world.code
    assert page.eval("location.search") == f"?code={world.code}"
    message = page.text("#activity-error")
    assert world.code in message
    assert "請先結束或取消它" in message  # FR-037
    assert_no_script_errors(page)
