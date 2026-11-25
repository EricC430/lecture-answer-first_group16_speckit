"""006 US3：老師一眼掌握活動進度並找到下一步操作（兩欄、分頁、階段進度、主要按鈕）。"""

import json

import pytest

from tests.browser.ui_helpers import (
    assert_no_script_errors,
    computed,
    open_teacher,
    token_value,
    wait_stage,
)
from tests.fixtures.guided_notes_layouts import defect_cases

LABELS = {
    "PREPARING": "準備中",
    "JOINING": "開放加入",
    "ROUND_OPEN": "搶答中",
    "RESULT_PENDING": "結果未定案",
    "RESULT_FINAL": "結果已定案",
    "ENDED": "已結束",
}

PRIMARY = {
    "PREPARING": "#open-joining",
    "JOINING": "#open-round-panel button[type=submit]",
    "ROUND_OPEN": "#close-round",
    "RESULT_PENDING": ".ranking-finalize",
    "RESULT_FINAL": "#open-round-panel button[type=submit]",
    "ENDED": "#export-preview-button",
}

TAB_FOR = {
    "PREPARING": "tab-import",
    "JOINING": "tab-import",
    "ROUND_OPEN": "tab-board",
    "RESULT_PENDING": "tab-ranking",
    "RESULT_FINAL": "tab-ranking",
    "ENDED": "tab-export",
}

VISIBLE_PRIMARY = (
    "(()=>{const p=getComputedStyle(document.querySelector('#teacher-sidebar')).getPro"
    "pertyValue('--color-primary');"
    "const span=document.createElement('span');span.style.color='var(--color-primary)';"
    "document.body.append(span);const want=getComputedStyle(span).color;span.remove();"
    "const panel=document.querySelector('[role=tabpanel]:not([hidden])');"
    "const scope=[...document.querySelectorAll('#teacher-sidebar button')]"
    ".concat(panel?[...panel.querySelectorAll('button')]:[]);"
    "return scope.filter(b=>b.getClientRects().length>0 && getComputedStyle(b).backgro"
    "undColor===want)"
    ".map(b=>b.id||b.className||b.textContent.trim());})()"
)


def _selected_tab(page) -> str | None:
    return page.eval(
        "(document.querySelector('#teacher-tabs [role=tab][aria-selected=true]')||{})."
        "id||null"
    )


def _walk(page, world, on_stage) -> None:
    """建立（準備中）→ … → 已結束，每個階段呼叫 on_stage(stage)。"""
    created = world.http.post("/api/activities", json={"maxGroups": 6})
    world.code = created.json()["code"]
    world.teacher_token = created.json()["teacherToken"]
    world.api("PUT", "/import/source", {"spreadsheetId": "sheet-1", "sheetId": 0})
    assert world.api("POST", "/import").status_code == 200
    open_teacher(page, world)
    stage = "PREPARING"
    wait_stage(page, "activity-stage", LABELS[stage])
    on_stage(stage)
    assert world.api("POST", "/open-joining").status_code == 200
    world.join(1, 2)
    for stage, action in [
        ("JOINING", None),
        ("ROUND_OPEN", lambda: world.open_round([3, 4])),
        (
            "RESULT_PENDING",
            lambda: (
                world.submit(1, 3, 1, ["甲"]),
                world.submit(1, 3, 2, ["乙"]),
                world.close_round(),
            ),
        ),
        ("RESULT_FINAL", world.finalize),
        ("ENDED", lambda: world.api("POST", "/end")),
    ]:
        if action:
            action()
        wait_stage(page, "activity-stage", LABELS[stage])
        page.eval("new Promise(r => setTimeout(r, 300))")
        on_stage(stage)


def test_stage_progress_marks_current_stage_with_text(page, world):
    """US3-AS1、FR-017：左欄階段進度以文字標示目前階段（aria-current=step）。"""

    def check(stage):
        current = page.eval(
            "(document.querySelector('#stage-progress [aria-current=step]')||{}).textC"
            "ontent||''"
        )
        assert LABELS[stage] in current, (stage, current)
        assert page.eval(
            "document.getElementById('teacher-sidebar').contains(document.getElementById('stage-progress'))"
        )

    _walk(page, world, check)
    assert_no_script_errors(page)


