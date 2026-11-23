"""T065：結束與取消活動（US5）。"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import (
    CancelActivity,
    CloseRound,
    EndActivity,
    Finalize,
    FinalizeOutcome,
    JoinGroup,
    OpenRound,
    ReplaceQuestions,
)
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    describe_rejection,
)
from lecture_quiz.core.activity.snapshot_view import SnapshotView
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, TEACHER, new_activity, with_questions

apply = ActivityStateMachine.apply


def finalized(solved=frozenset({1, 2})):
    activity = with_questions(new_activity(), 1, 2, 3)
    activity = apply(activity, OpenRound(TEACHER, (1, 2, 3)), NOW).activity
    activity = apply(activity, CloseRound(TEACHER), NOW).activity
    return apply(activity, Finalize(TEACHER, FinalizeOutcome(solved)), NOW).activity


def test_end_after_finalize_lists_unsolved():
    """Scenario: US5-AS1

    定案後結束：已結束，未成功題清單含第 3 題；快照的 unsolvedQuestions 也列出。
    """
    activity = finalized()
    transition = apply(activity, EndActivity(TEACHER), NOW)
    assert transition.ok and transition.changed
    ended = transition.activity
    assert ended.stage is Stage.ENDED
    assert ended.unsolved_questions == (3,)
    assert SnapshotView.for_teacher(ended).to_json()["unsolvedQuestions"] == [3]


@pytest.mark.parametrize("stage", [Stage.ROUND_OPEN, Stage.RESULT_PENDING])
def test_end_during_round_or_pending_rejected(stage):
    """Scenario: US5-AS3

    搶答中或結果未定案時結束被拒，訊息含「請先關輪並確認定案」，階段不變。
    """
    activity = dataclasses.replace(finalized(), stage=stage)
    command = EndActivity(TEACHER)
    transition = apply(activity, command, NOW)
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert transition.activity == activity
    message = describe_rejection(transition.rejection, activity.stage, command)
    assert "請先關輪並確認定案" in message


def test_cancel_while_preparing_then_everything_rejected():
    """Scenario: US5-AS4

    準備中取消 → 已取消（與已結束不同），之後任何操作都被拒。
    """
    activity = with_questions(new_activity())
    cancelled = apply(activity, CancelActivity(TEACHER), NOW).activity
    assert cancelled.stage is Stage.CANCELLED
    assert cancelled.stage is not Stage.ENDED
    for command in (
        OpenRound(TEACHER),
        CloseRound(TEACHER),
        Finalize(TEACHER),
        EndActivity(TEACHER),
        CancelActivity(TEACHER),
        ReplaceQuestions(TEACHER, (1,)),
    ):
        transition = apply(cancelled, command, NOW)
        assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
        assert transition.activity == cancelled
    join = JoinGroup(TEACHER, 1)
    rejected = apply(cancelled, join, NOW, IssuedSecrets(device_token_hash="d" * 64))
    assert rejected.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert (
        describe_rejection(rejected.rejection, cancelled.stage, join)
        == "活動已取消，無法加入。"
    )


@pytest.mark.parametrize(
    "stage", [Stage.ROUND_OPEN, Stage.RESULT_PENDING, Stage.RESULT_FINAL]
)
def test_cancel_only_while_preparing(stage):
    activity = dataclasses.replace(finalized(), stage=stage)
    assert apply(activity, CancelActivity(TEACHER), NOW).rejection is (
        RejectionReason.STAGE_NOT_ALLOWED
    )


def test_ended_rejects_join():
    """Scenario: US5-AS5

    已結束時新組別加入被拒，
    訊息說明活動已結束（提交的拒絕見服務層 accepts_submission）。
    """
    ended = apply(finalized(), EndActivity(TEACHER), NOW).activity
    join = JoinGroup(TEACHER, 2)
    transition = apply(ended, join, NOW, IssuedSecrets(device_token_hash="d" * 64))
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert (
        describe_rejection(transition.rejection, ended.stage, join)
        == "活動已結束，無法加入。"
    )


def test_end_while_preparing_rejected():
    """Scenario: US5-AS6

    準備中送結束（不是取消）被拒，訊息為「準備中只能取消活動」。
    """
    activity = with_questions(new_activity())
    command = EndActivity(TEACHER)
    transition = apply(activity, command, NOW)
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert (
        describe_rejection(transition.rejection, activity.stage, command)
        == "準備中只能取消活動。"
    )
