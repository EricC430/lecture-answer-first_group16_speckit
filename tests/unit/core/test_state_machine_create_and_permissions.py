"""T023：建立活動與老師權限（US1、SC-002）。

老師專用操作的範圍限於 001 擁有的操作：開輪、關輪、定案、結束、取消、
匯入題號（ReplaceQuestions）。
判錯、撤銷判錯、匯出、刪除組別的權限，由 004、005、
US7 各自測試（jacky0407 2026-11-23 決定）。
"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import (
    Anonymous,
    CancelActivity,
    CloseRound,
    Device,
    EndActivity,
    Finalize,
    OpenRound,
    ReplaceQuestions,
    Teacher,
)
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import (
    NOW,
    OTHER_TEACHER_HASH,
    TEACHER,
    TEACHER_HASH,
    new_activity,
    with_questions,
)

TEACHER_ONLY_COMMANDS = [
    lambda actor: OpenRound(actor),
    lambda actor: CloseRound(actor),
    lambda actor: Finalize(actor),
    lambda actor: EndActivity(actor),
    lambda actor: CancelActivity(actor),
    lambda actor: ReplaceQuestions(actor, (1, 2)),
]


def test_create_activity_starts_preparing():
    """Scenario: US1-AS1

    建立後為準備中、version == 1，沒有題目也沒有輪次。
    """
    activity = new_activity()
    assert activity.stage is Stage.PREPARING
    assert activity.version == 1
    assert activity.changed_at == NOW
    assert activity.code == "K7QH2M"
    assert activity.teacher.token_hash == TEACHER_HASH
    assert activity.question_numbers == ()
    assert activity.rounds == ()
    assert dict(activity.groups) == {}


def test_create_requires_issued_secrets():
    from lecture_quiz.core.activity.commands import CreateActivity

    with pytest.raises(ValueError):
        ActivityStateMachine.apply(None, CreateActivity(TEACHER), NOW, None)


@pytest.mark.parametrize(
    "actor",
    [Device("d" * 64), Teacher(OTHER_TEACHER_HASH), Anonymous(), Device(TEACHER_HASH)],
    ids=["device", "other-teacher", "anonymous", "device-with-teacher-hash"],
)
@pytest.mark.parametrize("make_command", TEACHER_ONLY_COMMANDS)
def test_non_teacher_is_rejected_without_change(actor, make_command):
    """Scenario: US1-AS4, US1-AS5, US1-AS6

    學生裝置、別的活動的老師、沒有身分的請求，對老師專用操作一律 NOT_TEACHER，
    活動完全不變。
    """
    for stage in (
        Stage.PREPARING,
        Stage.ROUND_OPEN,
        Stage.RESULT_PENDING,
        Stage.RESULT_FINAL,
    ):
        activity = dataclasses.replace(with_questions(new_activity()), stage=stage)
        transition = ActivityStateMachine.apply(activity, make_command(actor), NOW)
        assert not transition.ok
        assert transition.rejection is RejectionReason.NOT_TEACHER
        assert not transition.changed
        assert transition.activity == activity


@pytest.mark.parametrize("make_command", TEACHER_ONLY_COMMANDS)
def test_teacher_of_this_activity_passes_permission_check(make_command):
    activity = with_questions(new_activity())
    transition = ActivityStateMachine.apply(activity, make_command(TEACHER), NOW)
    assert transition.rejection is not RejectionReason.NOT_TEACHER
