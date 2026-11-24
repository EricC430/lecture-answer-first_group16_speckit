"""US2：關輪後以純計算導出初始結果，不寫入存放區（research R2）。"""

import asyncio

from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


async def _closed_world():
    world = await ranking_world(groups=(1, 2))
    world.reader.set(
        world.code,
        1,
        [
            make_sub(world.code, 2, 1, 1, 1),
            make_sub(world.code, 1, 1, 2, 2),
            make_sub(world.code, 1, 2, 3, 3),
        ],
    )
    return world


def test_review_is_none_while_round_is_open():
    async def scenario():
        world = await _closed_world()
        return world.ranking.review_for(world.code, 1)

    assert asyncio.run(scenario()) is None


def test_initial_result_is_derived_not_stored_and_stable():
    async def scenario():
        world = await _closed_world()
        await world.close()
        first = world.ranking.review_for(world.code, 1)
        second = world.ranking.review_for(world.code, 1)
        return world, first, second

    world, first, second = asyncio.run(scenario())
    assert first is not None and second is not None
    assert first.version == 1 and first.wrong_marks == frozenset()
    assert first.affected == frozenset() and dict(first.replaced) == {}
    assert first.result == second.result
    assert world.store.get(world.code, 1) is None  # 沒有寫入存放區
    by_question = {r.question_number: r for r in first.result.rankings}
    assert by_question[1].success_group == 2
    assert by_question[2].success_group == 1
    assert first.result.order == (1, 2, 3, 4)


def test_unknown_round_or_activity_returns_none():
    async def scenario():
        world = await _closed_world()
        await world.close()
        return (
            world.ranking.review_for(world.code, 9),
            world.ranking.review_for("ZZZ999", 1),
        )

    assert asyncio.run(scenario()) == (None, None)
