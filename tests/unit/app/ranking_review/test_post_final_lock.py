"""US6：定案後鎖定（FR-010、FR-021）。"""

import asyncio

from lecture_quiz.core.ranking_review.review import ReviewRejection
from tests.unit.app.ranking_review.test_finalize import closed_world


def test_marking_after_final_is_rejected():
    """Scenario: US6-AS4。"""

    async def scenario():
        world = await closed_world()
        await world.ranking.finalize(world.code, world.teacher, 1)
        mark = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        undo = await world.ranking.unmark_wrong(world.code, world.teacher, 1, 1, 1)
        return world, mark, undo

    world, mark, undo = asyncio.run(scenario())
    assert mark.rejection is ReviewRejection.RESULT_ALREADY_FINAL
    assert undo.rejection is ReviewRejection.RESULT_ALREADY_FINAL
    assert world.store.get(world.code, 1).version == 1


def test_old_round_stays_locked_after_next_round_opens():
    """Scenario: US6-AS5。"""

    async def scenario():
        world = await closed_world()
        await world.ranking.finalize(world.code, world.teacher, 1)
        opened = await world.activities.open_round(
            world.code, world.teacher, None, False, None
        )
        mark = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        return world, opened, mark

    world, opened, mark = asyncio.run(scenario())
    assert opened.ok
    assert mark.rejection is ReviewRejection.RESULT_ALREADY_FINAL
    assert world.activities.get(world.code).groups[2].success_count == 1


def test_no_route_changes_round_mode_and_pending_stage_blocks_new_round():
    """FR-010：004 沒有切換模式入口；結果未定案時不能再開輪（001 行為）。"""
    from tests.conftest import make_app

    paths = make_app().openapi()["paths"]
    mode_routes = [p for p in paths if "mode" in p.lower() or "fair" in p.lower()]
    assert mode_routes == []

    async def scenario():
        world = await closed_world()
        return await world.activities.open_round(
            world.code, world.teacher, None, True, None
        )

    assert asyncio.run(scenario()).ok is False
