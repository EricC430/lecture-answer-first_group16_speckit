"""US4：判錯成功後的推送時機與失敗處理（research R4）。"""

import asyncio
import logging

from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


async def _closed():
    world = await ranking_world(groups=(1, 2))
    world.reader.set(
        world.code,
        1,
        [make_sub(world.code, 1, 1, 1, 1), make_sub(world.code, 2, 1, 2, 2)],
    )
    await world.close()
    return world


def test_real_change_publishes_once_after_lock_release():
    """實際變更恰推送一次，且推送時 004 的鎖已釋放。"""

    async def scenario():
        world = await _closed()
        outcome = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        return world, outcome

    world, outcome = asyncio.run(scenario())
    assert outcome.ok and outcome.value.changed
    assert outcome.value.result_version == 2
    assert len(world.publisher.published) == 1
    assert world.publisher.lock_held_during_publish == [False]


def test_no_change_and_rejections_do_not_publish():
    """重複判錯、重複撤銷與被拒絕的請求都不推送。"""

    async def scenario():
        world = await _closed()
        await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        world.publisher.published.clear()
        again = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        undo_none = await world.ranking.unmark_wrong(world.code, world.teacher, 1, 1, 2)
        rejected = await world.ranking.mark_wrong(world.code, world.teacher, 1, 3, 1)
        return world, again, undo_none, rejected

    world, again, undo_none, rejected = asyncio.run(scenario())
    assert again.ok and not again.value.changed and again.value.affected_questions == ()
    assert undo_none.ok and not undo_none.value.changed
    assert not rejected.ok
    assert world.publisher.published == []


def test_publish_failure_keeps_state_and_logs(caplog):
    """推送拋例外時狀態變更仍保留，並記錄 exception。"""

    async def scenario():
        world = await _closed()
        world.publisher.fail = True
        with caplog.at_level(logging.ERROR):
            outcome = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        return world, outcome

    world, outcome = asyncio.run(scenario())
    assert outcome.ok and outcome.value.changed
    stored = world.store.get(world.code, 1)
    assert stored is not None and stored.version == 2
    assert any(r.exc_info for r in caplog.records)
