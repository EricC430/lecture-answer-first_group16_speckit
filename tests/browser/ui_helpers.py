"""006 介面改版的真實瀏覽器測試共用工具。"""

import json
import time

from tests.browser.cdp import Page
from tests.browser.test_pages import assert_no_script_errors, open_student, open_teacher

__all__ = [
    "assert_no_script_errors",
    "computed",
    "open_projection",
    "open_student",
    "open_teacher",
    "token_value",
    "wait_stage",
]


def computed(page: Page, selector: str, prop: str) -> str:
    """第一個符合元素的計算樣式值。"""
    return page.eval(
        f"getComputedStyle(document.querySelector({json.dumps(selector)}))"
        f".getPropertyValue({json.dumps(prop)}).trim()"
    )


def token_value(page: Page, name: str) -> str:
    """tokens.css 基準值經瀏覽器解析後的顏色（轉成 rgb() 方便與計算樣式比較）。"""
    return page.eval(
        "(()=>{const e=document.createElement('span');"
        f"e.style.color='var({name})';document.body.append(e);"
        "const v=getComputedStyle(e).color;e.remove();return v;})()"
    )


def wait_stage(page: Page, element_id: str, label: str, timeout: float = 10.0) -> None:
    """等到某個顯示階段的元素文字包含 label。"""
    page.wait_for(
        f"(document.getElementById({json.dumps(element_id)})||{{}}).textContent"
        f"?.includes({json.dumps(label)}) === true",
        timeout,
    )


TRACK_SOCKETS = (
    "(()=>{const W=window.WebSocket;window.__sockets=[];"
    "window.WebSocket=function(...a){const s=new W(...a);window.__sockets.push(s);retu"
    "rn s;};"
    "window.WebSocket.prototype=W.prototype;Object.assign(window.WebSocket,W);})();"
)


def track_sockets(page: Page) -> None:
    """在頁面載入前記錄它建立的 WebSocket（只為了測試時能讓同步中斷）。"""
    page.add_init_script(TRACK_SOCKETS)


def break_sync(page: Page) -> None:
    """讓頁面離線並關掉現有的同步連線：sync.js 會進入「同步中斷」並持續重連失敗。"""
    page.call("Network.enable")
    page.call(
        "Network.emulateNetworkConditions",
        offline=True,
        latency=0,
        downloadThroughput=0,
        uploadThroughput=0,
    )
    page.eval("(window.__sockets||[]).forEach(s => s.close()), true")
    page.wait_for("document.body.classList.contains('sync-broken')")


def restore_sync(page: Page) -> None:
    """恢復網路；sync.js 的重連會在數秒內成功。"""
    page.call(
        "Network.emulateNetworkConditions",
        offline=False,
        latency=0,
        downloadThroughput=-1,
        uploadThroughput=-1,
    )


def open_projection(page: Page, world, with_token: bool = True) -> None:
    """以老師身分（同一瀏覽器的 localStorage）開投影畫面。"""
    if with_token:
        page.add_init_script(
            f"localStorage.setItem('teacher:{world.code}', "
            f"{json.dumps(world.teacher_token)});"
        )
    page.goto(f"{world.server.base}/projection.html?code={world.code}")
    page.wait_for("document.getElementById('projection-root') !== null")
    time.sleep(0.05)