def test_exactly_one_primary_button_per_stage(page, world):
    """US3-AS2、FR-018：每階段只有一個主要按鈕，且是對照表中的下一步；取消、結束為危險樣式。"""

    def check(stage):
        if stage == "RESULT_PENDING":
            page.wait_for("document.querySelector('.ranking-finalize') !== null")
        found = page.eval(VISIBLE_PRIMARY)
        expected = page.eval(
            f"(()=>{{const e=document.querySelector({json.dumps(PRIMARY[stage])});"
            "return e.id||e.className||e.textContent.trim();})()"
        )
        assert found == [expected], (stage, found)
        for danger in ("#cancel-activity", "#end-activity"):
            if page.visible(danger):
                assert computed(page, danger, "color") == token_value(
                    page, "--color-danger"
                )

    _walk(page, world, check)


def test_new_submission_row_is_highlighted_without_stealing_focus(page, world):
    """US3-AS3、FR-020：作答看板的新資料有短暫提示，且不搶走焦點。"""
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    open_teacher(page, world)
    page.wait_for("!document.getElementById('round-submission-section').hidden")
    page.eval("new Promise(r => setTimeout(r, 1700))")  # 頁面剛載入的內容不算新資料
    page.eval("document.getElementById('close-round').focus(), true")
    page.eval(
        "window.__sawNew=false;new MutationObserver(()=>{if(document.querySelector('#t"
        "eacher-workspace .is-new'))"
        "window.__sawNew=true;}).observe(document.body,{subtree:true,attributes:true,childList:true});true"
    )
    world.submit(1, 3, 1, ["新答案"])
    page.wait_for("window.__sawNew === true", 3)
    page.wait_for("document.querySelector('#teacher-workspace .is-new') === null", 3)
    assert page.eval("document.activeElement.id") == "close-round"


def test_ranking_status_labels_and_judge_button_adjacent(page, world):
    """US3-AS4：每個候選有狀態標籤（文字＋圖示）；判錯按鈕與目前成功者同一列。"""
    world.create()
    world.join(1, 2)
    world.open_round([3])
    world.submit(1, 3, 1, ["甲"])
    world.submit(1, 3, 2, ["乙"])
    world.close_round()
    open_teacher(page, world)
    page.wait_for("document.querySelectorAll('.ranking-entry').length >= 2")
    labels = page.eval(
        "[...document.querySelectorAll('.ranking-entry > strong')].map(s=>"
        "[s.textContent.trim(), getComputedStyle(s,'::before').maskImage || getCompute"
        "dStyle(s,'::before').webkitMaskImage])"
    )
    assert all(text and icon and icon != "none" for text, icon in labels), labels
    # 004 把判錯按鈕放在該題區塊（不改 004 腳本，contracts/ui-dom.md）：
    # 按鈕與目前成功者在同一題區塊，
    # 且文字標明成功者的組號
    same_block = page.eval(
        "(()=>{const e=document.querySelector('.ranking-entry.status-success');"
        "const block=e&&e.closest('.ranking-question');const b=block&&block.querySelec"
        "tor('button.ranking-action');"
        r"const group=e.querySelector('strong').textContent.match(/第 (\d+) 組/)[1];"
        "return !!b && b.textContent.includes(`第 ${group} 組`);})()"
    )
    assert same_block is True


