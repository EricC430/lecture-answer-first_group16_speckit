"""真實瀏覽器測試工具：以無頭 Chrome／Edge＋Chrome DevTools Protocol 驅動頁面。

為什麼需要：前端沒有 JavaScript 測試環境，過去的前端問題（腳本沒被載入、畫面漏顯示、
換活動後留著舊畫面）都只在人工操作時才被發現；HTTP 與 JSON 的測試完全看不到。這裡讓測試
在真的瀏覽器裡載入頁面、操作、讀取畫面。

只用已安裝的 `websockets`，不新增套件。找不到瀏覽器時**明確失敗**
（不跳過、不假裝通過）。
"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from websockets.sync.client import connect

CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def find_browser() -> str:
    """找可用的 Chrome／Edge；可用環境變數 `BROWSER_PATH` 指定。找不到就明確失敗。"""
    env = os.environ.get("BROWSER_PATH", "").strip()
    paths = [env] if env else []
    paths += [p for p in CANDIDATES if Path(p).exists()]
    for name in ("chrome", "msedge", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            paths.append(found)
    for path in paths:
        if path and Path(path).exists():
            return path
    raise AssertionError(
        "找不到 Chrome 或 Edge，無法執行真實瀏覽器測試；請安裝其中一個，"
        "或以環境變數 BROWSER_PATH 指定瀏覽器執行檔。"
    )


class Page:
    """一個分頁。"""

    def __init__(self, browser: "Browser", session_id: str, target_id: str) -> None:
        self.browser = browser
        self.session_id = session_id
        self.target_id = target_id
        self.errors: list[str] = []
        self.requests: list[str] = []

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        """呼叫這個分頁的 CDP 方法。"""
        return self.browser.call(method, params, self.session_id, self)

    def add_init_script(self, source: str) -> None:
        """在之後每次載入的文件、任何頁面腳本之前先執行（例如預先放入身分）。"""
        self.call("Page.addScriptToEvaluateOnNewDocument", source=source)

    def goto(self, url: str, timeout: float = 15.0) -> None:
        """前往網址並等到載入完成。"""
        self.call("Page.navigate", url=url)
        self.wait_for("document.readyState === 'complete'", timeout)

    def eval(self, expression: str) -> Any:
        """執行運算式並回傳值（支援 Promise）；頁面丟出例外時拋出 AssertionError。"""
        result = self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            text = details.get("exception", {}).get("description") or details.get(
                "text"
            )
            raise AssertionError(f"頁面執行失敗：{text}")
        return result["result"].get("value")

    def wait_for(self, expression: str, timeout: float = 10.0) -> None:
        """輪詢直到運算式為真；逾時時把頁面錯誤與目前畫面一併放進失敗訊息。"""
        deadline = time.time() + timeout
        last: Any = None
        while time.time() < deadline:
            try:
                last = self.eval(expression)
            except AssertionError as exc:
                last = str(exc)
            if last is True:
                return
            time.sleep(0.05)
        raise AssertionError(
            f"逾時未成立：{expression}\n最後的值：{last!r}\n頁面錯誤：{self.errors}\n"
            f"目前畫面文字：{self.text()[:1500]}"
        )

    def text(self, selector: str = "body") -> str:
        """某元素的可見文字（找不到元素回傳空字串）。"""
        return self.eval(
            f"(document.querySelector({json.dumps(selector)})||{{}}).innerText||''"
        )

    def visible(self, selector: str) -> bool:
        """元素存在且沒有被隱藏。"""
        return self.eval(
            f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
            "return !!e && !e.hidden && e.getClientRects().length>0;})()"
        )

    def click(self, selector: str) -> None:
        """點擊元素。"""
        self.eval(f"document.querySelector({json.dumps(selector)}).click(), true")

    def set_viewport(self, width: int, height: int, scale: float = 1) -> None:
        """設定視窗大小與裝置像素比（`scale=2` 模擬 200% 縮放）。"""
        self.call(
            "Emulation.setDeviceMetricsOverride",
            width=width,
            height=height,
            deviceScaleFactor=scale,
            mobile=False,
        )

    def emulate_media(self, reduced_motion: bool) -> None:
        """模擬（或取消模擬）作業系統的「減少動態效果」設定。"""
        value = "reduce" if reduced_motion else ""
        self.call(
            "Emulation.setEmulatedMedia",
            features=[{"name": "prefers-reduced-motion", "value": value}],
        )

    def track_network(self) -> None:
        """開始記錄這個分頁發出的每個請求網址（之後用 `network_urls()` 讀取）。"""
        self.call("Network.enable")

    def network_urls(self) -> list[str]:
        """目前為止記錄到的請求網址。

        先送一個空命令來回一趟：同一條連線上，這之前送出的事件一定先於回應抵達，
        所以回傳時已收齊。
        """
        self.call("Runtime.evaluate", expression="0")
        return list(self.requests)

    def screenshot(self, path: str) -> None:
        """把目前視窗截成 PNG 存到 `path`。

        先把分頁帶到前景：同時開著多個分頁時，背景分頁不會產生畫格，
        `Page.captureScreenshot` 會一直等不到回應。
        """
        self.call("Page.bringToFront")
        data = self.call("Page.captureScreenshot", format="png")["data"]
        Path(path).write_bytes(base64.b64decode(data))


class Browser:
    """一個無頭瀏覽器程序。"""

    def __init__(self) -> None:
        self.path = find_browser()
        self.profile = tempfile.mkdtemp(prefix="quiz-browser-")
        self.process = subprocess.Popen(
            [
                self.path,
                "--headless=new",
                "--remote-debugging-port=0",
                f"--user-data-dir={self.profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-gpu",
                "--disable-extensions",
                "about:blank",
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
        )
        endpoint = self._read_endpoint()
        self.ws = connect(endpoint, max_size=None)
        self._next_id = 0
        self._pages: dict[str, Page] = {}

    def _read_endpoint(self) -> str:
        deadline = time.time() + 20
        assert self.process.stderr is not None
        while time.time() < deadline:
            line = self.process.stderr.readline()
            match = re.search(r"ws://\S+", line or "")
            if match:
                return match.group(0)
            if self.process.poll() is not None:
                break
        self.close()
        raise AssertionError("瀏覽器沒有在期限內提供遠端除錯位址")

    def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        session_id: str | None = None,
        page: Page | None = None,
    ) -> dict[str, Any]:
        """送出 CDP 命令並等待回應；沿途收集各分頁的 console 錯誤、例外與請求網址。

        事件依它的 `sessionId` 交給所屬分頁，而不是交給目前發命令的分頁；
        同時開著老師、學生、投影分頁時，才不會把別頁的錯誤或請求算錯對象。
        """
        self._next_id += 1
        message: dict[str, Any] = {
            "id": self._next_id,
            "method": method,
            "params": params or {},
        }
        if session_id:
            message["sessionId"] = session_id
        self.ws.send(json.dumps(message))
        while True:
            reply = json.loads(self.ws.recv(timeout=30))
            if reply.get("id") == self._next_id:
                if "error" in reply:
                    raise AssertionError(f"{method} 失敗：{reply['error']}")
                return reply.get("result", {})
            owner = self._pages.get(reply.get("sessionId", ""), page)
            if owner is not None:
                self._collect(reply, owner)

    @staticmethod
    def _collect(event: dict[str, Any], page: Page) -> None:
        method = event.get("method")
        params = event.get("params", {})
        if method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails", {})
            text = details.get("exception", {}).get("description") or details.get(
                "text"
            )
            page.errors.append(str(text))
        elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
            page.errors.append(
                " ".join(str(a.get("value", "")) for a in params["args"])
            )
        elif method == "Log.entryAdded" and params["entry"].get("level") == "error":
            page.errors.append(params["entry"].get("text", ""))
        elif method == "Network.requestWillBeSent":
            page.requests.append(params["request"]["url"])

    def new_page(self) -> Page:
        """開一個新分頁。"""
        target = self.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        session = self.call(
            "Target.attachToTarget", {"targetId": target, "flatten": True}
        )["sessionId"]
        page = Page(self, session, target)
        self._pages[session] = page
        page.call("Page.enable")
        page.call("Runtime.enable")
        page.call("Log.enable")
        return page

    def close(self) -> None:
        """關閉瀏覽器並清掉暫存的使用者資料。"""
        try:
            if getattr(self, "ws", None) is not None:
                self.ws.close()
        finally:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            shutil.rmtree(self.profile, ignore_errors=True)
