"""US6：001 拒絕定案時 004 不保存定案紀錄。"""

import asyncio

from lecture_quiz.app.activity.ports import Outcome
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.ranking_review.review import ReviewRejection
from tests.unit.app.ranking_review.test_finalize import closed_world


def test_001_rejection_leaves_review_markable():
    async def scenario():
        world = await closed_world()

        async def refuse(*args, **kwargs):
            reason = RejectionReason.STAGE_NOT_ALLOWED
            return Outcome(ok=False, rejection=reason, message=reason.default_message)

        world.spy.finalize = refuse
        outcome = await world.ranking.finalize(world.code, world.teacher, 1)
        mark = await world.ranking.mark_wrong(world.code, world.teacher, 1, 1, 1)
        return world, outcome, mark

    world, outcome, mark = asyncio.run(scenario())
    assert outcome.rejection is ReviewRejection.FINALIZE_REJECTED
    assert mark.ok and mark.value.changed and mark.value.result_version == 2
    assert world.store.get(world.code, 1).finalized is None
