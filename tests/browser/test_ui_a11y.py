"""006 US6：符合無障礙基本要求（鍵盤、對比、錯誤訊息、縮放）。"""

import json

from tests.browser.ui_helpers import open_teacher, wait_stage
from tests.unit.ui.tokens import contrast_ratio

FOCUS_RING = (
    "(()=>{const e=document.activeElement;if(!e||e===document.body)return null;"
    "const s=getComputedStyle(e);return [e.id||e.tagName, parseFloat(s.outlineWidth), "
    "s.outlineStyle];})()"
)


def _key(page, key: str, code: int, shift: bool = False) -> None:
    modifiers = 8 if shift else 0
    page.call(
        "Input.dispatchKeyEvent",
        type="rawKeyDown",
        key=key,
        code=key,
        windowsVirtualKeyCode=code,
        modifiers=modifiers,
    )
    page.call(
        "Input.dispatchKeyEvent",
        type="keyUp",
        key=key,
        code=key,
        windowsVirtualKeyCode=code,
        modifiers=modifiers,
    )


def _tab_to(page, selector: str, limit: int = 80) -> None:
    """只按 Tab 直到焦點落在 selector；每一步都檢查焦點外框清楚可見（≥ 3px）。"""
    for _ in range(limit):
        _key(page, "Tab", 9)
        ring = page.eval(FOCUS_RING)
        if ring is not None:
            assert ring[1] >= 3 and ring[2] != "none", ring
        if page.eval(f"document.activeElement.matches({json.dumps(selector)})"):
            return
    raise AssertionError(f"按 {limit} 次 Tab 都沒有到達 {selector}")


def _enter(page) -> None:
    page.call(
        "Input.dispatchKeyEvent",
        type="keyDown",
        key="Enter",
        code="Enter",
        windowsVirtualKeyCode=13,
        text="\r",
    )
    page.call(
        "Input.dispatchKeyEvent",
        type="keyUp",
        key="Enter",
        code="Enter",
        windowsVirtualKeyCode=13,
    )


def test_keyboard_only_teacher_and_student_flow(page, world):
    """US6-AS1、FR-026、SC-004：只用鍵盤完成老師的開放加入 → 開輪 → 關輪，以及學生的加入
    → 送出。
    """
    created = world.http.post("/api/activities", json={"maxGroups": 6})
    world.code = created.json()["code"]
    world.teacher_token = created.json()["teacherToken"]
    world.api("PUT", "/import/source", {"spreadsheetId": "sheet-1", "sheetId": 0})
    assert (
        world.api("POST", "/import").status_code == 200
    )  # 匯入需要 Google 選檔，不在鍵盤測試範圍
    open_teacher(page, world)
    wait_stage(page, "activity-stage", "準備中")

    _tab_to(page, "#open-joining")
    _enter(page)
    wait_stage(page, "activity-stage", "開放加入")

    student = page.browser.new_page()
    student.goto(f"{world.server.base}/student.html")
    _tab_to(student, "#join-code")
    student.call("Input.insertText", text=world.code)
    _tab_to(student, "#join-number")
    student.call("Input.insertText", text="1")
    _tab_to(student, "#student-join button[type=submit]")
    _enter(student)
    student.wait_for("document.getElementById('student-info').hidden === false")

    page.wait_for("document.querySelectorAll('#open-round-questions input').length > 0")
    _tab_to(page, "#open-round-panel button[type=submit]")
    _enter(page)
    wait_stage(page, "activity-stage", "搶答中")

    student.wait_for("document.querySelectorAll('form[data-question]').length > 0")
    number = student.eval(
        "[...document.querySelectorAll('form[data-question]')]"
        ".find(f=>f.querySelectorAll('textarea').length===1).dataset.question"
    )
    _tab_to(student, f'form[data-question="{number}"] textarea')
    student.call("Input.insertText", text="鍵盤作答")
    _tab_to(student, f'form[data-question="{number}"] button[type=submit]')
    _enter(student)
    student.wait_for(
        f"document.querySelector('form[data-question=\"{number}\"]').dataset.submitSta"
        "te === 'done'"
    )

    _tab_to(page, "#close-round")
    _enter(page)
    wait_stage(page, "activity-stage", "結果未定案")


