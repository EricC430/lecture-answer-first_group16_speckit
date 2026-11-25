"""006 US4：狀態變化有一致的視覺語意與適度動畫。"""

import time

from tests.browser.ui_helpers import (
    assert_no_script_errors,
    break_sync,
    open_student,
    open_teacher,
    restore_sync,
    token_value,
    track_sockets,
)

LOOK = (
    "(sel=>{const e=document.querySelector(sel);if(!e)return null;const s=getComputedS"
    "tyle(e);"
    "const b=getComputedStyle(e,'::before');"
    "return [s.color,s.backgroundColor,(b.maskImage||b.webkitMaskImage||'none')!=='non"
    "e',"
    "e.textContent.trim().length>0];})"
)


def _look(page, selector):
    return page.eval(f"{LOOK}({selector!r})")


def test_status_labels_consistent_across_pages(page, world):
    """US4-AS1、FR-015：同一種狀態在老師頁與學生頁外觀相同，且有圖示＋文字。"""
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    world.submit(1, 3, 1, ["甲"])
    world.submit(1, 3, 2, ["乙"])
    world.close_round()
    world.judge(1, 3, 1, True)  # 組 1 答錯、組 2 遞補為搶答成功；第 4 題未成功
    open_teacher(page, world)
    page.wait_for("!!document.querySelector('.ranking-entry.status-wrong')")
    student = page.browser.new_page()
    open_student(student, world, 2)
    student.wait_for("!!document.querySelector('.ranking-line.status-success')")

    success_t = _look(page, ".ranking-entry.status-success > strong")
    success_s = _look(student, ".ranking-line.status-success > strong")
    assert success_t[:2] == success_s[:2], (success_t, success_s)
    assert success_t[0] == token_value(page, "--color-success")
    assert all(success_t[2:]) and all(success_s[2:])

    other = page.browser.new_page()
    open_student(other, world, 1)
    other.wait_for("!!document.querySelector('.ranking-line.status-wrong')")
    wrong_t = _look(page, ".ranking-entry.status-wrong > strong")
    wrong_s = _look(other, ".ranking-line.status-wrong > strong")
    assert wrong_t[:2] == wrong_s[:2], (wrong_t, wrong_s)
    assert wrong_t[0] == token_value(page, "--color-danger")

    unsolved_t = page.eval(
        "getComputedStyle([...document.querySelectorAll('.ranking-question > p')]"
        ".find(p=>p.textContent.trim()==='未成功')).color"
    )
    unsolved_s = other.eval(
        "getComputedStyle([...document.querySelectorAll('.ranking-line')]"
        ".find(l=>l.textContent.trim()==='未成功')).color"
    )
    assert unsolved_t == unsolved_s == token_value(page, "--color-neutral")
    for p in (page, student, other):
        assert_no_script_errors(p)


def test_reduced_motion_disables_animation(page, world):
    """US4-AS2、FR-016：減少動態效果時，新資料提示與分頁、按鈕過場都沒有動畫。"""
    page.emulate_media(reduced_motion=True)
    world.create()
    world.join(1)
    world.open_round([3])
    open_teacher(page, world)
    page.eval("new Promise(r => setTimeout(r, 1700))")
    page.eval(
        "window.__anim=[];new MutationObserver(()=>{document.querySelectorAll('.is-new"
        "').forEach(e=>{"
        "const s=getComputedStyle(e);window.__anim.push([s.animationName,s.animationDu"
        "ration]);});})"
        ".observe(document.body,{subtree:true,attributes:true,childList:true});true"
    )
    world.submit(1, 3, 1, ["甲"])
    page.wait_for("window.__anim.length > 0", 3)
    assert all(name == "none" for name, _ in page.eval("window.__anim")), page.eval(
        "window.__anim"
    )
    durations = page.eval(
        "[...document.querySelectorAll('button, [role=tab]')].map(b=>getComputedStyle("
        "b).transitionDuration)"
    )
    assert all(
        d in ("0s", "0ms") or set(d.replace("s", "").split(", ")) == {"0"}
        for d in durations
    ), durations
    page.emulate_media(reduced_motion=False)


def test_reconnect_shows_latest_without_flashback(page, world):
    """US4-AS3、FR-014 ↔ OpenSpec「重連或重啟」「延遲回應」：恢復連線後直接顯示最新結果
    ，不閃回舊的成功者。
    """
    track_sockets(page)
    world.create()
    world.join(1, 2)
    world.open_round([3])
    world.submit(1, 3, 1, ["甲"])
    world.submit(1, 3, 2, ["乙"])
    world.close_round()
    open_student(page, world, 2)
    page.wait_for("document.body.innerText.includes('目前搶答成功者：第 1 組')")
    break_sync(page)
    world.judge(1, 3, 1, True)  # 中斷期間結果改變：組 2 遞補
    restore_sync(page)
    page.wait_for("!document.body.classList.contains('sync-broken')", 15)
    page.wait_for(
        "document.body.innerText.includes('目前搶答成功者：（本組）第 2 組')", 5
    )
    samples = []
    for _ in range(6):
        samples.append(page.text("#ranking-review-student-list"))
        time.sleep(0.05)
    assert all("目前搶答成功者：第 1 組" not in s for s in samples)


def test_activity_gone_banner_uses_warning_style(page, world):
    """FR-013：活動失效提示（sync.js 的 gone）以與其他狀態一致的警示樣式顯示。"""
    world.create()
    world.join(1)
    open_student(page, world, 1)
    page.eval(
        "(()=>{const b=document.getElementById('sync-banner');"
        "b.textContent='活動已失效，請重新建立或加入活動';b.hidden=false;return true;}"
        ")()"
    )
    looks = _look(page, "#sync-banner")
    assert looks[0] == token_value(page, "--color-warning")
    assert looks[1] == token_value(page, "--color-warning-bg")
    assert looks[2] is True
