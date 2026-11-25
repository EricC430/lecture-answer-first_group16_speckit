"""真實瀏覽器裡的老師頁與學生頁（人工測試發現的問題；每個測試都對應一個實際看到的錯誤）。"""

import json


def assert_no_script_errors(page) -> None:
    """頁面不得有 JS 錯誤（瀏覽器自動要 favicon 的 404 不算）。"""
    real = [e for e in page.errors if "Failed to load resource" not in e]
    assert real == [], real


def open_student(page, world, group: int) -> None:
    """以該組裝置的身分開學生頁（身分放在分頁的 sessionStorage，與人工加入相同）。"""
    page.add_init_script(
        f"sessionStorage.setItem('device:{world.code}', "
        f"{json.dumps(world.devices[group])});"
    )
    page.goto(f"{world.server.base}/student.html?code={world.code}")
    page.wait_for("document.getElementById('student-info').hidden === false")


def open_teacher(page, world) -> None:
    """以老師身分開老師頁。"""
    page.add_init_script(
        f"localStorage.setItem('teacher:{world.code}', "
        f"{json.dumps(world.teacher_token)});"
        f"localStorage.setItem('teacher:last', {json.dumps(world.code)});"
    )
    page.goto(f"{world.server.base}/teacher.html?code={world.code}")
    page.wait_for("document.getElementById('activity-info').hidden === false")


def test_student_sees_latest_winner_answer_and_own_status_while_teacher_judges(
    page, world
):
    """學生頁在老師判錯階段要看到各題最新的搶答成功組別、答案、狀態與本組各題的狀態。"""
    world.create()
    world.join(1, 2, 3)
    world.open_round()
    world.submit(1, 3, 1, ["甲的答案"])  # 題 3（單題）：組 1 最早
    world.submit(1, 3, 2, ["乙的答案"])
    world.submit(1, 4, 2, ["乙的第四題"])  # 題 4：只有組 2
    world.close_round()

    open_student(page, world, 3)  # 組 3 什麼都沒提交
    page.wait_for(
        "document.getElementById('student-stage').textContent.includes('結果未定案')"
    )
    page.wait_for("!document.getElementById('ranking-review-student-section').hidden")
    shown = page.text("#ranking-review-student-list")
    assert "第 3 題" in shown and "第 1 組" in shown and "甲的答案" in shown, shown
    assert "搶答成功" in shown
    assert "第 4 題" in shown and "乙的第四題" in shown, shown
    assert "第 1 題" in shown and "未成功" in shown, shown  # 沒人提交的題也要看到

    # 老師把題 3 目前的搶答成功者（組 1）判錯 → 學生頁要即時更新成組 2，並看到組 1 答錯
    world.judge(1, 3, 1, True)
    page.wait_for(
        "document.getElementById('ranking-review-student-list').innerText.includes('乙的答案')"
    )
    shown = page.text("#ranking-review-student-list")
    assert "目前搶答成功者：第 2 組" in shown, shown
    assert "答錯" in shown and "甲的答案" in shown, shown  # 剛被判錯的前一組一起顯示
    assert "結果已更新" in shown, shown
    assert_no_script_errors(page)

    # 組 2 的學生頁：本組各題的狀態
    other = page.browser.new_page()
    open_student(other, world, 2)
    other.wait_for("!document.getElementById('ranking-review-student-section').hidden")
    own = other.text("#ranking-review-student-list")
    assert "目前搶答成功者：（本組）第 2 組" in own, (
        own
    )  # 判錯後組 2 遞補成為搶答成功者
    assert "乙的第四題" in own and "乙的答案" in own, own


def test_open_round_panel_defaults_to_unsolved_questions_only(page, world):
    """老師開下一輪時，預設勾選的題目不可包含已搶答正確的題。"""
    world.create()
    world.join(1, 2)
    world.open_round()  # 預設全部 4 題
    world.submit(1, 3, 1, ["甲的答案"])  # 只有第 3 題有人成功
    world.close_round()
    world.finalize()

    open_teacher(page, world)
    page.wait_for("document.getElementById('open-round-panel').hidden === false")
    page.wait_for("document.querySelectorAll('#open-round-questions input').length > 0")
    offered = page.eval(
        "[...document.querySelectorAll('#open-round-questions input')]"
        ".map(i => Number(i.value))"
    )
    checked = page.eval(
        "[...document.querySelectorAll('#open-round-questions input:checked')]"
        ".map(i => Number(i.value))"
    )
    assert offered == [1, 2, 4], offered
    assert checked == [1, 2, 4], checked
    assert_no_script_errors(page)


def test_creating_new_activity_clears_previous_activity_screen(page, world):
    """結束活動後建立新活動，舊活動的匯入預覽、作答、順位與組別都不得殘留。"""
    world.create()
    world.join(1, 2)
    world.open_round()
    world.submit(1, 3, 1, ["舊活動的答案"])
    world.close_round()
    world.finalize()
    assert world.api("POST", "/end").status_code == 200

    open_teacher(page, world)
    page.wait_for("document.getElementById('new-activity').hidden === false")
    page.wait_for("!document.getElementById('ranking-review-section').hidden")
    assert "舊活動的答案" in page.text("#ranking-review-list")
    assert page.text("#import-preview-body") != ""
    page.click("#export-preview-button")  # 舊活動留下寫回預覽
    page.wait_for("document.getElementById('export-preview').hidden === false")
    assert "舊活動的答案" in page.text("#export-preview-body")

    page.click("#new-activity")
    for section in [
        "import-section",
        "round-submission-section",
        "published-section",
        "ranking-review-section",
        "export-section",
    ]:
        assert not page.visible(f"#{section}"), f"{section} 在建立畫面仍然顯示"

    page.eval("document.getElementById('create-max-groups').value = '3', true")
    page.click("#create-activity")
    page.wait_for("document.getElementById('activity-info').hidden === false")
    page.wait_for(
        "document.getElementById('activity-code').textContent !== "
        f"{json.dumps(world.code)}"
    )
    page.wait_for("document.getElementById('import-section').hidden === false")

    assert page.text("#import-preview-body") == ""
    assert not page.visible("#import-preview")
    assert page.text("#ranking-review-list") == ""
    assert not page.visible("#ranking-review-section")
    assert page.text("#export-preview-body") == ""
    assert not page.visible("#export-preview")
    assert page.text("#submission-board") == ""
    assert page.text("#published-list") == ""
    assert "舊活動" not in page.text()
    assert_no_script_errors(page)