def test_contrast_tokens_meet_aa(page, world):
    """US6-AS2、FR-025：抽查三頁實際渲染的文字／背景組合（不只檢查設計基準值）。"""
    world.create()
    world.join(1)
    open_teacher(page, world)
    pairs = page.eval(
        "(()=>{const rgb=c=>{const m=c.match(/\\d+(\\.\\d+)?/g);return m?m.slice(0,3)."
        "map(Number):null;};"
        "const bg=e=>{for(let n=e;n;n=n.parentElement){const c=getComputedStyle(n).bac"
        "kgroundColor;"
        "if(c&&!c.startsWith('rgba(0, 0, 0, 0')&&c!=='transparent')return c;}return 'r"
        "gb(255, 255, 255)';};"
        "return [...document.querySelectorAll('h1,h2,h3,p,label,th,td,button,span,stro"
        "ng,li,a')]"
        ".filter(e=>e.getClientRects().length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))"
        ".filter(e=>!e.closest('#sync-status'))"
        ".map(e=>[e.id||e.tagName+':'+e.textContent.trim().slice(0,8),rgb(getComputedStyle(e).color),rgb(bg(e))]);})()"
    )
    assert pairs

    def hex_of(values):
        return "#" + "".join(f"{int(v):02x}" for v in values)

    failing = [
        (name, round(contrast_ratio(hex_of(fg), hex_of(bg)), 2))
        for name, fg, bg in pairs
        if contrast_ratio(hex_of(fg), hex_of(bg)) < 4.5
    ]
    assert failing == [], failing


def test_field_errors_near_field_and_announced(page, world):
    """US6-AS3、FR-028：錯誤訊息緊鄰表單、role=alert、欄位以 aria-describedby 關聯；欄位
    有可見標籤。
    """
    page.goto(f"{world.server.base}/student.html")
    labels = page.eval(
        "['join-code','join-number','join-credential'].map(id=>{const i=document.getEl"
        "ementById(id);"
        "const l=i.closest('label');return !!l && l.textContent.replace(i.value,'').tr"
        "im().length>0;})"
    )
    assert all(labels), labels
    page.eval(
        "document.getElementById('join-code').value='NOPE99';"
        "document.getElementById('join-number').value='1';true"
    )
    page.click("#student-join button[type=submit]")
    page.wait_for("!document.getElementById('student-error').hidden")
    assert (
        page.eval("document.getElementById('student-error').getAttribute('role')")
        == "alert"
    )
    gap = page.eval(
        "document.getElementById('student-join').getBoundingClientRect().top - "
        "document.getElementById('student-error').getBoundingClientRect().bottom"
    )
    assert 0 <= gap <= 48, gap
    described = page.eval(
        "['join-code','join-number','join-credential'].every(id=>"
        "(document.getElementById(id).getAttribute('aria-describedby')||'').includes('student-error'))"
    )
    assert described is True


def test_zoom_200_percent_no_overlap(page, world):
    """FR-029：模擬 200% 縮放（720×450 CSS 像素）時。

    沒有整頁水平捲動，主要按鈕互不重疊。
    """
    world.create()
    world.join(1)
    page.set_viewport(720, 450, scale=2)
    for path in (
        "index.html",
        f"teacher.html?code={world.code}",
        "student.html",
        "projection.html",
    ):
        if path.startswith("teacher"):
            open_teacher(page, world)
        else:
            page.goto(f"{world.server.base}/{path}")
        assert page.eval(
            "document.documentElement.scrollWidth <= document.documentElement.clientWi"
            "dth"
        ), path
        overlaps = page.eval(
            "(()=>{const b=[...document.querySelectorAll('button, a')].filter(e=>e.get"
            "ClientRects().length)"
            ".map(e=>e.getBoundingClientRect());let n=0;for(let i=0;i<b.length;i++)for"
            "(let j=i+1;j<b.length;j++){"
            "const x=b[i],y=b[j];if(x.left<y.right-1&&y.left<x.right-1&&x.top<y.bottom"
            "-1&&y.top<x.bottom-1)n++;}"
            "return n;})()"
        )
        assert overlaps == 0, (path, overlaps)
