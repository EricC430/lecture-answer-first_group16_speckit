"""真實瀏覽器測試的共用 fixture：真實 uvicorn 後端（Google 用假替身）＋無頭瀏覽器。"""

import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import httpx
import pytest
import uvicorn

from lecture_quiz.main import create_app
from tests.browser.cdp import Browser, Page
from tests.conftest import post_join
from tests.fixtures.guided_notes_layouts import layout_a, layout_b
from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway, FakeSheetsReader
from tests.unit.app.result_export.fakes import FakeSheetsWriter


class LiveServer:
    """在背景執行緒啟動的真實 uvicorn（只監聽 127.0.0.1）。"""

    def __init__(self) -> None:
        self.reader = FakeSheetsReader()
        snapshot_a, _ = layout_a()
        snapshot_b, _ = layout_b()
        self.reader.add(
            "sheet-1", "學習單", [(0, "版面A", snapshot_a), (7, "版面B", snapshot_b)]
        )
        self.writer = FakeSheetsWriter(self.reader)
        self.app = create_app(
            import_auth_gateway=FakeAuthGateway(authorized=True),
            import_sheets_reader=self.reader,
            export_sheets_writer=self.writer,
        )
        config = uvicorn.Config(
            self.app, host="127.0.0.1", port=0, log_level="warning", lifespan="on"
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.time() + 20
        while not self.server.started and time.time() < deadline:
            time.sleep(0.02)
        assert self.server.started, "後端沒有在期限內啟動"
        self.port = self.server.servers[0].sockets[0].getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        """停止後端。"""
        self.server.should_exit = True
        self.thread.join(timeout=15)


@dataclass
class World:
    """一個活動與它的各組裝置（以 HTTP 建立，和人工操作等價）。"""

    server: LiveServer
    http: httpx.Client
    code: str = ""
    teacher_token: str = ""
    devices: dict[int, str] = field(default_factory=dict)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.teacher_token}"}

    def api(
        self, method: str, path: str, body: dict | None = None, token: str | None = None
    ):
        headers = {"Authorization": f"Bearer {token}"} if token else self.headers
        response = self.http.request(
            method,
            f"/api/activities/{self.code}{path}",
            json=body if body is not None else {},
            headers=headers,
        )
        return response

    def create(self, max_groups: int = 6) -> None:
        """建立活動、匯入版面 A（4 題）、開放加入。"""
        created = self.http.post("/api/activities", json={"maxGroups": max_groups})
        assert created.status_code == 201, created.text
        self.code = created.json()["code"]
        self.teacher_token = created.json()["teacherToken"]
        put = self.api(
            "PUT", "/import/source", {"spreadsheetId": "sheet-1", "sheetId": 0}
        )
        assert put.status_code == 200, put.text
        assert self.api("POST", "/import").status_code == 200
        assert self.api("POST", "/open-joining").status_code == 200

    def join(self, *groups: int) -> None:
        for group in groups:
            # 每組一個新瀏覽器；金鑰之後由 test_pages 以 cookie 注入該組的分頁（007）
            joined, key = post_join(self.http, self.code, {"groupNumber": group})
            assert joined.status_code == 200, joined.text
            self.devices[group] = key

    def open_round(self, questions: list[int] | None = None) -> None:
        body = {} if questions is None else {"questionNumbers": questions}
        response = self.api("POST", "/rounds", body)
        assert response.status_code == 201, response.text

    def submit(
        self, round_number: int, question: int, group: int, answers: list[str]
    ) -> None:
        response = self.http.post(
            f"/api/activities/{self.code}/submissions",
            json={
                "roundNumber": round_number,
                "questionNumber": question,
                "answers": answers,
            },
            headers={"Authorization": f"Bearer {self.devices[group]}"},
        )
        assert response.status_code == 201, response.text

    def close_round(self) -> None:
        assert self.api("POST", "/rounds/current/close").status_code == 200

    def finalize(self) -> None:
        snapshot = self.api("GET", "/snapshot").json()
        rounds = snapshot.get("ranking", {}).get("rounds", [])
        version = rounds[-1]["resultVersion"] if rounds else 1
        response = self.api(
            "POST", "/rounds/current/finalize", {"resultVersion": version}
        )
        assert response.status_code == 200, response.text

    def judge(self, round_number: int, question: int, group: int, wrong: bool) -> None:
        response = self.api(
            "PUT",
            f"/rounds/{round_number}/questions/{question}/groups/{group}/judgement",
            {"wrong": wrong},
        )
        assert response.status_code == 200, response.text


@pytest.fixture(scope="session")
def live_server() -> Iterator[LiveServer]:
    server = LiveServer()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    instance = Browser()
    yield instance
    instance.close()


@pytest.fixture
def world(live_server: LiveServer) -> Iterator[World]:
    with httpx.Client(base_url=live_server.base, timeout=30) as http:
        yield World(live_server, http)


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    tab = browser.new_page()
    yield tab
    browser.call("Target.closeTarget", {"targetId": tab.target_id})
