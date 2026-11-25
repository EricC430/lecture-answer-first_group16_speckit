"""006 US7：老師可以投影給全班看的唯讀畫面（contracts/projection-view.md）。"""

import json
import time

from tests.browser.ui_helpers import (
    assert_no_script_errors,
    break_sync,
    open_projection,
    open_teacher,
    track_sockets,
)

PRIVATE_KEYS = [
    "reason",
    "countAtProcessing",
    "groupCounts",
    "actions",
    "ownGroup",
    "groups",
    "credential",
    "token",
    "teacherToken",
    "deviceCount",
]
ROUND_FORBIDDEN_KEYS = [
    "answers",
    "entries",
    "groupNumber",
    "order",
    "receivedAt",
    "results",
]


def _view(page, world, snapshot: dict | None = None) -> dict:
    """在瀏覽器以 ES module 載入真正的 projection-view.js，對真實後端的老師快照呼叫純函
    式。
    """
    snap = snapshot if snapshot is not None else world.api("GET", "/snapshot").json()
    if page.eval("location.href") == "about:blank":
        page.goto(f"{world.server.base}/index.html")
    return page.eval(
        "import('/js/projection-view.js')"
        f".then(m => m.toProjectionView({json.dumps(snap)}, true))"
    )


def _keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(v) for v in value)) if value else set()
    return set()


def _round_open_with_answers(world) -> None:
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    world.submit(1, 3, 1, ["甲組祕密答案"])
    world.submit(1, 3, 2, ["乙組祕密答案"])


def test_projection_view_whitelist_round_open(page, world):
    """禁止事項 1、FR-032：搶答中輸出 mode=round，不含任何答案或組別資料。"""
    _round_open_with_answers(world)
    snap = world.api("GET", "/snapshot").json()
    assert "甲組祕密答案" in json.dumps(
        snap, ensure_ascii=False
    )  # 老師快照確實含答案（負對照）
    view = _view(page, world, snap)
    assert view["mode"] == "round"
    text = json.dumps(view, ensure_ascii=False)
    assert "祕密答案" not in text, text
    assert not (_keys(view) & set(ROUND_FORBIDDEN_KEYS)), _keys(view)
    assert view["questionNumbers"] == [3, 4]


def test_projection_view_whitelist_never_leaks_private_fields(page, world):
    """禁止事項 2、FR-031：任何階段都不含理由、成功次數、操作、組別表、憑證或 token。"""
    world.create()
    world.join(1, 2)
    views = [_view(page, world)]
    world.open_round([3])
    world.submit(1, 3, 1, ["甲"])
    world.submit(1, 3, 2, ["乙"])
    views.append(_view(page, world))
    world.close_round()
    snap = world.api("GET", "/snapshot").json()
    assert "reason" in json.dumps(snap)  # 老師快照確實含理由（負對照）
    views.append(_view(page, world, snap))
    world.finalize()
    views.append(_view(page, world))
    world.api("POST", "/end")
    views.append(_view(page, world))
    for view in views:
        leaked = _keys(view) & set(PRIVATE_KEYS)
        assert not leaked, (view["mode"], leaked)
        assert world.teacher_token not in json.dumps(view)


def test_projection_view_only_current_round(page, world):
    """禁止事項 3、US7-AS7：只輸出目前輪；下一輪搶答中沒有 results。"""
    world.create()
    world.join(1, 2)
    world.open_round([3])
    world.submit(1, 3, 1, ["第一輪答案"])
    world.close_round()
    world.finalize()
    world.open_round([4])
    view = _view(page, world)
    assert view["mode"] == "round" and "results" not in view
    assert "第一輪答案" not in json.dumps(view, ensure_ascii=False)
    world.submit(2, 4, 2, ["第二輪答案"])
    world.close_round()
    view = _view(page, world)
    assert view["mode"] == "results"
    assert [card["questionNumber"] for card in view["results"]] == [4]


def test_open_projection_from_teacher_page(page, world):
    """US7-AS1、FR-030：老師頁的按鈕開啟 projection.html?code=…；投影畫面沒有任何操作元
    件。
    """
    world.create()
    open_teacher(page, world)
    page.wait_for("!document.getElementById('open-projection').hidden")
    page.eval(
        "window.__opened=null;window.open=(u,t,f)=>{window.__opened=[u,t,f];return nul"
        "l;};true"
    )
    page.click("#open-projection")
    url, target, features = page.eval("window.__opened")
    assert (
        url == f"projection.html?code={world.code}"
        and target == "_blank"
        and "noopener" in features
    )
    assert world.teacher_token not in url
    proj = page.browser.new_page()
    open_projection(proj, world)
    proj.wait_for(
        "document.getElementById('projection-code').textContent === "
        f"{json.dumps(world.code)}"
    )
    assert (
        proj.eval(
            "document.querySelectorAll('button, input, form, select, textarea').length"
        )
        == 0
    )
    assert_no_script_errors(proj)


