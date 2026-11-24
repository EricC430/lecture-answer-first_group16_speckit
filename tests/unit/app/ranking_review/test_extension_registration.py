"""建立 `RankingService` 後向 001 註冊快照擴充；無已關輪輪次時快照不變。"""

import asyncio

from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.ranking_review.service import RankingService
from lecture_quiz.app.ranking_review.store import ReviewStore
from tests.conftest import FakeClock, ManualScheduler
from tests.unit.app.ranking_review.conftest import (
    FakeSubmissionReader,
    RecordingPublisher,
    ranking_world,
)


def test_registers_exactly_one_extension():
    activities = ActivityService(
        ActivityRegistry(), FakeClock(), ManualScheduler(), RecordingPublisher()
    )
    before = len(activities._extensions)
    RankingService(
        activities, FakeSubmissionReader(), ReviewStore(), RecordingPublisher()
    )
    assert len(activities._extensions) == before + 1


def test_snapshot_is_unchanged_without_closed_round():
    async def scenario():
        world = await ranking_world()
        teacher_view = world.activities.snapshot(world.code, world.teacher).value
        student_view = world.activities.snapshot(world.code, world.student(1)).value
        return teacher_view, student_view

    teacher_view, student_view = asyncio.run(scenario())
    assert "ranking" not in teacher_view.extra
    assert "ranking" not in student_view.extra
