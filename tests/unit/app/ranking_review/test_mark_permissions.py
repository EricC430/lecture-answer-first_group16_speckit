"""US4：只有該活動的老師能判錯／撤銷（FR-011、FR-026）。"""

import asyncio

from lecture_quiz.core.activity.commands import Anonymous
from lecture_quiz.core.ranking_review.review import ReviewRejection
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


def test_student_and_anonymous_cannot_mark_or_unmark():
    """Scenario: US4-AS4。"""

    async def scenario():
        world = await _closed()
        outcomes = []
        for who in (world.student(1), Anonymous()):
            outcomes.append(await world.ranking.mark_wrong(world.code, who, 1, 1, 1))
            outcomes.append(await world.ranking.unmark_wrong(world.code, who, 1, 1, 1))
        return world, outcomes

    world, outcomes = asyncio.run(scenario())
    assert all(o.rejection is ReviewRejection.NOT_TEACHER for o in outcomes)
    assert world.store.get(world.code, 1) is None
    assert world.publisher.published == []
    assert all(o.value is None for o in outcomes)


def test_teacher_of_another_activity_is_rejected():
    """其他活動的老師身分不能操作這個活動。"""

    async def scenario():
        world = await _closed()
        other = (await world.activities.create(6)).value
        foreign = world.activities.resolve_requester(other.code, other.teacher_token)
        return world, await world.ranking.mark_wrong(world.code, foreign, 1, 1, 1)

    world, outcome = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.NOT_TEACHER
    assert world.store.get(world.code, 1) is None