def test_export_confirm_disabled_until_preview_and_replacements_marked(page, world):
    """US3-AS5：預覽前「確認寫回」停用；覆寫影響以危險色呈現。"""
    world.create()
    world.join(1)
    world.open_round([3])
    world.submit(1, 3, 1, ["甲"])
    world.close_round()
    world.finalize()
    world.api("POST", "/end")
    open_teacher(page, world)
    page.wait_for("!document.getElementById('export-section').hidden")
    assert (
        page.eval("document.getElementById('export-confirm-button').disabled") is True
    )
    page.click("#export-preview-button")
    page.wait_for("!document.getElementById('export-preview').hidden", 15)
    color = page.eval(
        "(()=>{const s=document.createElement('span');s.className='export-impact-repla"
        "ce';"
        "document.getElementById('export-preview').append(s);const c=getComputedStyle("
        "s).color;"
        "s.remove();return c;})()"
    )
    assert color == token_value(page, "--color-danger")


def test_import_issues_table_readable(page, world):
    """US3-AS6：匯入失敗時問題以表格呈現，每列五欄，表格在可捲動容器內。"""
    case = defect_cases()["missing_number_header"]
    world.server.reader.add("sheet-bad", "壞的學習單", [(0, "壞", case.snapshot)])
    created = world.http.post("/api/activities", json={"maxGroups": 6})
    world.code = created.json()["code"]
    world.teacher_token = created.json()["teacherToken"]
    world.api("PUT", "/import/source", {"spreadsheetId": "sheet-bad", "sheetId": 0})
    open_teacher(page, world)
    page.wait_for("!document.getElementById('import-section').hidden")
    page.eval("document.getElementById('import-run').hidden=false, true")
    page.click("#import-run")
    page.wait_for("!document.getElementById('import-issues').hidden", 10)
    rows = page.eval(
        "[...document.querySelectorAll('#import-issues-body tr')].map(r=>r.children.le"
        "ngth)"
    )
    assert rows and all(n == 5 for n in rows), rows
    assert page.eval(
        "!!document.getElementById('import-issues-body').closest('.table-scroll')"
    )


def test_two_column_layout_with_sticky_sidebar(page, world):
    """US3-AS7、FR-017a：1280 寬時左右兩欄；右欄捲動時左欄仍可見。"""
    page.set_viewport(1280, 800)
    world.create()
    world.join(1, 2)
    open_teacher(page, world)
    side = page.eval(
        "document.getElementById('teacher-sidebar').getBoundingClientRect().toJSON()"
    )
    work = page.eval(
        "document.getElementById('teacher-workspace').getBoundingClientRect().toJSON()"
    )
    assert side["right"] <= work["left"] + 1, (side, work)
    assert abs(side["top"] - work["top"]) < 40
    page.eval(
        "document.getElementById('teacher-workspace').style.minHeight='4000px';"
        "window.scrollTo(0, 1500);true"
    )
    top = page.eval(
        "document.getElementById('teacher-sidebar').getBoundingClientRect().top"
    )
    assert 0 <= top < 200, top


def test_tabs_auto_switch_only_on_stage_change(page, world):
    """US3-AS8、FR-017b：依階段自動切換；同一階段內手動選擇不會被切走。"""
    selected = {}

    def check(stage):
        page.wait_for(
            f"document.getElementById('{TAB_FOR[stage]}').getAttribute('aria-selected')==='true'"
        )
        selected[stage] = _selected_tab(page)
        if stage == "ROUND_OPEN":
            page.click("#tab-import")
            world.submit(1, 4, 2, ["丙"])  # 同一階段的新快照
            page.eval("new Promise(r => setTimeout(r, 600))")
            assert _selected_tab(page) == "tab-import"

    _walk(page, world, check)
    assert selected == {k: TAB_FOR[k] for k in selected}


def test_updated_badge_on_background_tab(page, world):
    """US3-AS9、FR-017c：背景分頁有新資料時出現「有更新」，不自動跳轉；打開後消失。"""
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    open_teacher(page, world)
    page.wait_for(
        "document.getElementById('tab-board').getAttribute('aria-selected')==='true'"
    )
    page.eval("new Promise(r => setTimeout(r, 1700))")  # 剛載入時的補畫不算「有更新」
    page.click("#tab-import")
    world.submit(1, 3, 1, ["甲"])
    page.wait_for("!!document.querySelector('#tab-board .tab-badge')", 3)
    assert "有更新" in page.text("#tab-board")
    assert _selected_tab(page) == "tab-import"
    page.click("#tab-board")
    page.wait_for("!document.querySelector('#tab-board .tab-badge')")


