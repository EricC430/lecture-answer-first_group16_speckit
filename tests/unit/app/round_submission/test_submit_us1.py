"""US1：`SubmissionService.submit` 接受與拒絕（FR-005）。"""

import asyncio

from lecture_quiz.core.round_submission.models import SubmissionAttempt
from lecture_quiz.core.round_submission.rules import DecisionKind, SubmissionRejection
from tests.unit.app.round_submission.conftest import open_world


def _attempt(question, answers, round_number=1):
    return SubmissionAttempt(round_number, question, list(answers))


def test_accepted_submission_is_stored_and_pushed():
    """Scenario: US1-AS1（接受後保存、老師 revision + 1、version 不變、推送一次）。"""

    async def scenario():
        world = await open_world()
        before = world.activities.get(world.code)
        outcome = await world.submissions.submit(
            world.code, world.devices[1][0], _attempt(2, ("乙一", "乙二"))
        )
        return world, before, outcome

    world, before, outcome = asyncio.run(scenario())
    assert outcome.ok
    decision = outcome.value
    assert decision.kind is DecisionKind.ACCEPTED
    assert decision.submission.received_at == world.clock.now()
    ledger = world.store.get(world.code)
    assert ledger.submissions == (decision.submission,)
    after = world.activities.get(world.code)
    assert after.revision == before.revision + 1
    assert after.version == before.version
    assert after.groups[1].has_submissions
    assert len(world.publisher.published) == 1


def test_rejected_submission_changes_nothing():
    """Scenario: US1-AS3（被拒：不保存、不消耗序號、不改版本、不推送；FR-005）。"""

    async def scenario():
        world = await open_world()
        before = world.activities.get(world.code)
        outcomes = [
            await world.submissions.submit(
                world.code, world.devices[1][0], _attempt(q, answers)
            )
            for q, answers in ((1, ("甲", "")), (1, ("甲",)), (9, ("甲",)))
        ]
        return world, before, outcomes

    world, before, outcomes = asyncio.run(scenario())
    assert [o.value.rejection for o in outcomes] == [
        SubmissionRejection.BLANK_EMPTY,
        SubmissionRejection.WRONG_BLANK_COUNT,
        SubmissionRejection.QUESTION_NOT_OPEN,
    ]
    assert all(o.ok and o.value.kind is DecisionKind.REJECTED for o in outcomes)
    ledger = world.store.get(world.code)
    assert ledger.submissions == () and ledger.next_sequence == 1
    after = world.activities.get(world.code)
    assert after == before
    assert world.publisher.published == []


def test_gone_and_not_in_group_become_decisions():
    async def scenario():
        world = await open_world()
        gone = await world.submissions.submit("ZZZZZZ", "x", _attempt(1, ("a", "b")))
        stranger = await world.submissions.submit(
            world.code, "not-a-token", _attempt(1, ("a", "b"))
        )
        return gone, stranger

    gone, stranger = asyncio.run(scenario())
    assert gone.ok and gone.value.rejection is SubmissionRejection.ACTIVITY_GONE
    assert stranger.value.rejection is SubmissionRejection.NOT_IN_GROUP


def test_code_is_normalized():
    async def scenario():
        world = await open_world()
        outcome = await world.submissions.submit(
            f" {world.code.lower()} ", world.devices[1][0], _attempt(3, ("丙",))
        )
        return world, outcome

    world, outcome = asyncio.run(scenario())
    assert outcome.value.kind is DecisionKind.ACCEPTED
    assert outcome.value.submission.activity_code == world.code
    assert len(world.store.get(world.code).submissions) == 1
