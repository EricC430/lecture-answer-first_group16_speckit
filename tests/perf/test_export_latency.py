"""T082：005 的效能（SC-008）；以 `pytest -m perf` 執行。

兩個測試：

1. 計算時間（不含 Google 往返）：50 題、99 組的預覽計算與 CSV 產生，各 < 3 秒。
2. 推送延遲：127.0.0.1 啟動真實 uvicorn，老師 1 條與 6 組各 2 條共 13 條 WebSocket；量測
   「送出寫回請求 → 老師連線收到含新狀態的快照」，10 次的最大值必須 < 2000 ms；
   同時確認 12 條學生連線沒有收到任何 `export` 欄位。

Google 一律用假替身（不連網）；這裡量的是 005 自己的處理與推送。
"""

import asyncio
import json
import logging
import statistics
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import uvicorn
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.csv_export import build_rows, render_csv
from lecture_quiz.core.result_export.models import (
    BlankTarget,
    FinalizedEntry,
    FinalizedQuestion,
    SubmissionFact,
)
from lecture_quiz.core.result_export.snapshot import build_snapshot
from lecture_quiz.main import create_app
from tests.fixtures.guided_notes_layouts import layout_a
from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway, FakeSheetsReader
from tests.unit.app.result_export.fakes import FakeSheetsWriter

logger = logging.getLogger("perf")

QUESTIONS = 50
GROUPS = 99
COMPUTE_LIMIT_S = 3.0
PUSH_LIMIT_MS = 2000.0
REPEATS = 10


@pytest.mark.perf
def test_compute_time_for_50_questions_99_groups(caplog):
    """SC-008：預覽計算與 CSV 產生（不含 Google 往返）各不超過 3 秒。"""
    caplog.set_level(logging.INFO, logger="perf")
    t0 = datetime(2026, 11, 24, 20, 0, tzinfo=UTC)
    blanks = tuple(
        BlankTarget(q, None, CellRef(10 + q, 6)) for q in range(1, QUESTIONS + 1)
    )
    questions = tuple(FinalizedQuestion(1, q, 1) for q in range(1, QUESTIONS + 1))
    entries = tuple(
        FinalizedEntry(1, q, g, g, False)
        for q in range(1, QUESTIONS + 1)
        for g in range(1, GROUPS + 1)
    )
    facts = tuple(
        SubmissionFact(1, q, g, (f"答案{q}-{g}",), t0 + timedelta(seconds=q * g))
        for q in range(1, QUESTIONS + 1)
        for g in range(1, GROUPS + 1)
    )
    start = time.perf_counter()
    snapshot = build_snapshot(
        questions, facts, blanks, range(1, QUESTIONS + 1), {}, (1,)
    )
    preview_seconds = time.perf_counter() - start
    start = time.perf_counter()
    text = render_csv(build_rows(entries, facts, blanks))
    csv_seconds = time.perf_counter() - start
    logger.info(
        "效能 預覽計算 %.3f s（%d 項）、CSV 產生 %.3f s（%d 列）",
        preview_seconds,
        len(snapshot.items),
        csv_seconds,
        text.count("\r\n") - 1,
    )
    assert len(snapshot.items) == QUESTIONS
    assert text.count("\r\n") - 1 == QUESTIONS * GROUPS
    assert preview_seconds < COMPUTE_LIMIT_S and csv_seconds < COMPUTE_LIMIT_S


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

    async def wait_for_export(self, attempt_id: int, timeout: float = 10.0) -> float:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            for arrived, message in self.messages:
                summary = message.get("export")
                if (
                    summary
                    and summary["attemptId"] == attempt_id
                    and summary["status"] == "SUCCESS"
                ):
                    return arrived
            await asyncio.sleep(0.001)
        raise TimeoutError("沒有在期限內收到寫回成功的快照")


