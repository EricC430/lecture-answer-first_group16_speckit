"""US1：基準來自 001 在開輪時保存的各組成功次數（題組只計一次、兩種模式都計入）。"""

import asyncio

from lecture_quiz.core.activity.commands import FinalizeOutcome
from tests.unit.app.ranking_review.conftest import make_sub, ranking_world


async def _finish_round_one(world, solved, increments):
    """關輪並以指定成果定案第 1 輪（模擬先前輪次的結果）。"""
    await world.close()
    result = await world.activities.finalize(
        world.code, world.teacher, FinalizeOutcome(frozenset(solved), increments)
    )
    assert result.ok, result


def test_three_cell_question_counts_once_not_three_times():
    """Scenario: US1-AS1 ↔ OpenSpec「題組與不同模式的累計」。"""

    async def scenario():
        world = await ranking_world(groups=(1, 2))
        # 第 1 輪速度模式：甲組（1）贏得一個三格題組 → 成功次數 +1（不是 +3）
        await _finish_round_one(world, {1}, {1: 1})
        assert (
            await world.activities.open_round(world.code, world.teacher, (2, 3), True)
        ).ok
        activity = world.activities.get(world.code)
        round_two = activity.current_round
        built = world.ranking._build_input(activity, 2, (), frozenset())
        return round_two, built

    round_two, built = asyncio.run(scenario())
    assert round_two.rules.fair_mode is True
    assert dict(built.baseline) == {1: 1, 2: 0}
    assert built.fair_mode is True
    assert built.question_numbers == (2, 3)


def test_speed_mode_successes_count_toward_baseline():
    """Scenario: US1-AS2（速度模式下的兩個單題成功都計入）。"""

    async def scenario():
        world = await ranking_world(groups=(1, 2))
        await _finish_round_one(world, {1, 2}, {1: 2})
        assert (
            await world.activities.open_round(world.code, world.teacher, (3, 4), True)
        ).ok
        activity = world.activities.get(world.code)
        return world.ranking._build_input(activity, 2, (), frozenset())

    built = asyncio.run(scenario())
    assert dict(built.baseline) == {1: 2, 2: 0}


def test_unfinalized_result_never_changes_baseline_or_success_counts():
    """Scenario: US1-AS3（本輪未定案的成功不會被累加到歷史基準）。"""

    async def scenario():
        world = await ranking_world(groups=(1, 2))
        subs = [
            make_sub(world.code, 1, 1, 1, 1),
            make_sub(world.code, 1, 2, 2, 2),
            make_sub(world.code, 2, 1, 3, 3),
        ]
        world.reader.set(world.code, 1, subs)
        await world.close()
        activity = world.activities.get(world.code)
        built = world.ranking._build_input(activity, 1, tuple(subs), frozenset())
        return activity, built

    activity, built = asyncio.run(scenario())
    assert dict(built.baseline) == dict(activity.current_round.baseline)
    assert all(g.success_count == 0 for g in activity.groups.values())


def test_group_joining_after_round_opened_starts_at_zero():
    """Scenario: US1-AS4（開輪後才加入的組別沒有基準，視為 0）。"""

    async def scenario():
        world = await ranking_world(groups=(1,))
        assert (await world.activities.join(world.code, 2)).ok  # 搶答中途加入
        await world.close()
        activity = world.activities.get(world.code)
        subs = (make_sub(world.code, 2, 1, 1, 1),)
        built = world.ranking._build_input(activity, 1, subs, frozenset())
        return activity, built

    activity, built = asyncio.run(scenario())
    assert 2 not in dict(activity.current_round.baseline)
    assert 2 not in dict(built.baseline) or dict(built.baseline)[2] == 0
