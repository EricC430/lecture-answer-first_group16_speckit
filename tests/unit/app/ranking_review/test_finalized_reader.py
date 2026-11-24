"""US6：給 005 的唯讀定案結果（`RankingReader`）。"""

import asyncio

from lecture_quiz.core.ranking_review.models import DisplayStatus
from tests.unit.app.ranking_review.test_finalize import closed_world


def test_only_finalized_rounds_with_final_data():
    async def scenario():
        world = await closed_world()
        before = world.ranking.finalized_rounds(world.code)
        await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        await world.ranking.finalize(world.code, world.teacher, 2)
        return world, before, world.ranking.finalized_rounds(world.code)

    world, before, after = asyncio.run(scenario())
    assert before == ()
    assert [r.round_number for r in after] == [1]
    result = after[0].result
    q1 = result.rankings[0]
    by_group = {e.group_number: e for e in q1.entries}
    assert by_group[1].rank is None and by_group[1].wrong
    assert by_group[2].rank == 1 and by_group[2].display_status is DisplayStatus.CORRECT
    activity = world.activities.get(world.code)
    assert dict(result.final_counts) == {
        n: g.success_count for n, g in activity.groups.items()
    }
    assert result.solved_questions == {1, 2}
    try:
        result.rankings = ()  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("FinalizedResult 必須不可變")


def test_unknown_activity_has_no_rounds():
    async def scenario():
        world = await closed_world()
        return world.ranking.finalized_rounds("ZZZ999")

    assert asyncio.run(scenario()) == ()
