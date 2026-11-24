"""US3：截止邊界、關輪、接收序號與接收時間（FakeClock；SC-004、FR-016）。"""

import asyncio

from lecture_quiz.core.round_submission.models import SubmissionAttempt
from lecture_quiz.core.round_submission.rules import DecisionKind, SubmissionRejection
from tests.unit.app.round_submission.conftest import open_world


def _attempt(question, answers, round_number=1):
    return SubmissionAttempt(round_number, question, list(answers))


def _deadline_case(offset_seconds):
    async def scenario():
        world = await open_world(countdown=60)
        world.clock.advance(60 + offset_seconds)
        outcome = await world.submissions.submit(
            world.code, world.devices[1][0], _attempt(3, ("丙",))
        )
        return world, outcome

    return asyncio.run(scenario())


def test_one_ms_before_deadline_is_accepted():
    """Scenario: US3-AS1（OpenSpec「截止邊界」：截止前 1 毫秒接受）。"""
    world, outcome = _deadline_case(-0.001)
    assert outcome.value.kind is DecisionKind.ACCEPTED
    assert outcome.value.submission.received_at == world.clock.now()


def test_at_or_after_deadline_is_rejected():
    """Scenario: US3-AS2（恰於或晚於截止時間拒絕且不保存）。"""
    for offset in (0, 0.001):
        world, outcome = _deadline_case(offset)
        assert outcome.value.rejection is SubmissionRejection.ROUND_CLOSED, offset
        assert world.store.get(world.code).submissions == ()
        assert world.publisher.published == []


def test_no_countdown_accepts_until_teacher_closes():
    """Scenario: US3-AS3（無倒數輪次在老師關輪前一直接受，關輪後拒絕）。"""

    async def scenario():
        world = await open_world()
        token = world.devices[1][0]
        world.clock.advance(3600)
        before = await world.submissions.submit(world.code, token, _attempt(3, ("丙",)))
        assert (await world.activities.close_round(world.code, world.teacher)).ok
        after = await world.submissions.submit(world.code, token, _attempt(4, ("丁",)))
        return world, before, after

    world, before, after = asyncio.run(scenario())
    assert before.value.kind is DecisionKind.ACCEPTED
    assert after.value.rejection is SubmissionRejection.ROUND_CLOSED
    assert len(world.store.get(world.code).submissions) == 1


def test_sequence_increases_across_rounds_and_skips_rejections():
    """FR-016：序號跨輪遞增；被拒不消耗序號。"""

    async def scenario():
        world = await open_world()
        g1, g2 = world.devices[1][0], world.devices[2][0]
        results = [
            await world.submissions.submit(world.code, g1, _attempt(1, ("a", "b"))),
            await world.submissions.submit(world.code, g2, _attempt(1, ("a",))),
            await world.submissions.submit(world.code, g2, _attempt(1, ("c", "d"))),
        ]
        assert (await world.activities.close_round(world.code, world.teacher)).ok
        assert (await world.activities.finalize(world.code, world.teacher)).ok
        opened = await world.activities.open_round(world.code, world.teacher, (3,))
        assert opened.ok
        results.append(
            await world.submissions.submit(world.code, g1, _attempt(3, ("e",), 2))
        )
        return results

    results = asyncio.run(scenario())
    sequences = [
        r.value.submission.sequence
        for r in results
        if r.value.kind is DecisionKind.ACCEPTED
    ]
    assert sequences == [1, 2, 3]
    assert results[1].value.kind is DecisionKind.REJECTED


def test_reader_returns_sorted_submissions():
    """T040：`SubmissionReader` 依（接收時間, 接收序號）回傳，給 004、005。"""

    async def scenario():
        world = await open_world(groups=(1, 2, 3))
        for group, question, answers in ((2, 3, ("x",)), (1, 3, ("y",))):
            await world.submissions.submit(
                world.code, world.devices[group][0], _attempt(question, answers)
            )
        world.clock.advance(1)
        await world.submissions.submit(
            world.code, world.devices[3][0], _attempt(4, ("z",))
        )
        return world

    world = asyncio.run(scenario())
    round_one = world.submissions.round_submissions(world.code, 1)
    assert isinstance(round_one, tuple)
    assert [(s.group_number, s.sequence) for s in round_one] == [(2, 1), (1, 2), (3, 3)]
    assert world.submissions.all_submissions(world.code) == round_one
    assert world.submissions.round_submissions(world.code, 2) == ()
    assert world.submissions.round_submissions("NOPE00", 1) == ()
