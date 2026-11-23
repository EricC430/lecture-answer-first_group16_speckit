"""T052：關輪只一次、定案後才能往下走（US4）。"""

import dataclasses
from datetime import timedelta
from types import MappingProxyType

import pytest

from lecture_quiz.core.activity.commands import (
    CloseRound,
    EndActivity,
    Finalize,
    FinalizeOutcome,
    OpenRound,
    System,
)
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import (
    NOW,
    TEACHER,
    new_activity,
    with_groups,
    with_questions,
)

apply = ActivityStateMachine.apply


def opened(countdown=None, questions=(1, 2)):
    activity = with_groups(with_questions(new_activity()), 1, 2)
    return apply(
        activity, OpenRound(TEACHER, questions, False, countdown), NOW
    ).activity


def test_teacher_close_moves_to_result_pending():
    """Scenario: US4-AS1

    老師關輪後進入結果未定案，closed=True，close_cause=teacher，版本加 1。
    """
    activity = opened()
    later = NOW + timedelta(seconds=5)
    transition = apply(activity, CloseRound(TEACHER), later)
    assert transition.ok and transition.changed
    new = transition.activity
    assert new.stage is Stage.RESULT_PENDING
    assert new.version == activity.version + 1
    current = new.current_round
    assert current.closed is True
    assert current.closed_at == later
    assert current.close_cause == "teacher"


def test_system_close_only_after_deadline():
    """Scenario: US4-AS2

    System 關輪在 now >= deadline 時才生效（行為與手動關輪相同）；
    截止前回傳成功但無變化。
    """
    activity = opened(countdown=60)
    deadline = activity.current_round.rules.deadline
    early = apply(activity, CloseRound(System()), deadline - timedelta(microseconds=1))
    assert early.ok and not early.changed
    assert early.activity == activity
    on_time = apply(activity, CloseRound(System()), deadline)
    assert on_time.changed
    assert on_time.activity.stage is Stage.RESULT_PENDING
    assert on_time.activity.current_round.close_cause == "deadline"


def test_system_close_without_countdown_is_noop():
    activity = opened()
    transition = apply(activity, CloseRound(System()), NOW + timedelta(days=1))
    assert transition.ok and not transition.changed


@pytest.mark.parametrize("second_actor", [TEACHER, System()], ids=["teacher", "system"])
def test_second_close_is_idempotent(second_actor):
    """Scenario: US4-AS3

    已關輪後再收到 CloseRound（老師或倒數），回傳成功但 changed=False，版本不變。
    """
    closed = apply(opened(countdown=10), CloseRound(TEACHER), NOW).activity
    late = NOW + timedelta(seconds=30)
    transition = apply(closed, CloseRound(second_actor), late)
    assert transition.ok and not transition.changed
    assert transition.activity == closed
    finalized = apply(closed, Finalize(TEACHER), late).activity
    again = apply(finalized, CloseRound(second_actor), late)
    assert again.ok and not again.changed


def test_result_pending_never_moves_by_itself():
    """Scenario: US4-AS4

    結果未定案時，倒數或時間經過都不會自動定案或開下一輪。
    """
    closed = apply(opened(countdown=10), CloseRound(TEACHER), NOW).activity
    for seconds in (10, 3600, 86400):
        transition = apply(
            closed, CloseRound(System()), NOW + timedelta(seconds=seconds)
        )
        assert transition.activity.stage is Stage.RESULT_PENDING
        assert not transition.changed


def test_open_during_result_pending_rejected():
    """Scenario: US4-AS5

    結果未定案時開下一輪被拒（STAGE_NOT_ALLOWED）。
    """
    closed = apply(opened(), CloseRound(TEACHER), NOW).activity
    transition = apply(closed, OpenRound(TEACHER, (3,)), NOW)
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert transition.activity == closed


def test_finalize_then_next_round_only_unsolved():
    """Scenario: US4-AS6

    定案後為結果已定案，已成功題與成功次數依 outcome 更新；再開輪時 number=2，
    只能選未成功題。
    """
    closed = apply(opened(questions=(1, 2)), CloseRound(TEACHER), NOW).activity
    outcome = FinalizeOutcome(frozenset({1}), MappingProxyType({1: 1}))
    final = apply(closed, Finalize(TEACHER, outcome), NOW)
    assert final.ok and final.changed
    new = final.activity
    assert new.stage is Stage.RESULT_FINAL
    assert new.solved_questions == frozenset({1})
    assert new.groups[1].success_count == 1
    assert new.groups[2].success_count == 0

    reject = apply(new, OpenRound(TEACHER, (1, 3)), NOW)
    assert reject.rejection is RejectionReason.INVALID_SELECTION
    second = apply(new, OpenRound(TEACHER), NOW).activity
    assert second.current_round.number == 2
    assert second.current_round.rules.question_numbers == (2, 3, 4)
    assert dict(second.current_round.baseline) == {1: 1, 2: 0}


@pytest.mark.parametrize(
    "outcome",
    [
        FinalizeOutcome(frozenset({3})),  # 不是本輪的題目
        FinalizeOutcome(frozenset(), MappingProxyType({"不存在的組": 1})),
        FinalizeOutcome(frozenset(), MappingProxyType({1: -1})),
    ],
)
def test_invalid_outcome_rejected(outcome):
    closed = apply(opened(questions=(1, 2)), CloseRound(TEACHER), NOW).activity
    transition = apply(closed, Finalize(TEACHER, outcome), NOW)
    assert transition.rejection is RejectionReason.INVALID_SELECTION
    assert transition.activity == closed


def test_end_requires_finalize():
    closed = apply(opened(), CloseRound(TEACHER), NOW).activity
    transition = apply(closed, EndActivity(TEACHER), NOW)
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED


def test_is_deadline_passed_boundary():
    activity = opened(countdown=60)
    current = activity.current_round
    deadline = current.rules.deadline
    assert not ActivityStateMachine.is_deadline_passed(
        current, deadline - timedelta(microseconds=1)
    )
    assert ActivityStateMachine.is_deadline_passed(current, deadline)
    no_countdown = dataclasses.replace(
        current, rules=dataclasses.replace(current.rules, deadline=None)
    )
    assert not ActivityStateMachine.is_deadline_passed(no_countdown, deadline)