async def _run() -> tuple[list[float], int]:
    reader = FakeSheetsReader()
    snapshot, _ = layout_a()
    reader.add("sheet-1", "學習單", [(0, "版面A", snapshot)])
    app = create_app(
        import_auth_gateway=FakeAuthGateway(authorized=True),
        import_sheets_reader=reader,
        export_sheets_writer=FakeSheetsWriter(reader),
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=0, log_level="warning", lifespan="off"
        )
    )
    serve_task = asyncio.get_running_loop().create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    listeners: list[Listener] = []
    samples: list[float] = []
    student_exports = 0
    try:
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}", timeout=30
        ) as http:
            created = (await http.post("/api/activities", json={"maxGroups": 6})).json()
            code, token = created["code"], created["teacherToken"]
            headers = {"Authorization": f"Bearer {token}"}
            base = f"/api/activities/{code}"
            assert (
                await http.put(
                    f"{base}/import/source",
                    json={"spreadsheetId": "sheet-1", "sheetId": 0},
                    headers=headers,
                )
            ).status_code == 200
            assert (
                await http.post(f"{base}/import", json={}, headers=headers)
            ).status_code == 200
            assert (
                await http.post(f"{base}/open-joining", json={}, headers=headers)
            ).status_code == 200
            devices: dict[int, list[str]] = {}
            for group in range(1, 7):
                credential = None
                for _ in range(2):
                    joined = (
                        await http.post(
                            f"{base}/groups/join",
                            json={"groupNumber": group, "credential": credential},
                        )
                    ).json()
                    credential = joined["credential"]
                    devices.setdefault(group, []).append(joined["deviceToken"])
            tokens = [token] + [t for g in devices.values() for t in g]
            for t in tokens:
                ws = await connect(f"ws://127.0.0.1:{port}/ws/activities/{code}")
                await ws.send(json.dumps({"type": "auth", "token": t}))
                listeners.append(Listener(ws))
            assert (
                await http.post(f"{base}/rounds", json={}, headers=headers)
            ).status_code == 201
            sub = await http.post(
                f"{base}/submissions",
                json={"roundNumber": 1, "questionNumber": 3, "answers": ["答"]},
                headers={"Authorization": f"Bearer {devices[1][0]}"},
            )
            assert sub.status_code == 201, sub.text
            assert (
                await http.post(
                    f"{base}/rounds/current/close", json={}, headers=headers
                )
            ).status_code == 200
            fin = await http.post(
                f"{base}/rounds/current/finalize",
                json={"resultVersion": 1},
                headers=headers,
            )
            assert fin.status_code == 200, fin.text
            preview = (
                await http.post(f"{base}/export/preview", json={}, headers=headers)
            ).json()
            attempt_id = 0
            last = preview["snapshotId"]
            for index in range(REPEATS):
                for listener in listeners:
                    listener.messages.clear()
                start = time.perf_counter()
                if index == 0:
                    response = await http.post(
                        f"{base}/export/writes",
                        json={"snapshotId": last},
                        headers=headers,
                    )
                else:
                    response = await http.post(
                        f"{base}/export/writes/{attempt_id}/retry",
                        json={},
                        headers=headers,
                    )
                assert response.status_code == 200, response.text
                attempt_id = response.json()["attemptId"]
                arrived = await listeners[0].wait_for_export(attempt_id)
                samples.append((arrived - start) * 1000)
            await asyncio.sleep(0.2)
            for listener in listeners[1:]:
                student_exports += sum(1 for _, m in listener.messages if "export" in m)
    finally:
        for lis in listeners:
            await lis.ws.close()
            lis.task.cancel()
        server.should_exit = True
        await serve_task
    return samples, student_exports


@pytest.mark.perf
@pytest.mark.timeout(300)
def test_push_latency_six_groups_under_two_seconds(caplog):
    """SC-008（必過）：老師 + 6 組、每組 2 條連線，寫回狀態推送最大值 < 2000 ms。"""
    caplog.set_level(logging.INFO, logger="perf")
    samples, student_exports = asyncio.run(_run())
    logger.info(
        "效能 寫回狀態推送（13 條連線、%d 次）：最大 %.1f ms、平均 %.1f ms、"
        "是否 < %.0f ms：%s",
        len(samples),
        max(samples),
        statistics.mean(samples),
        PUSH_LIMIT_MS,
        max(samples) < PUSH_LIMIT_MS,
    )
    assert len(samples) == REPEATS
    assert max(samples) < PUSH_LIMIT_MS, samples
    assert student_exports == 0, "學生連線不得收到 export 欄位"
