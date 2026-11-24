"""T056：提交同步延遲（SC-006）；以 `pytest -m perf` 執行。

以 127.0.0.1 啟動真實 uvicorn，連上老師 1 條與 6 組各 2 條，共 13 條 WebSocket。
開第 1 輪後，各組輪流由第一台裝置送出 20 筆有效提交，量測：
- 「送出 HTTP → 老師收到含該提交的快照」
- 「送出 HTTP → 同組另一台收到含該提交的快照」
兩者的最大值都必須小於 2000 ms，並以 logging 輸出最大值與平均值。
寫法沿用 001 的 `test_sync_latency.py`。
"""

import asyncio
import json
import logging
import statistics
import time
from collections.abc import Callable

import httpx
import pytest
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from lecture_quiz.main import create_app
from tests.conftest import FakeQuestionShapeSource

logger = logging.getLogger("perf")

GROUPS = 6
DEVICES_PER_GROUP = 2
QUESTIONS = 4
SUBMISSIONS = 20
LIMIT_MS = 2000.0
BLANKS = {1: 2, 2: 2, 3: 1, 4: 1}


class Listener:
    """一條 WebSocket 連線，保存每則快照與到達時間。"""

    def __init__(self, ws):
        self.ws = ws
        self.messages: list[tuple[float, dict]] = []
        self.task = asyncio.get_running_loop().create_task(self._read())

    async def _read(self):
        try:
            async for raw in self.ws:
                message = json.loads(raw)
                if message.get("type") == "snapshot":
                    self.messages.append((time.perf_counter(), message))
        except ConnectionClosed:
            pass

    async def wait_until(
        self, predicate: Callable[[dict], bool], timeout: float = 5.0
    ) -> float:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            for arrived, message in self.messages:
                if predicate(message):
                    return arrived
            await asyncio.sleep(0.001)
        raise TimeoutError(f"沒有在 {timeout} 秒內收到符合條件的快照")


def _teacher_sees(group: int, question: int) -> Callable[[dict], bool]:
    def check(message: dict) -> bool:
        current = (message.get("submissions") or {}).get("current") or {}
        return any(
            q["questionNumber"] == question
            and any(e["groupNumber"] == group for e in q["entries"])
            for q in current.get("questions", [])
        )

    return check


def _group_sees(question: int) -> Callable[[dict], bool]:
    def check(message: dict) -> bool:
        current = (message.get("submissions") or {}).get("current") or {}
        return any(s["questionNumber"] == question for s in current.get("own", []))

    return check


async def _run() -> dict[str, list[float]]:
    shapes = FakeQuestionShapeSource()
    app = create_app(question_shape_source=shapes)
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=0, log_level="warning", lifespan="off"
        )
    )
    serve_task = asyncio.get_running_loop().create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    service = app.state.activity_service
    results: dict[str, list[float]] = {"老師看板": [], "同組另一台": []}
    listeners: list[Listener] = []
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as http:
            created = (await http.post("/api/activities", json={"maxGroups": 6})).json()
            code = created["code"]
            headers = {"Authorization": f"Bearer {created['teacherToken']}"}
            shapes.set(code, BLANKS)
            teacher = service.resolve_requester(code, created["teacherToken"])
            await service.replace_questions(code, teacher, tuple(BLANKS))
            assert (await service.open_joining(code, teacher)).ok
            devices: dict[int, list[str]] = {}
            for g in range(1, GROUPS + 1):
                credential = None
                for _ in range(DEVICES_PER_GROUP):
                    joined = await service.join(code, g, credential)
                    assert joined.ok, joined
                    credential = joined.value.credential
                    devices.setdefault(g, []).append(joined.value.device_token)
            opened = await http.post(
                f"/api/activities/{code}/rounds", json={}, headers=headers
            )
            assert opened.status_code == 201, opened.text

            tokens = [created["teacherToken"]] + [
                t for g in devices.values() for t in g
            ]
            for token in tokens:
                ws = await connect(f"ws://127.0.0.1:{port}/ws/activities/{code}")
                await ws.send(json.dumps({"type": "auth", "token": token}))
                listeners.append(Listener(ws))
            assert len(listeners) == 1 + GROUPS * DEVICES_PER_GROUP
            board = listeners[0]
            await board.wait_until(lambda m: m.get("stage") == "ROUND_OPEN")

            pairs = [(g, q) for q in BLANKS for g in devices][:SUBMISSIONS]
            for group, question in pairs:
                sender, other = devices[group]
                partner = listeners[tokens.index(other)]
                start = time.perf_counter()
                response = await http.post(
                    f"/api/activities/{code}/submissions",
                    json={
                        "roundNumber": 1,
                        "questionNumber": question,
                        "answers": [f"第{group}組"] * BLANKS[question],
                    },
                    headers={"Authorization": f"Bearer {sender}"},
                )
                assert response.status_code == 201, response.text
                seen_board, seen_partner = await asyncio.gather(
                    board.wait_until(_teacher_sees(group, question)),
                    partner.wait_until(_group_sees(question)),
                )
                results["老師看板"].append((seen_board - start) * 1000)
                results["同組另一台"].append((seen_partner - start) * 1000)
    finally:
        for lis in listeners:
            await lis.ws.close()
            lis.task.cancel()
        server.should_exit = True
        await serve_task
    return results


@pytest.mark.perf
@pytest.mark.timeout(120)
def test_submission_latency_under_two_seconds(caplog):
    """SC-006：13 條連線、20 筆提交，老師與同組另一台的最大延遲都小於 2000 ms。"""
    caplog.set_level(logging.INFO, logger="perf")
    results = asyncio.run(_run())
    for name, samples in results.items():
        assert len(samples) == SUBMISSIONS
        logger.info(
            "效能 提交→%s：最大 %.1f ms、平均 %.1f ms（%d 次，13 條連線）",
            name,
            max(samples),
            statistics.mean(samples),
            len(samples),
        )
    for name, samples in results.items():
        assert max(samples) < LIMIT_MS, (name, samples)