def test_tab_visibility_follows_section_visibility(page, world):
    """US3-AS10、FR-017d：分頁是否出現與面板內區塊的 hidden 一致；取消的活動沒有寫回分頁
    。
    """
    created = world.http.post("/api/activities", json={"maxGroups": 6})
    world.code = created.json()["code"]
    world.teacher_token = created.json()["teacherToken"]
    open_teacher(page, world)
    page.eval("new Promise(r => setTimeout(r, 400))")

    def consistent():
        return page.eval(
            "[...document.querySelectorAll('#teacher-tabs [role=tab]')].map(t=>{"
            "const panel=document.getElementById(t.getAttribute('aria-controls'));"
            "const anyShown=[...panel.querySelectorAll('section[data-feature]')].some("
            "s=>!s.hidden);"
            "return [t.id, !t.hidden, anyShown];})"
        )

    for tab, shown, any_section in consistent():
        assert shown == any_section, (tab, shown, any_section)
    assert world.api("POST", "/cancel").status_code == 200
    wait_stage(page, "activity-stage", "已取消")
    page.eval("new Promise(r => setTimeout(r, 400))")
    for tab, shown, any_section in consistent():
        assert shown == any_section, (tab, shown, any_section)
    assert page.eval("document.getElementById('tab-export').hidden") is True


def test_single_column_below_1024(page, world):
    """US3-AS11：寬度小於 1024 時單欄（左欄在上），沒有整頁水平捲動。"""
    page.set_viewport(1000, 800)
    world.create()
    open_teacher(page, world)
    side = page.eval(
        "document.getElementById('teacher-sidebar').getBoundingClientRect().toJSON()"
    )
    work = page.eval(
        "document.getElementById('teacher-workspace').getBoundingClientRect().toJSON()"
    )
    assert side["bottom"] <= work["top"] + 1, (side, work)
    assert page.eval(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )


@pytest.mark.parametrize("key", ["ArrowRight"])
def test_tabs_keyboard_navigation(page, world, key):
    """FR-017e：分頁列可用方向鍵移動焦點、Enter 選取；aria 屬性正確。"""
    world.create()
    world.join(1)
    world.open_round([3])
    open_teacher(page, world)
    page.wait_for(
        "document.getElementById('tab-board').getAttribute('aria-selected')==='true'"
    )
    page.eval("document.getElementById('tab-board').focus(), true")
    before = page.eval("document.activeElement.id")
    page.call(
        "Input.dispatchKeyEvent",
        type="keyDown",
        key=key,
        code=key,
        windowsVirtualKeyCode=39,
    )
    page.call(
        "Input.dispatchKeyEvent",
        type="keyUp",
        key=key,
        code=key,
        windowsVirtualKeyCode=39,
    )
    after = page.eval("document.activeElement.id")
    assert after != before and after.startswith("tab-"), (before, after)
    page.call(
        "Input.dispatchKeyEvent",
        type="keyDown",
        key="Enter",
        code="Enter",
        windowsVirtualKeyCode=13,
    )
    page.call(
        "Input.dispatchKeyEvent",
        type="keyUp",
        key="Enter",
        code="Enter",
        windowsVirtualKeyCode=13,
    )
    assert _selected_tab(page) == after
    attrs = page.eval(
        "[...document.querySelectorAll('#teacher-tabs [role=tab]')].map(t=>"
        "[t.getAttribute('aria-selected'), t.tabIndex, !!document.getElementById(t.get"
        "Attribute('aria-controls'))])"
    )
    assert all(ctrl for *_, ctrl in attrs)
    assert sum(1 for sel, *_ in attrs if sel == "true") == 1
    assert all((tab == 0) == (sel == "true") for sel, tab, _ in attrs)
