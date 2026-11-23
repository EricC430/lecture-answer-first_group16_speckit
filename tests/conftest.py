"""全專案共用的測試工具（研究 R4）。

- `FakeClock`：可手動前進的時鐘，取代系統時鐘。
- `ManualScheduler`：手動觸發的倒數排程（001）。
- `make_app`：以指定時鐘、排程與開發用 seed 設定建立 app 的工廠。
- fixture：`fake_clock`、`manual_scheduler`、`client`、`teacher`（001）。

子功能專屬的工具請追加在本檔最後，或放在各自測試目錄的 conftest.py。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lecture_quiz.main import create_app

TAIPEI = timezone(timedelta(hours=8))
FAKE_CLOCK_START = datetime(2026, 11, 21, 9, 0, 0, tzinfo=TAIPEI)


class FakeClock:
    """測試用時鐘：`now()` 回傳固定時間，只有呼叫 `advance` 才會前進。"""

    def __init__(self, start: datetime = FAKE_CLOCK_START) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock 的起點必須有時區")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now += timedelta(seconds=seconds)
        return self._now


class ManualScheduler:
    """測試用倒數排程：只記錄排程，`fire(code)` 時才以截止時間呼叫回呼。

    即使排程已被取消，`fire` 仍會以最後一次排程的截止時間觸發，
    用來模擬「取消來不及、計時器仍然觸發」的競爭情況（SC-003）。
    """

    def __init__(self) -> None:
        self.scheduled: dict[str, datetime] = {}
        self.last_deadline: dict[str, datetime] = {}
        self.cancelled: list[str] = []
        self._callback = None

    def set_callback(self, callback) -> None:
        self._callback = callback

    def schedule(self, code: str, deadline: datetime) -> None:
        self.scheduled[code] = deadline
        self.last_deadline[code] = deadline

    def cancel(self, code: str) -> None:
        self.scheduled.pop(code, None)
        self.cancelled.append(code)

    async def fire(self, code: str) -> None:
        assert self._callback is not None
        await self._callback(code, self.last_deadline[code])


def make_app(
    clock: FakeClock | None = None,
    scheduler: ManualScheduler | None = None,
    dev_seed: bool = False,
    **kwargs: Any,
) -> FastAPI:
    """以 FakeClock 與 ManualScheduler 建立 app。"""
    return create_app(
        clock=clock if clock is not None else FakeClock(),
        scheduler=scheduler if scheduler is not None else ManualScheduler(),
        dev_seed=dev_seed,
        **kwargs,
    )


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def manual_scheduler() -> ManualScheduler:
    return ManualScheduler()


@pytest.fixture
def client(
    fake_clock: FakeClock, manual_scheduler: ManualScheduler
) -> Iterator[TestClient]:
    with TestClient(make_app(fake_clock, manual_scheduler)) as test_client:
        yield test_client


@dataclass
class TeacherSession:
    """建立活動後的老師身分。"""

    code: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def create_activity(client: TestClient, max_groups: int = 6) -> TeacherSession:
    response = client.post("/api/activities", json={"maxGroups": max_groups})
    assert response.status_code == 201, response.text
    body = response.json()
    return TeacherSession(body["code"], body["teacherToken"])


@pytest.fixture
def teacher(client: TestClient) -> TeacherSession:
    return create_activity(client)


def service_of(client: TestClient):
    """取得 app 內的 ActivityService。"""
    return client.app.state.activity_service


def call(client: TestClient, fn, *args, **kwargs):
    """在 TestClient 的事件迴圈中呼叫非同步函式（與 HTTP、WebSocket 共用）。"""

    async def runner():
        return await fn(*args, **kwargs)

    return client.portal.call(runner)


def seed_questions(client: TestClient, teacher: TeacherSession, count: int = 4) -> None:
    """以 replace_questions 放入題號 1..count（研究 R8：自動化測試直接呼叫服務）."""
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)
    outcome = call(
        client,
        service.replace_questions,
        teacher.code,
        requester,
        tuple(range(1, count + 1)),
    )
    assert outcome.ok, outcome


def join_group(client: TestClient, code: str, group_name: str) -> str:
    """以最小的組別加入入口取得裝置 token（US2 完成後改用 HTTP 加入）."""
    outcome = call(client, service_of(client).join, code, group_name)
    assert outcome.ok, outcome
    return outcome.value.device_token
