"""全專案共用的測試工具（研究 R4）。

- `FakeClock`：可手動前進的時鐘，取代系統時鐘。
- `make_app`：以指定時鐘建立 app 的工廠。
- fixture：`fake_clock`、`client`。

子功能專屬的工具（例如 001 的 `ManualScheduler`、`teacher` fixture）請追加在本檔最後，
或放在各自測試目錄的 conftest.py。
"""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

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


def make_app(clock: FakeClock | None = None) -> FastAPI:
    """以 FakeClock 建立 app；001 之後會在這裡補上 scheduler 等參數。"""
    return create_app(clock=clock if clock is not None else FakeClock())


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(fake_clock: FakeClock) -> Iterator[TestClient]:
    with TestClient(make_app(fake_clock)) as test_client:
        yield test_client
