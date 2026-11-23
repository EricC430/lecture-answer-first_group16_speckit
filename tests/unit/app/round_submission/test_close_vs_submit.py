"""US3：關輪與提交同時發生（Scenario: US3-AS6；FR-019、SC-004）。"""

import asyncio
import random

from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.round_submission.models import SubmissionAttempt
from lecture_quiz.core.round_submission.rules import DecisionKind, SubmissionRejection
from tests.unit.app.round_submission.conftest import open_world


def test_close_and_submit_race_50_times():
    """提交要嘛在關輪前保存並出現在關輪推送中，要嘛被拒且未保存。"""
    rng = random.Random(7)

    async def once(close_first):
        world = await open_world()
        stored_at_publish = []
        original = world.publisher.publish

        async def publish(activity):
            stored_at_publish.append(
                (activity.stage, len(world.store.get(world.code).submissions))
            )
            await original(activity)

        world.publisher.publish = publish
        submit = world.submissions.submit(
            world.code, world.devices[1][0], SubmissionAttempt(1, 3, ["丙"])
        )
        close = world.activities.close_round(world.code, world.teacher)
        tasks = (close, submit) if close_first else (submit, close)
        results = await asyncio.gather(*tasks)
        outcome = results[1] if close_first else results[0]
        return world, outcome, stored_at_publish

    accepted = rejected = 0
    for _ in range(50):
        world, outcome, stored_at_publish = asyncio.run(once(rng.random() < 0.5))
        stored = world.store.get(world.code).submissions
        assert world.activities.get(world.code).stage is Stage.RESULT_PENDING
        closing = [n for stage, n in stored_at_publish if stage is Stage.RESULT_PENDING]
        assert len(closing) == 1
        if outcome.value.kind is DecisionKind.ACCEPTED:
            accepted += 1
            assert stored == (outcome.value.submission,)
            assert closing[0] == 1  # 關輪推送時已包含這筆提交
        else:
            rejected += 1
            assert outcome.value.rejection is SubmissionRejection.ROUND_CLOSED
            assert stored == ()
    assert accepted and rejected
