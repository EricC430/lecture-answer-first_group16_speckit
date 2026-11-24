"""US6：確認定案（FR-018～FR-021、SC-005）。"""

import asyncio

from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.ranking_review.models import DisplayStatus
from lecture_quiz.core.ranking_review.review import ReviewRejection
from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


class SpyActivities:
    """包裝 001 的服務，記錄 finalize 的呼叫。"""

    def __init__(self, inner):
        self._inner = inner
        self.finalize_calls = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    async def finalize(self, *args, **kwargs):
        self.finalize_calls.append(args)
        return await self._inner.finalize(*args, **kwargs)


async def closed_world(fair=False):
    world = await ranking_world(groups=(1, 2, 3), fair=fair)
    world.reader.set(
        world.code,
        1,
        [
            make_sub(world.code, 1, 1, 1, 1),
            make_sub(world.code, 2, 1, 2, 2),
            make_sub(world.code, 2, 2, 3, 3),
        ],
    )
    await world.close()
    spy = SpyActivities(world.activities)
    world.ranking._activities = spy
    world.spy = spy
    return world


def _view(world, kind="teacher"):
    activity = world.activities.get(world.code)
    from lecture_quiz.app.activity.ports import GroupViewer, TeacherViewer

    viewer = TeacherViewer() if kind == "teacher" else GroupViewer(1)
    return world.ranking.snapshot_extension(activity, viewer)["ranking"]["rounds"][0]


def test_finalize_updates_001_and_marks_correct():
    """Scenario: US6-AS1／AS2／AS3。"""

    async def scenario():
        world = await closed_world()
        await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        v = world.store.get(world.code, 1).version
        before_t = _view(world)
        before_s = _view(world, "student")
        outcome = await world.ranking.finalize(world.code, world.teacher, v)
        return world, v, outcome, before_t, before_s

    world, v, outcome, before_t, before_s = asyncio.run(scenario())
    assert outcome.ok and not outcome.value.already_finalized
    assert outcome.value.result_version == v
    activity = world.activities.get(world.code)
    assert activity.stage is Stage.RESULT_FINAL
    assert activity.groups[2].success_count == 2
    assert activity.groups[1].success_count == 0
    assert activity.solved_questions == {1, 2}
    after_t = _view(world)
    after_s = _view(world, "student")
    assert before_t["final"] is False and after_t["final"] is True
    assert after_t["resultVersion"] == before_t["resultVersion"]  # 版本相同、輸出不同
    q1_before = before_t["questions"][0]["entries"][0]
    assert q1_before["displayStatus"] == "SUCCESS"
    assert after_t["questions"][0]["entries"][0]["displayStatus"] == "CORRECT"
    assert after_t["questions"][0]["actions"] == {"judgeGroup": None, "undoGroup": None}
    assert after_t["questions"][0]["replacedGroup"] is None
    assert after_s["final"] is True and after_s["questions"][0]["replacedGroup"] is None
    assert before_s["final"] is False
    stored = world.store.get(world.code, 1)
    assert (
        stored.finalized.rankings[0].entries[0].display_status is DisplayStatus.CORRECT
    )


def test_repeat_same_version_is_idempotent_and_calls_001_once():
    """Scenario: US6-AS2。"""

    async def scenario():
        world = await closed_world()
        first = await world.ranking.finalize(world.code, world.teacher, 1)
        second = await world.ranking.finalize(world.code, world.teacher, 1)
        return world, first, second

    world, first, second = asyncio.run(scenario())
    assert second.ok and second.value.already_finalized
    assert len(world.spy.finalize_calls) == 1
    assert world.activities.get(world.code).groups[2].success_count == 1


def test_stale_version_is_rejected_without_changes():
    """Scenario: US6-AS3。"""

    async def scenario():
        world = await closed_world()
        await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        outcome = await world.ranking.finalize(world.code, world.teacher, 1)
        return world, outcome

    world, outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.STALE_RESULT_VERSION
    assert world.activities.get(world.code).stage is Stage.RESULT_PENDING
    assert world.store.get(world.code, 1).version == 2
    assert world.store.get(world.code, 1).finalized is None
    assert world.spy.finalize_calls == []


def test_different_version_after_final_is_already_final():
    """定案後以不同版本確認。"""

    async def scenario():
        world = await closed_world()
        await world.ranking.finalize(world.code, world.teacher, 1)
        return await world.ranking.finalize(world.code, world.teacher, 5)

    outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.RESULT_ALREADY_FINAL
    assert "1" in outcome.message


def test_finalize_without_any_mark():
    """Scenario: US6-AS6。"""

    async def scenario():
        world = await closed_world()
        return await world.ranking.finalize(world.code, world.teacher, 1)

    assert asyncio.run(scenario()).ok


def test_finalize_rejections_for_role_and_stage():
    """學生不能定案；搶答中不能定案。"""

    async def scenario():
        world = await ranking_world(groups=(1,))
        open_round = await world.ranking.finalize(world.code, world.teacher, 1)
        student = await world.ranking.finalize(world.code, world.student(1), 1)
        return open_round, student

    open_round, student = asyncio.run(scenario())
    assert open_round.rejection is ReviewRejection.ROUND_STILL_OPEN
    assert student.rejection is ReviewRejection.NOT_TEACHER