def test_projection_lobby_shows_large_code(page, world):
    """US7-AS2、FR-036：1920×1080 下代碼字級 ≥ 8% 畫面高，其餘文字 ≥ 24px；1280×720 不捲
    動可見代碼。
    """
    world.create()
    page.set_viewport(1920, 1080)
    open_projection(page, world)
    page.wait_for(
        "document.getElementById('projection-code').textContent === "
        f"{json.dumps(world.code)}"
    )
    size = page.eval(
        "parseFloat(getComputedStyle(document.getElementById('projection-code')).fontSize)"
    )
    assert size >= 1080 * 0.08, size
    smallest = page.eval(
        "Math.min(...[...document.querySelectorAll('#projection-root *')]"
        ".filter(e=>e.childNodes.length && [...e.childNodes].some(n=>n.nodeType===3&&n"
        ".textContent.trim()))"
        ".map(e=>parseFloat(getComputedStyle(e).fontSize)))"
    )
    assert smallest >= 24, smallest
    page.set_viewport(1280, 720)
    bottom = page.eval(
        "document.getElementById('projection-code').getBoundingClientRect().bottom"
    )
    assert bottom <= 720, bottom


def test_projection_hides_answers_while_round_open(page, world):
    """US7-AS3、FR-032、SC-010：搶答中投影畫面不含任何答案、組號或送出數量；重新整理後仍然如此。"""
    _round_open_with_answers(world)
    open_projection(page, world)
    page.wait_for(
        "document.getElementById('projection-stage').textContent.includes('搶答中')"
    )
    for _ in range(2):
        body = page.text("#projection-root")
        assert "祕密答案" not in body
        assert "第 1 組" not in body and "第 2 組" not in body
        assert "第 3 題" in body and "第 4 題" in body
        page.goto(f"{world.server.base}/projection.html?code={world.code}")
        page.wait_for(
            "document.getElementById('projection-stage').textContent.includes('搶答中')"
        )


def test_projection_results_cards_after_close(page, world):
    """US7-AS4、FR-033 ↔ OpenSpec「結果公布與後續輪次」：每題一張卡片，依送出先後列出組
    號、答案、順位、狀態。
    """
    world.create()
    world.join(1, 2)
    world.open_round([3, 4])
    world.submit(1, 3, 2, ["<b>乙</b>"])
    world.submit(1, 3, 1, ["甲"])
    world.close_round()
    open_projection(page, world)
    page.wait_for("document.querySelectorAll('.projection-card').length === 2")
    card3 = page.text('.projection-card[data-question="3"]')
    assert card3.index("第 2 組") < card3.index("第 1 組")  # 依送出先後
    assert "<b>乙</b>" in card3 and "搶答成功" in card3
    assert page.eval("document.querySelectorAll('#projection-results b').length") == 0
    assert page.eval(
        '!!document.querySelector(\'.projection-card[data-question="3"] .projection-e'
        "ntry.is-winner')"
    )
    assert "未成功" in page.text('.projection-card[data-question="4"]')


def _results_world(world):
    world.create()
    world.join(1, 2)
    world.open_round([3])
    world.submit(1, 3, 1, ["甲"])
    world.submit(1, 3, 2, ["乙"])
    world.close_round()


def test_projection_shows_replacement_within_2s(page, world):
    """US7-AS5、FR-034、FR-035：判錯後 2 秒內顯示答錯與「第 N 組遞補」；量 10 次。"""
    delays = []
    for _ in range(10):
        _results_world(world)
        open_projection(page, world)
        page.wait_for("document.querySelectorAll('.projection-entry').length === 2")
        start = time.time()
        world.judge(1, 3, 1, True)
        page.wait_for(
            "document.querySelector('.projection-card[data-question=\"3\"]').textConte"
            "nt.includes('第 2 組遞補')",
            2,
        )
        delays.append(time.time() - start)
        card = page.text('.projection-card[data-question="3"]')
        assert "答錯" in card
    assert max(delays) <= 2.0, delays
    print(f"遞補延遲（秒）：max={max(delays):.3f} 全部={[round(d, 3) for d in delays]}")


def test_projection_undo_restores_within_2s(page, world):
    """US7-AS6：撤銷判錯後 2 秒內恢復原成功者。"""
    _results_world(world)
    open_projection(page, world)
    page.wait_for("document.querySelectorAll('.projection-entry').length === 2")
    world.judge(1, 3, 1, True)
    page.wait_for("document.body.innerText.includes('第 2 組遞補')", 2)
    world.judge(1, 3, 1, False)
    page.wait_for(
        "document.querySelector('.projection-entry.is-winner')?.dataset.group === '1'",
        2,
    )


