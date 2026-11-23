"""T062：同步延遲效能測試（SC-001、研究 R2）；以 `pytest -m perf` 執行。

以 127.0.0.1 啟動真實 uvicorn，連上老師 1 條與 6 組各 2 條，共 13 條 WebSocket。
開輪、關輪、定案、結束各做 10 次，量測「送出 HTTP → 13 條連線都收到新版本」的時間，
每項的最大值都必須小於 2000 ms，並以 logging 輸出每項的最大值與平均值。
"""

import asyncio
import json
import logging
import statistics
import time

import httpx
import pytest
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from lecture_quiz.main import create_app

logger = logging.getLogger("perf")

GROUPS = 6
DEVICES_PER_GROUP = 2
ROUNDS = 10
LIMIT_MS = 2000.0
OPERATIONS = ("開輪", "關輪", "定案", "結束")


class Listener:
    """一條 WebSocket 連線，記錄每個版本第一次到達的時間。"""

    def __init__(self, ws):
        self.ws = ws
        self.arrivals: dict[int, float] = {}
        self.task = asyncio.get_running_loop().create_task(self._read())

    async def _read(self):
        try:
            async for raw in self.ws:
                message = json.loads(raw)
                if message.get("type") == "snapshot":
                    self.arrivals.setdefault(message["version"], time.perf_counter())
        except ConnectionClosed:
            pass

    async def wait_for(self, version: int, timeout: float = 5.0) -> float:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            hits = [t for v, t in self.arrivals.items() if v >= version]
            if hits:
                return min(hits)
            await asyncio.sleep(0.001)
        raise TimeoutError(f"版本 {version} 沒有在 {timeout} 秒內到達")


async def _run() -> dict[str, list[float]]:
    app = create_app(dev_seed=False)
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=0, log_level="warning", lifespan="off"
        )
    )
    serve_task = asyncio.get_running_loop().create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    service = app.state.activity_service
    results: dict[str, list[float]] = {op: [] for op in OPERATIONS}
    try:
        async with httpx.AsyncClient(base_url=base) as http:
            for _ in range(ROUNDS):
                created = (
                    await http.post("/api/activities", json={"maxGroups": 6})
                ).json()
                code = created["code"]
                headers = {"Authorization": f"Bearer {created['teacherToken']}"}
                teacher = service.resolve_requester(code, created["teacherToken"])
                await service.replace_questions(code, teacher, (1, 2, 3, 4))
                tokens = [created["teacherToken"]]
                for g in range(GROUPS):
                    credential = None
                    for _ in range(DEVICES_PER_GROUP):
                        joined = await service.join(code, g + 1, credential)
                        assert joined.ok, joined
                        credential = joined.value.credential
                        tokens.append(joined.value.device_token)
                listeners = []
                for token in tokens:
                    ws = await connect(f"ws://127.0.0.1:{port}/ws/activities/{code}")
                    await ws.send(json.dumps({"type": "auth", "token": token}))
                    listeners.append(Listener(ws))
                assert len(listeners) == 1 + GROUPS * DEVICES_PER_GROUP

                steps = [
                    ("開輪", "/rounds"),
                    ("關輪", "/rounds/current/close"),
                    ("定案", "/rounds/current/finalize"),
                    ("結束", "/end"),
                ]
                for name, path in steps:
                    start = time.perf_counter()
                    response = await http.post(
                        f"/api/activities/{code}{path}", json={}, headers=headers
                    )
                    assert response.status_code in (200, 201), response.text
                    version = response.json()["version"]
                    arrivals = await asyncio.gather(
                        *(lis.wait_for(version) for lis in listeners)
                    )
                    results[name].append((max(arrivals) - start) * 1000)
                for lis in listeners:
                    await lis.ws.close()
                    lis.task.cancel()
    finally:
        server.should_exit = True
        await serve_task
    return results


@pytest.mark.perf
@pytest.mark.timeout(120)
def test_sync_latency_under_two_seconds(caplog):
    """SC-001：13 條連線，四種狀態變更各 10 次，最大延遲都小於 2000 ms。"""
    caplog.set_level(logging.INFO, logger="perf")
    results = asyncio.run(_run())
    for name in OPERATIONS:
        samples = results[name]
        assert len(samples) == ROUNDS
        logger.info(
            "效能 %s：最大 %.1f ms、平均 %.1f ms（%d 次，13 條連線）",
            name,
            max(samples),
            statistics.mean(samples),
            len(samples),
        )
    for name in OPERATIONS:
        assert max(results[name]) < LIMIT_MS, (name, results[name])
