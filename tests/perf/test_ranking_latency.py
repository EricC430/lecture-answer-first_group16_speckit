"""T082：判錯、撤銷、定案的同步延遲（SC-004）；以 `pytest -m perf` 執行。

以 127.0.0.1 啟動真實 uvicorn 與真實 WebSocket 客戶端。流程：
1. 第 1～9 輪各開 1 題、組 1 提交、關輪、定案（9 筆定案樣本，這幾輪定案時已有連線）。
2. 第 10 輪開剩餘全部題目（41 題），每組都提交每一題，關輪。
3. 在第 10 輪對組 1 的 10 個不同題目各判錯一次、再各撤銷一次（各 10 筆樣本）。
4. 第 10 輪定案（第 10 筆定案樣本）。
每筆量測「送出 HTTP → 每一條連線都收到含新結果的快照」的最大值。

6 組（13 條連線）是必過門檻：最大值 < 2000 ms。20 組（41 條連線）只記錄，不當成通過條件
（由 `verification.md` 如實說明）。
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

DEVICES_PER_GROUP = 2
QUESTIONS = 50
SMALL_ROUNDS = 9
REPEATS = 10
LIMIT_MS = 2000.0


class Listener:
    """一條 WebSocket 連線，保存快照與到達時間。"""

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
        self, predicate: Callable[[dict], bool], timeout: float = 10.0
    ) -> float:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            for arrived, message in self.messages:
                if predicate(message):
                    return arrived
            await asyncio.sleep(0.001)
        raise TimeoutError(f"沒有在 {timeout} 秒內收到符合條件的快照")


def _version_at_least(round_number: int, version: int) -> Callable[[dict], bool]:
    def check(message: dict) -> bool:
        rounds = (message.get("ranking") or {}).get("rounds", [])
        return any(
            r["roundNumber"] == round_number and r["resultVersion"] >= version
            for r in rounds
        )

    return check


def _final(round_number: int) -> Callable[[dict], bool]:
    def check(message: dict) -> bool:
        rounds = (message.get("ranking") or {}).get("rounds", [])
        return any(r["roundNumber"] == round_number and r["final"] for r in rounds)

    return check


async def _timed(http, listeners, request, predicate) -> float:
    """送出請求，量到所有連線都收到符合條件快照的最大時間（毫秒）。"""
    for listener in listeners:
        listener.messages.clear()
    start = time.perf_counter()
    response = await request(http)
    assert response.status_code == 200, response.text
    arrived = await asyncio.gather(*(lis.wait_until(predicate) for lis in listeners))
    return (max(arrived) - start) * 1000


async def _run(groups: int) -> dict[str, list[float]]:
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
    results: dict[str, list[float]] = {"判錯": [], "撤銷判錯": [], "定案": []}
    listeners: list[Listener] = []
    try:
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}", timeout=30
        ) as http:
            created = (
                await http.post("/api/activities", json={"maxGroups": groups})
            ).json()
            code = created["code"]
            teacher_token = created["teacherToken"]
            headers = {"Authorization": f"Bearer {teacher_token}"}
            shapes.set(code, dict.fromkeys(range(1, QUESTIONS + 1), 1))
            teacher = service.resolve_requester(code, teacher_token)
            assert (
                await service.replace_questions(
                    code, teacher, tuple(range(1, QUESTIONS + 1))
                )
            ).ok
            assert (await service.open_joining(code, teacher)).ok
            devices: dict[int, list[str]] = {}
            for g in range(1, groups + 1):
                credential = None
                for _ in range(DEVICES_PER_GROUP):
                    joined = await service.join(code, g, credential)
                    assert joined.ok, joined
                    credential = joined.value.credential
                    devices.setdefault(g, []).append(joined.value.device_token)
            tokens = [teacher_token] + [t for g in devices.values() for t in g]
            for token in tokens:
                ws = await connect(f"ws://127.0.0.1:{port}/ws/activities/{code}")
                await ws.send(json.dumps({"type": "auth", "token": token}))
                listeners.append(Listener(ws))
            assert len(listeners) == 1 + groups * DEVICES_PER_GROUP

            async def submit(group: int, question: int, round_number: int) -> None:
                response = await http.post(
                    f"/api/activities/{code}/submissions",
                    json={
                        "roundNumber": round_number,
                        "questionNumber": question,
                        "answers": [f"第{group}組"],
                    },
                    headers={"Authorization": f"Bearer {devices[group][0]}"},
                )
                assert response.status_code == 201, response.text

            async def finalize(round_number: int) -> float:
                async def request(client):
                    return await client.post(
                        f"/api/activities/{code}/rounds/current/finalize",
                        json={"resultVersion": 1},
                        headers=headers,
                    )

                return await _timed(http, listeners, request, _final(round_number))

            for n in range(1, SMALL_ROUNDS + 1):
                assert (await service.open_round(code, teacher, (n,), False, None)).ok
                await submit(1, n, n)
                assert (await service.close_round(code, teacher)).ok
                results["定案"].append(await finalize(n))

            big = SMALL_ROUNDS + 1
            assert (await service.open_round(code, teacher, None, True, None)).ok
            questions = range(SMALL_ROUNDS + 1, QUESTIONS + 1)
            for question in questions:
                for group in devices:
                    await submit(group, question, big)
            assert (await service.close_round(code, teacher)).ok
            version = 1
            targets = list(questions)[:REPEATS]
            for wrong, name in ((True, "判錯"), (False, "撤銷判錯")):
                for question in targets:
                    version += 1

                    async def request(client, q=question, w=wrong):
                        return await client.put(
                            f"/api/activities/{code}/rounds/{big}/questions/{q}"
                            "/groups/1/judgement",
                            json={"wrong": w},
                            headers=headers,
                        )

                    results[name].append(
                        await _timed(
                            http, listeners, request, _version_at_least(big, version)
                        )
                    )
            # 最後一次定案：版本要與目前結果版本相同
            current = version

            async def final_big(client):
                return await client.post(
                    f"/api/activities/{code}/rounds/current/finalize",
                    json={"resultVersion": current},
                    headers=headers,
                )

            results["定案"].append(
                await _timed(http, listeners, final_big, _final(big))
            )
    finally:
        for lis in listeners:
            await lis.ws.close()
            lis.task.cancel()
        server.should_exit = True
        await serve_task
    return results


def _report(groups: int, results: dict[str, list[float]]) -> None:
    for name, samples in results.items():
        logger.info(
            "效能 %s（%d 組、%d 條連線、%d 次）：最大 %.1f ms、平均 %.1f ms、"
            "是否 < %.0f ms：%s",
            name,
            groups,
            1 + groups * DEVICES_PER_GROUP,
            len(samples),
            max(samples),
            statistics.mean(samples),
            LIMIT_MS,
            max(samples) < LIMIT_MS,
        )


@pytest.mark.perf
@pytest.mark.timeout(300)
def test_ranking_latency_six_groups_under_two_seconds(caplog):
    """SC-004（必過）：老師 + 6 組、每組 2 條連線、50 題，三種操作最大值 < 2000 ms。"""
    caplog.set_level(logging.INFO, logger="perf")
    results = asyncio.run(_run(6))
    _report(6, results)
    assert {k: len(v) for k, v in results.items()} == {
        "判錯": REPEATS,
        "撤銷判錯": REPEATS,
        "定案": REPEATS,
    }
    for name, samples in results.items():
        assert max(samples) < LIMIT_MS, (name, samples)


@pytest.mark.perf
@pytest.mark.timeout(600)
def test_ranking_latency_twenty_groups_record_only(caplog):
    """只記錄：老師 + 20 組（41 條連線）；不把是否達標當成通過條件。"""
    caplog.set_level(logging.INFO, logger="perf")
    results = asyncio.run(_run(20))
    _report(20, results)
    assert all(len(samples) == REPEATS for samples in results.values())
