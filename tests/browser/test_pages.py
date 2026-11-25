"""真實瀏覽器裡的老師頁與學生頁（人工測試發現的問題；每個測試都對應一個實際看到的錯誤）。"""

import json


def assert_no_script_errors(page) -> None:
    """頁面不得有 JS 錯誤（瀏覽器自動要 favicon 的 404 不算）。"""
    real = [e for e in page.errors if "Failed to load resource" not in e]
    assert real == [], real


def open_student(page, world, group: int) -> None:
    """以該組瀏覽器的身分開學生頁（007：把該組的瀏覽器金鑰寫成 HttpOnly cookie）。

    模擬「這個瀏覽器先前已加入」。不同組要開在不同的瀏覽器 context（見 `student_tab`），
    否則同一瀏覽器的 cookie 會互相覆蓋（research R8）。
    """
    page.browser.set_cookie(
        page.context_id,
        world.server.base,
        "lq_browser",
        world.devices[group],
        httponly=True,
    )
    page.goto(f"{world.server.base}/student.html?code={world.code}")
    page.wait_for("document.getElementById('student-info').hidden === false")


def student_tab(browser):
    """在另一個獨立的瀏覽器開分頁（每組學生一個瀏覽器）。"""
    return browser.new_page(browser.new_context())


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
    other = student_tab(page.browser)
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


def test_student_joining_new_activity_does_not_keep_previous_answers(page, world):
    """學生換到新活動後，作答表單與已輸入的答案不得沿用上一個活動的內容。"""
    world.create()
    world.join(1)
    world.open_round()
    open_student(page, world, 1)
    page.wait_for("document.querySelectorAll('#answer-forms textarea').length > 0")
    page.eval(
        "document.querySelector('#answer-forms textarea').value = '上一個活動的答案',"
        " true"
    )
    world.close_round()
    world.finalize()
    assert world.api("POST", "/end").status_code == 200
    page.wait_for("document.getElementById('new-join').hidden === false")

    page.click("#new-join")  # 加入其他活動
    world.create()  # 新活動（老師另開）；第 1 輪、同題號
    page.eval(
        f"document.getElementById('join-code').value = {json.dumps(world.code)}, true"
    )
    page.eval("document.getElementById('join-number').value = '1', true")
    page.eval("document.querySelector('#student-join').requestSubmit(), true")
    page.wait_for("document.getElementById('student-info').hidden === false")
    world.open_round()
    page.wait_for("document.querySelectorAll('#answer-forms textarea').length > 0")
    values = page.eval(
        "[...document.querySelectorAll('#answer-forms textarea')].map(t => t.value)"
    )
    assert all(v == "" for v in values), values
    assert "上一個活動" not in page.text()
    assert_no_script_errors(page)


