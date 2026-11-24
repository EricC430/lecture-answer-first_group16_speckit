"""US5：兩個判錯同時到達，依鎖序逐一套用（FR-016）。"""

import asyncio

from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


async def _world():
    world = await ranking_world(groups=(1, 2, 3))
    world.reader.set(
        world.code,
        1,
        [
            make_sub(world.code, 1, 1, 1, 1),
            make_sub(world.code, 2, 1, 2, 2),
            make_sub(world.code, 3, 1, 3, 3),
            make_sub(world.code, 1, 2, 4, 4),
            make_sub(world.code, 2, 2, 5, 5),
        ],
    )
    await world.close()
    return world


def test_two_concurrent_marks_apply_serially_and_order_independent():
    """Scenario: US5-AS7。"""

    async def run(order):
        world = await _world()
        ops = [(1, 1), (2, 2)]
        coros = [
            world.ranking.mark_wrong(world.code, world.teacher, 1, q, g)
            for g, q in (ops if order else reversed(ops))
        ]
        results = await asyncio.gather(*coros)
        return world, results

    finals = []
    for order in (True, False):
        world, results = asyncio.run(run(order))
        assert all(r.ok and r.value.changed for r in results)
        assert sorted(r.value.result_version for r in results) == [2, 3]
        review = world.store.get(world.code, 1)
        assert review.version == 3
        finals.append(review.result)
    assert finals[0] == finals[1]
