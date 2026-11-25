"""006 US1：三個頁面套用一致的新視覺，且功能與顯示資訊不變。"""

from tests.browser.ui_helpers import (
    assert_no_script_errors,
    computed,
    open_student,
    open_teacher,
    token_value,
    wait_stage,
)


def _check_shared_styles(page) -> None:
    assert computed(page, "body", "background-color") == token_value(
        page, "--color-canvas"
    )
    heading = computed(page, "h1", "font-family")
    assert heading.startswith('"Noto Serif TC 600"'), heading
    radius = page.eval(
        "Math.min(...[...document.querySelectorAll('button, .button')]"
        ".filter(b => b.getClientRects().length > 0)"
        ".map(b => parseFloat(getComputedStyle(b).borderTopLeftRadius)))"
    )
    assert radius >= 22, radius  # 膠囊形（999px 會被瀏覽器夾在高度一半）


def test_pages_use_shared_component_styles(page, world):
    """US1-AS1：三頁使用同一套背景、標題字體、膠囊按鈕與錯誤訊息樣式。"""
    page.goto(f"{world.server.base}/index.html")
    assert computed(page, "body", "background-color") == token_value(
        page, "--color-canvas"
    )
    assert computed(page, "h1", "font-family").startswith('"Noto Serif TC 600"')

    world.create()
    world.join(1)
    open_teacher(page, world)
    _check_shared_styles(page)
    # 錯誤訊息樣式：讓既有元素顯示後檢查底色
    page.eval(
        "(()=>{const e=document.getElementById('activity-error');"
        "e.textContent='測試';e.hidden=false;return true;})()"
    )
    assert computed(page, "#activity-error", "background-color") == token_value(
        page, "--color-danger-bg"
    )
    assert_no_script_errors(page)

    other = page.browser.new_page()
    open_student(other, world, 1)
    _check_shared_styles(other)
    assert_no_script_errors(other)


def _teacher_info(page) -> dict:
    return page.eval(
        "(()=>{const t=id=>(document.getElementById(id)||{}).textContent?.trim()??null;"
        "return {code:t('activity-code'),max:t('activity-max-groups'),"
        "stage:t('activity-stage'),questions:t('activity-questions'),"
        "rows:document.querySelectorAll('#groups-body tr').length};})()"
    )


def _student_info(page) -> dict:
    return page.eval(
        "(()=>{const t=id=>(document.getElementById(id)||{}).textContent?.trim()??null;"
        "return {code:t('student-code'),group:t('student-group'),"
        "credential:t('student-credential'),stage:t('student-stage')};})()"
    )


def test_information_items_unchanged_through_full_flow(page, world):
    """US1-AS2、FR-001、FR-002：各階段畫面上的資訊與後端快照一致；搶答中學生看不到他組答案。"""
    world.create(max_groups=6)
    world.join(1, 2)
    open_teacher(page, world)
    student = page.browser.new_page()
    open_student(student, world, 1)

    def check(stage_label: str) -> None:
        wait_stage(page, "activity-stage", stage_label)
        wait_stage(student, "student-stage", stage_label)
        snap = world.api("GET", "/snapshot").json()
        info = _teacher_info(page)
        assert info["code"] == snap["code"]
        assert info["max"] == str(snap["maxGroups"])
        assert info["rows"] == len(snap["groups"])
        own = _student_info(student)
        assert own["code"] == snap["code"]
        assert "1" in own["group"]
        group1 = next(g for g in snap["groups"] if g["number"] == 1)
        assert own["credential"] == group1["credential"]

    check("開放加入")
    world.open_round([3, 4])
    check("搶答中")
    world.submit(1, 3, 2, ["第二組的祕密答案"])
    page.wait_for("document.body.innerText.includes('第二組的祕密答案')")  # 老師看得到
    assert "第二組的祕密答案" not in student.text()  # 學生看不到他組（FR-002）
    world.submit(1, 3, 1, ["第一組答案"])
    world.close_round()
    check("結果未定案")
    world.judge(1, 3, 2, True)
    world.finalize()
    check("結果已定案")
    assert world.api("POST", "/end").status_code == 200
    check("已結束")
    page.wait_for("!document.getElementById('export-section').hidden")
    page.click("#export-preview-button")
    page.wait_for("!document.getElementById('export-preview').hidden", 15)
    assert "第一組答案" in page.text("#export-preview")
    assert_no_script_errors(page)
    assert_no_script_errors(student)
