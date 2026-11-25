"""006 US5：首頁與空狀態使用手繪插圖；離線完整。"""

import json
from urllib.parse import urlparse

from tests.browser.ui_helpers import open_projection, open_student, open_teacher


def _assert_rendered(page, scope: str) -> None:
    """插圖真的畫出來了：<use> 參照的內容有實際尺寸（外部 SVG 解析失敗時 getBBox 為 0）
    。
    """
    page.wait_for(
        f"(()=>{{const u=[...document.querySelectorAll({json.dumps(scope + ' use')})];"
        "return u.length>0 && u.every(x=>{const b=x.getBBox();return b.width>10&&b.hei"
        "ght>10;});})()",
        5,
    )


def test_home_has_title_illustration_and_role_links(page, world):
    """US5-AS1、FR-021：系統名稱、說明、主插圖（有替代文字）與兩個大入口，可用鍵盤到達。"""
    page.goto(f"{world.server.base}/index.html")
    assert "課堂搶答" in page.text("h1")
    assert page.eval(
        "document.querySelector('.home-lead').textContent.trim().length > 10"
    )
    alt = page.eval(
        "(()=>{const h=document.querySelector('.home-hero');const img=h.querySelector("
        "'img');"
        "if(img) return img.alt; const svg=h.querySelector('svg'); return svg.getAttri"
        "bute('aria-label');})()"
    )
    assert alt and len(alt) > 5, alt
    _assert_rendered(page, ".home-hero")
    for link, href in (
        ("#role-teacher", "teacher.html"),
        ("#role-student", "student.html"),
    ):
        assert (
            page.eval(
                f"document.querySelector({json.dumps(link)}).getAttribute('href')"
            )
            == href
        )
        size = page.eval(
            f"document.querySelector({json.dumps(link)}).getBoundingClientRect().toJSON()"
        )
        assert size["width"] >= 44 and size["height"] >= 44, size
        assert page.eval(f"document.querySelector({json.dumps(link)}).tabIndex") == 0


def test_empty_states_show_illustration_and_next_step(page, world):
    """US5-AS2、FR-022：尚無組別、尚未匯入（老師）、尚未開輪（學生）時顯示插圖＋下一步說明。"""
    created = world.http.post("/api/activities", json={"maxGroups": 6})
    world.code = created.json()["code"]
    world.teacher_token = created.json()["teacherToken"]
    open_teacher(page, world)
    for selector in ("#groups-empty", "#import-empty"):
        page.wait_for(
            f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
            "return !!e && e.getClientRects().length>0;})()"
        )
        assert page.eval(
            f"!!document.querySelector({json.dumps(selector)} + ' use') || "
            f"!!document.querySelector('{selector} use')"
        )
        assert len(page.text(selector).strip()) > 4
        _assert_rendered(page, selector)
    world.api("PUT", "/import/source", {"spreadsheetId": "sheet-1", "sheetId": 0})
    world.api("POST", "/import")
    world.api("POST", "/open-joining")
    world.join(1)
    student = page.browser.new_page()
    open_student(student, world, 1)
    student.wait_for(
        "document.getElementById('student-waiting').getClientRects().length > 0"
    )
    assert student.eval("!!document.querySelector('#student-waiting use')")
    _assert_rendered(student, "#student-waiting")
    assert "老師開始" in student.text("#student-waiting")
    world.open_round([3])
    student.wait_for(
        "document.getElementById('student-waiting').getClientRects().length === 0"
    )


def test_pages_load_no_external_resources(page, world):
    """US5-AS3、FR-006、SC-009：四個頁面載入的資源全部來自本機；四個字型都載入完成。"""
    world.create()
    world.join(1)
    page.track_network()
    page.goto(f"{world.server.base}/index.html")
    open_teacher(page, world)
    other = page.browser.new_page()
    other.track_network()
    open_student(other, world, 1)
    proj = page.browser.new_page()
    proj.track_network()
    open_projection(proj, world)
    for p in (page, other, proj):
        p.eval("document.fonts.ready.then(()=>true)")
        hosts = {urlparse(u).hostname for u in p.network_urls() if u.startswith("http")}
        assert hosts <= {"127.0.0.1"}, hosts
    loaded = page.eval(
        "document.fonts.ready.then(()=>[...document.fonts].filter(f=>f.status==='loade"
        "d').map(f=>f.family+' '+f.weight))"
    )
    families = " ".join(loaded)
    for name in ("Noto Serif TC 600", "Inter", "IBM Plex Mono"):
        assert name in families, loaded


def test_decorative_illustrations_hidden_from_assistive_tech(page, world):
    """US5-AS4、FR-024：空狀態插圖對輔助技術隱藏；主插圖有替代文字。"""
    world.create()
    open_teacher(page, world)
    hidden = page.eval(
        "[...document.querySelectorAll('.empty-state svg')].map(s=>s.getAttribute('ari"
        "a-hidden'))"
    )
    assert hidden and all(h == "true" for h in hidden), hidden
    page.goto(f"{world.server.base}/student.html")
    hidden = page.eval(
        "[...document.querySelectorAll('.empty-state svg')].map(s=>s.getAttribute('ari"
        "a-hidden'))"
    )
    assert hidden and all(h == "true" for h in hidden), hidden
