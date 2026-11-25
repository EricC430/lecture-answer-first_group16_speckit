"""006 US2：學生在手機上清楚、安心地作答。"""

import json

from tests.browser.ui_helpers import (
    assert_no_script_errors,
    break_sync,
    open_student,
    open_teacher,
    track_sockets,
    wait_stage,
)

RECORD_STATES = (
    '(()=>{window.__states=[];const f=document.querySelector(\'form[data-question="3"'
    "]');"
    "window.__states.push(f.dataset.submitState);"
    "new MutationObserver(()=>window.__states.push(f.dataset.submitState))"
    ".observe(f,{attributes:true,attributeFilter:['data-submit-state']});return true;}"
    ")()"
)


def _fill(page, question: int, text: str) -> None:
    page.eval(
        f'(()=>{{const t=document.querySelector(\'form[data-question="{question}"] te'
        "xtarea');"
        f"t.value={json.dumps(text)};return true;}})()"
    )


def _submit(page, question: int) -> None:
    page.click(f'form[data-question="{question}"] button[type="submit"]')


def _open_round_page(page, world, questions=(3, 4), **round_kwargs):
    world.create()
    world.join(1, 2)
    if round_kwargs:
        body = {"questionNumbers": list(questions), **round_kwargs}
        assert world.api("POST", "/rounds", body).status_code == 201
    else:
        world.open_round(list(questions))
    open_student(page, world, 1)
    page.wait_for(
        f"document.querySelectorAll('form[data-question]').length === {len(questions)}"
    )


def test_submit_button_shows_busy_done_and_error_states(page, world):
    """US2-AS1、FR-009：送出中 → 已送出；後端拒絕時為送出失敗、訊息在該題內、按鈕可再操
    作。
    """
    _open_round_page(page, world)
    assert (
        page.eval(
            "document.querySelector('form[data-question=\"3\"]').dataset.submitState"
        )
        == "idle"
    )
    page.eval(RECORD_STATES)
    _fill(page, 3, "第一組的答案")
    _submit(page, 3)
    page.wait_for(
        "document.querySelector('form[data-question=\"3\"]').dataset.submitState === '"
        "done'"
    )
    states = page.eval("window.__states")
    assert states[:3] == ["idle", "busy", "done"] or (
        "busy" in states and states[-1] == "done"
    ), states

    # 空白答案：後端回 BLANK_EMPTY（真實拒絕）
    _fill(page, 4, "   ")
    _submit(page, 4)
    page.wait_for(
        "document.querySelector('form[data-question=\"4\"]').dataset.submitState === '"
        "error'"
    )
    form4 = 'form[data-question="4"]'
    assert page.visible(f"{form4} .submit-status.error-message")
    assert (
        page.eval(f"document.querySelector('{form4} button[type=\"submit\"]').disabled")
        is False
    )
    assert_no_script_errors(page)


def test_countdown_is_prominent_and_marks_urgent_without_blinking(page, world):
    """US2-AS2、FR-010：倒數大字；剩 10 秒內標示 data-urgent 且不閃爍；無倒數顯示由老師
    結束。
    """
    _open_round_page(page, world, countdownSeconds=8)
    page.wait_for(
        "document.getElementById('answer-countdown').textContent.includes('剩餘')"
    )
    size = page.eval(
        "parseFloat(getComputedStyle(document.getElementById('answer-countdown')).fontSize)"
    )
    assert size >= 24, size
    page.wait_for(
        "document.getElementById('student-countdown').hasAttribute('data-urgent')"
    )
    page.wait_for(
        "document.getElementById('answer-countdown').hasAttribute('data-urgent')"
    )
    assert (
        page.eval(
            "getComputedStyle(document.getElementById('answer-countdown')).animationName"
        )
        == "none"
    )


def test_no_countdown_round_says_teacher_ends(page, world):
    """US2-AS2 ↔ OpenSpec「無倒數輪次」：顯示既有文字「本輪沒有倒數，由老師結束。」。"""
    _open_round_page(page, world)
    page.wait_for(
        "document.getElementById('round-deadline-note').textContent.includes('由老師結束')"
    )
    assert "由老師結束" in page.text("#answer-countdown")


def test_html_answer_rendered_as_text(page, world):
    """US2-AS3、FR-011 ↔ OpenSpec「特殊文字答案」：老師頁與學生頁都以純文字顯示。"""
    _open_round_page(page, world)
    payload = '<img src=x onerror="window.__pwned=1">'
    _fill(page, 3, payload)
    _submit(page, 3)
    page.wait_for(
        "document.querySelector('form[data-question=\"3\"]').dataset.submitState === '"
        "done'"
    )
    assert payload in page.text('form[data-question="3"]')
    assert page.eval("document.querySelectorAll('#answer-forms img').length") == 0
    teacher = page.browser.new_page()
    open_teacher(teacher, world)
    teacher.wait_for(f"document.body.innerText.includes({json.dumps(payload)})")
    assert teacher.eval("document.querySelectorAll('main img').length") == 0
    assert teacher.eval("window.__pwned === undefined") is True
    assert page.eval("window.__pwned === undefined") is True


