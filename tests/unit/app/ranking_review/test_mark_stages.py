"""US4：判錯的階段與目標檢查，順序照 data-model「判定規則」。"""

import asyncio

from lecture_quiz.core.ranking_review.review import ReviewRejection
from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


async def _world():
    world = await ranking_world(groups=(1, 2))
    world.reader.set(
        world.code,
        1,
        [make_sub(world.code, 1, 1, 1, 1), make_sub(world.code, 2, 1, 2, 2)],
    )
    return world


def _unchanged(world):
    assert world.store.get(world.code, 1) is None
    assert world.publisher.published == []


def test_unknown_activity():
    """活動不存在。"""

    async def scenario():
        world = await _world()
        return await world.ranking.mark_wrong("ZZZ999", world.teacher, 1, 1, 1)

    assert asyncio.run(scenario()).rejection is ReviewRejection.ACTIVITY_NOT_FOUND


def test_round_still_open_has_clear_message():
    """Scenario: US4-AS5（搶答中）。"""

    async def scenario():
        world = await _world()
        return world, await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)

    world, outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.ROUND_STILL_OPEN
    assert outcome.message == "本輪尚未關閉，無法判錯。"
    _unchanged(world)


def test_no_round_yet():
    """還沒有輪次。"""

    async def scenario():
        world = await ranking_world(groups=(1,))
        activity = world.activities.get(world.code)
        # 用另一個尚未開輪的活動
        created = (await world.activities.create(6)).value
        teacher = world.activities.resolve_requester(
            created.code, created.teacher_token
        )
        assert activity is not None
        return await world.ranking.mark_wrong(created.code, teacher, 1, 1, 1)

    assert asyncio.run(scenario()).rejection is ReviewRejection.NO_ROUND


def test_unknown_round_number():
    """輪次編號不存在。"""

    async def scenario():
        world = await _world()
        await world.close()
        return await world.ranking.mark_wrong(world.code, world.teacher, 9, 1, 1)

    assert asyncio.run(scenario()).rejection is ReviewRejection.ROUND_NOT_FOUND


def test_cancelled_activity():
    """活動已取消（001 只允許第一輪之前取消，所以取消後的活動沒有輪次）。"""

    async def scenario():
        world = await _world()
        created = (await world.activities.create(6)).value
        teacher = world.activities.resolve_requester(
            created.code, created.teacher_token
        )
        assert (await world.activities.cancel(created.code, teacher)).ok
        return await world.ranking.mark_wrong(created.code, teacher, 1, 1, 1)

    assert asyncio.run(scenario()).rejection is ReviewRejection.ACTIVITY_CANCELLED


def test_missing_submission_is_not_found_and_state_unchanged():
    """目標提交不存在。"""

    async def scenario():
        world = await _world()
        await world.close()
        return world, await world.ranking.mark_wrong(world.code, world.teacher, 1, 2, 1)

    world, outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.SUBMISSION_NOT_FOUND
    _unchanged(world)


def test_final_round_cannot_be_changed():
    """該輪已定案。"""

    async def scenario():
        world = await _world()
        await world.close()
        assert (await world.activities.finalize(world.code, world.teacher, _plan())).ok
        return world, await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)

    def _plan():
        from lecture_quiz.core.activity.commands import FinalizeOutcome

        return FinalizeOutcome(frozenset({1}), {1: 1})

    world, outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.RESULT_ALREADY_FINAL
    assert world.store.get(world.code, 1) is None
