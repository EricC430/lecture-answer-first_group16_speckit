"""T018：AsyncioCountdownScheduler 以截止時間呼叫回呼、可取消、可取代。"""

import asyncio
from datetime import timedelta

from lecture_quiz.adapters.countdown import AsyncioCountdownScheduler
from tests.conftest import FakeClock


def run(coro):
    return asyncio.run(coro)


def test_fires_callback_with_deadline_after_delay():
    async def scenario():
        clock = FakeClock()
        calls = []

        async def callback(code, deadline):
            calls.append((code, deadline))

        scheduler = AsyncioCountdownScheduler(clock)
        scheduler.set_callback(callback)
        deadline = clock.now() + timedelta(seconds=0.05)
        scheduler.schedule("ABCDEF", deadline)
        await asyncio.sleep(0.2)
        return calls, deadline

    calls, deadline = run(scenario())
    assert calls == [("ABCDEF", deadline)]


def test_past_deadline_fires_immediately():
    async def scenario():
        clock = FakeClock()
        calls = []

        async def callback(code, deadline):
            calls.append(code)

        scheduler = AsyncioCountdownScheduler(clock)
        scheduler.set_callback(callback)
        scheduler.schedule("ABCDEF", clock.now() - timedelta(seconds=5))
        await asyncio.sleep(0.05)
        return calls

    assert run(scenario()) == ["ABCDEF"]


def test_cancel_prevents_callback():
    async def scenario():
        clock = FakeClock()
        calls = []

        async def callback(code, deadline):
            calls.append(code)

        scheduler = AsyncioCountdownScheduler(clock)
        scheduler.set_callback(callback)
        scheduler.schedule("ABCDEF", clock.now() + timedelta(seconds=0.05))
        scheduler.cancel("ABCDEF")
        scheduler.cancel("NOPE22")  # 沒有排程時不出錯
        await asyncio.sleep(0.15)
        return calls

    assert run(scenario()) == []


def test_schedule_replaces_previous_task_for_same_code():
    async def scenario():
        clock = FakeClock()
        calls = []

        async def callback(code, deadline):
            calls.append(deadline)

        scheduler = AsyncioCountdownScheduler(clock)
        scheduler.set_callback(callback)
        first = clock.now() + timedelta(seconds=0.05)
        second = clock.now() + timedelta(seconds=0.1)
        scheduler.schedule("ABCDEF", first)
        scheduler.schedule("ABCDEF", second)
        await asyncio.sleep(0.25)
        return calls, second

    calls, second = run(scenario())
    assert calls == [second]


def test_callback_error_does_not_crash_scheduler(caplog):
    async def scenario():
        clock = FakeClock()

        async def callback(code, deadline):
            raise RuntimeError("boom")

        scheduler = AsyncioCountdownScheduler(clock)
        scheduler.set_callback(callback)
        scheduler.schedule("ABCDEF", clock.now())
        await asyncio.sleep(0.05)

    run(scenario())
    assert any("倒數回呼失敗" in r.getMessage() for r in caplog.records)
