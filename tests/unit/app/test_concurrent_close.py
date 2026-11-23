"""T053：手動關輪與倒數截止同時發生 50 次，每次都只關一次（SC-003）。"""

import asyncio
from datetime import timedelta

from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.service import ActivityService
from tests.conftest import FakeClock, ManualScheduler


class CountingPublisher:
    def __init__(self):
        self.published = []

    async def publish(self, activity):
        self.published.append(activity.version)

    async def disconnect_device(self, code, token_hash, reason):
        pass


async def one_race(teacher_first: bool):
    clock = FakeClock()
    scheduler = ManualScheduler()
    publisher = CountingPublisher()
    service = ActivityService(ActivityRegistry(), clock, scheduler, publisher)
    scheduler.set_callback(service.on_deadline)
    created = (await service.create(6)).value
    teacher = service.resolve_requester(created.code, created.teacher_token)
    await service.replace_questions(created.code, teacher, (1, 2))
    await service.open_round(created.code, teacher, None, False, 30)
    version_before = service.get(created.code).version
    publisher.published.clear()
    clock.advance(30)  # 剛好到截止時間：兩邊都有資格關輪

    calls = [service.close_round(created.code, teacher), scheduler.fire(created.code)]
    if not teacher_first:
        calls.reverse()
    await asyncio.gather(*calls)

    activity = service.get(created.code)
    return activity, version_before, publisher.published


def test_close_and_deadline_race_closes_once_50_times():
    """Scenario: US4-AS3

    手動關輪與倒數截止同時發生 50 次，每次只有一個呼叫產生變更，
    版本只加 1、只推送一次、輪次數不增加（SC-003）。
    """
    for i in range(50):
        activity, version_before, published = asyncio.run(
            one_race(teacher_first=i % 2 == 0)
        )
        assert activity.stage.value == "RESULT_PENDING"
        assert activity.version == version_before + 1
        assert published == [version_before + 1]
        assert len(activity.rounds) == 1
        assert activity.current_round.closed


def test_deadline_callback_uses_deadline_when_timer_fires_early():
    """倒數計時器比牆上時鐘早觸發時，仍以截止時間關輪（PR #15 審查第 3 項）。"""

    async def scenario():
        clock = FakeClock()
        scheduler = ManualScheduler()
        service = ActivityService(
            ActivityRegistry(), clock, scheduler, CountingPublisher()
        )
        scheduler.set_callback(service.on_deadline)
        created = (await service.create(6)).value
        teacher = service.resolve_requester(created.code, created.teacher_token)
        await service.replace_questions(created.code, teacher, (1,))
        await service.open_round(created.code, teacher, None, False, 30)
        clock.advance(30 - 0.005)  # 計時器早 5 ms 觸發
        await scheduler.fire(created.code)
        return service.get(created.code)

    activity = asyncio.run(scenario())
    assert activity.stage.value == "RESULT_PENDING"
    assert activity.current_round.close_cause == "deadline"
    assert activity.current_round.closed_at == activity.current_round.rules.deadline
    assert (
        activity.current_round.closed_at - activity.current_round.opened_at
        == timedelta(seconds=30)
    )