def test_static_files_are_revalidated_not_cached_blindly(world):
    """靜態檔不得被瀏覽器盲目快取（否則更新後要強制重新整理才會換成新腳本）。"""
    response = world.http.get("/js/student.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_teacher_overview_shows_stage_winners_and_solved_count(page, world):
    """006：老師頁的本輪總覽依快照顯示階段、各題勝出組別與已定案的成功題數。

    Scenario: US1-AS1、US1-AS2、US1-AS3、US1-AS4、US1-AS5
    """
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    world.submit(1, 3, 2, ["乙的答案"])
    open_teacher(page, world)
    page.wait_for("!document.getElementById('overview-section').hidden")
    page.wait_for(
        "document.querySelector('#stage-track li.now')?.dataset.stage === 'ROUND_OPEN'"
    )
    tiles = page.text("#overview-questions")
    assert "Q3" in tiles and "作答中・1 組送出" in tiles, tiles
    assert tiles.count("未出題") == 2, tiles  # 題 1、題 2 還沒開過

    world.close_round()
    page.wait_for(
        "document.getElementById('overview-stage').textContent === '結果未定案'"
    )
    page.wait_for(
        "document.getElementById('overview-questions')"
        ".innerText.includes('第 2 組・待定案')"
    )
    assert page.text("#overview-score") == "0／4"

    world.finalize()
    page.wait_for(
        "document.getElementById('overview-questions')"
        ".innerText.includes('第 2 組・第 1 輪')"
    )
    assert page.text("#overview-score") == "1／4"
    assert page.text("#overview-questions").count("第 1 輪未成功") == 1  # 題 4 沒人提交
    # 記號只是裝飾：第 2 組的記號是方形（data-shape=2），且不帶文字
    shape = page.eval(
        "document.querySelector('#overview-questions .ov-solved .gl').dataset.shape"
    )
    assert shape == "2"
    assert_no_script_errors(page)


def test_group_glyphs_accompany_group_numbers_on_both_pages(page, world):
    """006：組別表、作答看板、順位列與學生頁本組都有幾何記號，且文字仍寫「第 N 組」。

    Scenario: US2-AS1、US2-AS2
    """
    world.create()
    world.join(1, 2)
    world.open_round([3])
    world.submit(1, 3, 2, ["乙的答案"])
    open_teacher(page, world)
    page.wait_for("document.querySelectorAll('#groups-body .gl').length === 2")
    page.wait_for("document.querySelectorAll('#submission-board th .gl').length === 2")
    assert "第 2 組" in page.text("#groups-body")
    world.close_round()
    page.wait_for(
        "document.querySelector('#ranking-review-list .ranking-entry .gl') !== null"
    )
    entry = page.eval(
        "(() => { const li = document.querySelector("
        "'#ranking-review-list .ranking-entry');"
        " return { shape: li.querySelector('.gl').dataset.shape,"
        " text: li.innerText }; })()"
    )
    assert entry["shape"] == "2" and "第 2 組" in entry["text"], entry

    student = student_tab(page.browser)
    open_student(student, world, 2)
    student.wait_for("document.querySelector('#student-glyph .gl') !== null")
    assert (
        student.eval("document.querySelector('#student-glyph .gl').dataset.shape")
        == "2"
    )
    assert student.text("#student-group") == "第 2 組"
    assert_no_script_errors(page)
    assert_no_script_errors(student)


def test_student_countdown_ring_follows_deadline_only_while_round_is_open(page, world):
    """006：有倒數的輪次顯示圓環與剩餘秒數；沒有倒數或不在搶答中時隱藏。

    Scenario: US3-AS1、US3-AS2
    """
    world.create()
    world.join(1)
    response = world.api(
        "POST", "/rounds", {"questionNumbers": [3], "countdownSeconds": 120}
    )
    assert response.status_code == 201, response.text
    open_student(page, world, 1)
    page.wait_for("!document.getElementById('student-pie').hidden")
    seconds = int(page.text("#student-pie-number"))
    assert 100 <= seconds <= 120, seconds
    left = page.eval(
        "parseFloat(document.getElementById('student-pie').style.getPropertyValue('--left'))"
    )
    assert 80 <= left <= 100, left

    world.close_round()
    page.wait_for("document.getElementById('student-pie').hidden")
    world.finalize()
    world.open_round([4])  # 沒有倒數
    page.wait_for(
        "document.getElementById('student-stage').textContent.includes('搶答中')"
    )
    assert page.eval("document.getElementById('student-pie').hidden") is True
    assert_no_script_errors(page)


def test_pages_fit_phone_width_without_horizontal_scroll(page, world):
    """006：375 寬的手機畫面，首頁、老師頁、學生頁都沒有整頁水平捲動。

    Scenario: US4-AS3
    """
    world.create()
    world.join(1, 2, 3, 4, 5, 6)
    world.open_round([1, 3])
    world.submit(1, 1, 2, ["需求規格", "驗收測試"])
    world.close_round()
    page.call(
        "Emulation.setDeviceMetricsOverride",
        width=375,
        height=812,
        deviceScaleFactor=1,
        mobile=True,
    )
    overflow = (
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    page.goto(f"{world.server.base}/index.html")
    assert page.eval(overflow) <= 0
    open_teacher(page, world)
    page.wait_for("!document.getElementById('ranking-review-section').hidden")
    assert page.eval(overflow) <= 0
    student = student_tab(page.browser)
    student.call(
        "Emulation.setDeviceMetricsOverride",
        width=375,
        height=812,
        deviceScaleFactor=1,
        mobile=True,
    )
    open_student(student, world, 2)
    student.wait_for(
        "!document.getElementById('ranking-review-student-section').hidden"
    )
    assert student.eval(overflow) <= 0