def test_projection_final_and_next_round(page, world):
    """US7-AS7：定案後標示結果已定案；開下一輪時結果卡片立即消失。"""
    _results_world(world)
    open_projection(page, world)
    page.wait_for("document.querySelectorAll('.projection-card').length === 1")
    world.finalize()
    page.wait_for(
        "document.getElementById('projection-stage').textContent.includes('結果已定案')"
    )
    world.open_round([4])
    page.wait_for(
        "document.getElementById('projection-stage').textContent.includes('搶答中')"
    )
    assert page.eval("document.querySelectorAll('.projection-card').length") == 0


def test_projection_ended_and_cancelled(page, world):
    """US7-AS8：結束時顯示未成功題；取消時顯示已取消。"""
    _results_world(world)
    world.finalize()
    world.api("POST", "/end")
    open_projection(page, world)
    page.wait_for(
        "document.getElementById('projection-stage').textContent.includes('已結束')"
    )
    assert "未成功題" in page.text("#projection-root")
    world.create()  # 新活動（同一 world 換代碼）
    world.api("POST", "/cancel")
    open_projection(page, world)
    page.wait_for(
        "document.getElementById('projection-stage').textContent.includes('已取消')"
    )


def test_projection_sync_broken_hides_winner(page, world):
    """US7-AS9：同步中斷時顯示中斷提示，不顯示可能過時的成功者。"""
    track_sockets(page)
    _results_world(world)
    open_projection(page, world)
    page.wait_for("!!document.querySelector('.projection-entry.is-winner')")
    break_sync(page)
    assert page.visible("#sync-banner")
    assert page.eval(
        "getComputedStyle(document.querySelector('.projection-entry.is-winner')).visibility"
    ) == "hidden" or not page.visible("#projection-results")


def test_projection_without_teacher_token_shows_hint(page, world):
    """Edge Case：沒有老師 token（例如學生打開連結）時只顯示提示，不建立同步連線。"""
    track_sockets = (
        "window.__ws=0;const W=window.WebSocket;window.WebSocket=function(...a){window"
        ".__ws++;return new W(...a);};"
    )
    world.create()
    page.add_init_script(track_sockets)
    open_projection(page, world, with_token=False)
    page.wait_for("document.body.innerText.includes('請從老師頁開啟投影畫面')")
    time.sleep(0.3)
    assert page.eval("window.__ws") == 0


def test_projection_stale_result_version_ignored(page, world):
    """contracts「版本處理」↔ OpenSpec「延遲回應」：較小 resultVersion 的結果不覆蓋較新
    的結果。
    """
    _results_world(world)
    open_projection(page, world)
    page.wait_for("document.querySelectorAll('.projection-entry').length === 2")
    old = world.api("GET", "/snapshot").json()
    world.judge(1, 3, 1, True)
    page.wait_for("document.body.innerText.includes('第 2 組遞補')", 2)
    page.eval(f"window.__projectionRender({json.dumps(old)})")
    time.sleep(0.2)
    assert "第 2 組遞補" in page.text("#projection-results")
    assert (
        page.eval("document.querySelector('.projection-entry.is-winner').dataset.group")
        == "2"
    )


def test_projection_paginates_when_cards_overflow(page, world):
    """FR-037：放不下時自動分頁輪播，不需老師操作；每一頁都是完整卡片，各題的成功者一定會出現。"""
    world.create()
    world.join(1, 2, 3, 4, 5, 6)
    world.open_round([1, 2, 3, 4])
    long = "很長的答案" * 30
    for group in range(1, 7):
        world.submit(1, 3, group, [f"{long}{group}"])
        world.submit(1, 4, group, [f"{long}{group}"])
    world.close_round()
    page.set_viewport(1280, 720)
    open_projection(page, world)
    page.wait_for("document.querySelectorAll('.projection-card').length === 4")
    page.wait_for("!!document.getElementById('projection-results').dataset.page", 3)
    pages = page.eval("document.getElementById('projection-results').dataset.page")
    assert pages.split("/")[1] != "1", pages
    # 每張有成功者的卡片都有 .is-winner，而且卡片整張出現在某一頁（沒有被切掉）
    winners = page.eval(
        "[...document.querySelectorAll('.projection-card')].filter(c=>!c.querySelector('.projection-unsolved'))"
        ".map(c=>!!c.querySelector('.projection-entry.is-winner'))"
    )
    assert winners and all(winners), winners
    visible_now = page.eval(
        "[...document.querySelectorAll('.projection-card')].filter(c=>!c.hidden).length"
    )
    assert 0 < visible_now < 4