def test_sync_broken_banner_hides_success_and_does_not_cover_inputs(page, world):
    """US2-AS4、FR-012：中斷橫幅可見、成功文字隱藏、橫幅不遮住作答欄位與送出按鈕。"""
    track_sockets(page)
    _open_round_page(page, world)
    _fill(page, 3, "答案")
    _submit(page, 3)
    page.wait_for(
        "document.querySelector('form[data-question=\"3\"]').dataset.submitState === '"
        "done'"
    )
    page.eval("window.scrollTo(0, 0), true")
    break_sync(page)
    assert page.visible("#sync-banner")
    status = 'form[data-question="3"] .submit-status'
    assert (
        page.eval(f"getComputedStyle(document.querySelector('{status}')).visibility")
        == "hidden"
    )
    overlap = page.eval(
        "(()=>{const b=document.getElementById('sync-banner').getBoundingClientRect();"
        "const els=[document.querySelector('form[data-question=\"4\"] textarea'),"
        "document.querySelector('form[data-question=\"4\"] button[type=submit]')];"
        "els.forEach(e=>e.scrollIntoView({block:'center'}));"
        "const b2=document.getElementById('sync-banner').getBoundingClientRect();"
        "return els.some(e=>{const r=e.getBoundingClientRect();"
        "return r.top < b2.bottom && r.bottom > b2.top;});})()"
    )
    assert overlap is False


def test_student_page_shows_only_own_group_while_round_open(page, world):
    """US2-AS5、FR-002 ↔ OpenSpec「檢查學生資料回應」：學生頁與題號導覽只反映本組。"""
    _open_round_page(page, world)
    world.submit(1, 3, 2, ["第二組才有的答案"])
    wait_stage(page, "student-stage", "搶答中")
    page.eval("new Promise(r => setTimeout(r, 500))")
    assert "第二組才有的答案" not in page.text()
    assert "已送出" not in page.text("#question-nav")


def test_student_page_fits_375px_with_44px_targets(page, world):
    """US2-AS6、FR-007、FR-027：375px 無整頁水平捲動；可點擊元素至少 44×44。"""
    page.set_viewport(375, 812)
    _open_round_page(page, world)
    assert page.eval(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    small = page.eval(
        "[...document.querySelectorAll('button, a, input, textarea, select')]"
        ".filter(e => e.getClientRects().length > 0)"
        ".map(e => [e.tagName, e.id || e.textContent.trim().slice(0,10), "
        "e.getBoundingClientRect().width, e.getBoundingClientRect().height])"
        ".filter(([tag,,w,h]) => h < 44 || (tag !== 'TEXTAREA' && w < 44))"
    )
    assert small == [], small


def test_question_nav_lists_questions_with_own_status_and_moves_focus(page, world):
    """US2-AS7、FR-008a：多題時有題號導覽、顯示本組狀態、點擊移動焦點；導覽與倒數持續可見。"""
    _open_round_page(page, world)
    page.wait_for("!document.getElementById('question-nav').hidden")
    items = page.eval(
        "[...document.querySelectorAll('#question-nav a')].map(a => a.textContent)"
    )
    assert len(items) == 2 and all("未送出" in t for t in items), items
    _fill(page, 3, "答案")
    _submit(page, 3)
    page.wait_for(
        "document.querySelector('#question-nav a[data-question=\"3\"]').textContent.in"
        "cludes('已送出')"
    )
    page.click('#question-nav a[data-question="4"]')
    page.wait_for(
        "document.activeElement && document.activeElement.id === 'q-heading-4'"
    )
    # 捲到最底：導覽與本組資訊列仍在視窗內（FR-008）
    page.eval("window.scrollTo(0, document.body.scrollHeight), true")
    inside = page.eval(
        "['answer-sticky'].every(id=>{const r=document.getElementById(id).getBoundingC"
        "lientRect();"
        "return r.top >= 0 && r.bottom <= innerHeight;})"
    )
    assert inside is True
    assert "第 1 組" in page.text("#answer-sticky")


def test_question_nav_hidden_for_single_question(page, world):
    """FR-008a：只開一題時不顯示題號導覽。"""
    _open_round_page(page, world, questions=(3,))
    page.eval("new Promise(r => setTimeout(r, 300))")
    assert page.eval("document.getElementById('question-nav').hidden") is True
