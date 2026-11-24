"""US2：同組多裝置競爭與重送只保存第一筆（SC-002、SC-003）。"""

import asyncio

from lecture_quiz.core.round_submission.models import SubmissionAttempt
from lecture_quiz.core.round_submission.rules import DecisionKind
from tests.unit.app.round_submission.conftest import open_world


def _attempt(question, answers, round_number=1):
    return SubmissionAttempt(round_number, question, list(answers))


def test_two_devices_race_keeps_one():
    """Scenario: US2-AS1（OpenSpec「同組兩裝置競爭」：重複 50 次都只保存一筆）。"""

    async def once():
        world = await open_world(groups=(1,), devices_per_group=2)
        a, b = world.devices[1]
        outcomes = await asyncio.gather(
            world.submissions.submit(world.code, a, _attempt(1, ("A一", "A二"))),
            world.submissions.submit(world.code, b, _attempt(1, ("B一", "B二"))),
        )
        return world, outcomes

    for _ in range(50):
        world, outcomes = asyncio.run(once())
        stored = world.store.get(world.code).submissions
        assert len(stored) == 1
        kinds = sorted(o.value.kind.value for o in outcomes)
        assert kinds == sorted(
            [DecisionKind.ACCEPTED.value, DecisionKind.ALREADY_SUBMITTED.value]
        )
        for outcome in outcomes:
            assert outcome.value.submission == stored[0]
        assert len(world.publisher.published) == 1


def test_resend_returns_original():
    """Scenario: US2-AS2（OpenSpec「回應遺失後重送」：重送 20 次仍只有原提交）。"""

    async def scenario():
        world = await open_world()
        token = world.devices[1][0]
        first = await world.submissions.submit(
            world.code, token, _attempt(1, ("甲", "乙"))
        )
        before = world.activities.get(world.code)
        world.clock.advance(1.5)
        resends = []
        for answers in [("甲", "乙")] * 10 + [("改一", "改二")] * 10:
            resends.append(
                await world.submissions.submit(world.code, token, _attempt(1, answers))
            )
        return world, first, before, resends

    world, first, before, resends = asyncio.run(scenario())
    original = first.value.submission
    assert first.value.kind is DecisionKind.ACCEPTED
    for outcome in resends:
        assert outcome.ok
        assert outcome.value.kind is DecisionKind.ALREADY_SUBMITTED
        assert outcome.value.submission == original
        assert outcome.value.submission.received_at == original.received_at
        assert outcome.value.submission.sequence == original.sequence
    ledger = world.store.get(world.code)
    assert ledger.submissions == (original,) and ledger.next_sequence == 2
    assert world.activities.get(world.code) == before
    assert len(world.publisher.published) == 1
