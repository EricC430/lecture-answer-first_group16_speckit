"""T043：ReplaceQuestions（002 的匯入入口；原則 III 被拒時既有題目不變）。"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import Anonymous, ReplaceQuestions
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, TEACHER, new_activity, with_questions


def test_teacher_replaces_questions_while_preparing():
    activity = dataclasses.replace(
        with_questions(new_activity(), 1, 2), solved_questions=frozenset({1})
    )
    transition = ActivityStateMachine.apply(
        activity, ReplaceQuestions(TEACHER, (5, 6, 7)), NOW
    )
    assert transition.ok and transition.changed
    assert transition.activity.question_numbers == (5, 6, 7)
    assert transition.activity.solved_questions == frozenset()
    assert transition.activity.version == activity.version + 1


@pytest.mark.parametrize(
    "stage", [Stage.ROUND_OPEN, Stage.RESULT_PENDING, Stage.RESULT_FINAL]
)
def test_rejected_outside_preparing_keeps_questions(stage):
    activity = dataclasses.replace(with_questions(new_activity(), 1, 2), stage=stage)
    transition = ActivityStateMachine.apply(
        activity, ReplaceQuestions(TEACHER, (9,)), NOW
    )
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert transition.activity.question_numbers == (1, 2)


def test_non_teacher_rejected():
    activity = with_questions(new_activity(), 1, 2)
    transition = ActivityStateMachine.apply(
        activity, ReplaceQuestions(Anonymous(), (9,)), NOW
    )
    assert transition.rejection is RejectionReason.NOT_TEACHER
    assert transition.activity == activity


@pytest.mark.parametrize("numbers", [(), (1, 1), (0,), (-2,), (True,)])
def test_invalid_numbers_rejected_and_unchanged(numbers):
    activity = with_questions(new_activity(), 1, 2)
    transition = ActivityStateMachine.apply(
        activity, ReplaceQuestions(TEACHER, numbers), NOW
    )
    assert transition.rejection is RejectionReason.INVALID_SELECTION
    assert transition.activity == activity
