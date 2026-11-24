"""US6：同時確認只定案一次（SC-005）。"""

import asyncio

from lecture_quiz.core.ranking_review.review import ReviewRejection
from tests.unit.app.ranking_review.test_finalize import closed_world


def test_two_identical_finalizes_call_001_once():
    async def scenario():
        world = await closed_world()
        a, b = await asyncio.gather(
            world.ranking.finalize(world.code, world.teacher, 1),
            world.ranking.finalize(world.code, world.teacher, 1),
        )
        return world, a, b

    world, a, b = asyncio.run(scenario())
    assert a.ok and b.ok
    assert sorted([a.value.already_finalized, b.value.already_finalized]) == [
        False,
        True,
    ]
    assert len(world.spy.finalize_calls) == 1
    assert world.activities.get(world.code).groups[2].success_count == 1


def test_mark_and_finalize_are_serialized():
    async def scenario():
        world = await closed_world()
        mark, fin = await asyncio.gather(
            world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1),
            world.ranking.finalize(world.code, world.teacher, 1),
        )
        return world, mark, fin

    world, mark, fin = asyncio.run(scenario())
    review = world.store.get(world.code, 1)
    if fin.ok:  # 先定案：判錯被拒；定案內容 = 版本 1 的結果
        assert mark.rejection is ReviewRejection.RESULT_ALREADY_FINAL
        assert review.finalized.version == 1 and review.version == 1
    else:  # 先判錯：定案版本過期
        assert mark.ok and fin.rejection is ReviewRejection.STALE_RESULT_VERSION
        assert review.finalized is None
