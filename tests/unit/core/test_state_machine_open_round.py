"""T042：開輪與規則快照（US3）。"""

import dataclasses
from datetime import timedelta
from types import MappingProxyType

import pytest

from lecture_quiz.core.activity.commands import OpenRound
from lecture_quiz.core.activity.models import Group, Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import (
    NOW,
    TEACHER,
    new_activity,
    with_groups,
    with_questions,
)


def open_round(activity, **kwargs):
    return ActivityStateMachine.apply(activity, OpenRound(TEACHER, **kwargs), NOW)


def test_default_selects_all_unsolved_without_fair_mode_or_countdown():
    """Scenario: US3-AS1

    question_numbers=None 時選取全部未成功題，公平模式預設關閉，沒有截止時間。
    """
    activity = with_questions(new_activity(), 1, 2, 3, 4)
    transition = open_round(activity)
    assert transition.ok and transition.changed
    rules = transition.activity.current_round.rules
    assert rules.question_numbers == (1, 2, 3, 4)
    assert rules.fair_mode is False
    assert rules.countdown_seconds is None
    assert rules.deadline is None


def test_open_two_questions_creates_round_one_with_baseline():
    """Scenario: US3-AS2

    選兩題開輪：建立第 1 輪，保存各組歷史成功次數基準，進入搶答中，版本加 1。
    """
    activity = with_groups(with_questions(new_activity()), "第一組", "第二組")
    groups = dict(activity.groups)
    groups["第二組"] = Group("第二組", success_count=3)
    activity = dataclasses.replace(activity, groups=MappingProxyType(groups))
    transition = open_round(activity, question_numbers=(1, 3))
    new = transition.activity
    assert new.stage is Stage.ROUND_OPEN
    assert new.version == activity.version + 1
    assert len(new.rounds) == 1
    current = new.current_round
    assert current.number == 1
    assert current.rules.question_numbers == (1, 3)
    assert dict(current.baseline) == {"第一組": 0, "第二組": 3}
    assert current.opened_at == NOW
    assert current.closed is False


def test_no_questions_is_rejected():
    """Scenario: US3-AS3

    從未成功匯入題目時開輪被拒（NO_QUESTIONS），維持準備中。
    """
    activity = new_activity()
    transition = open_round(activity)
    assert transition.rejection is RejectionReason.NO_QUESTIONS
    assert transition.activity == activity


@pytest.mark.parametrize(
    ("setup", "kwargs", "reason"),
    [
        (lambda a: a, {"question_numbers": ()}, RejectionReason.INVALID_SELECTION),
        (
            lambda a: dataclasses.replace(a, solved_questions=frozenset({2})),
            {"question_numbers": (1, 2)},
            RejectionReason.INVALID_SELECTION,
        ),
        (
            lambda a: dataclasses.replace(a, stage=Stage.RESULT_PENDING),
            {},
            RejectionReason.STAGE_NOT_ALLOWED,
        ),
    ],
    ids=["zero-questions", "solved-question", "result-pending"],
)
def test_invalid_open_is_rejected_without_change(setup, kwargs, reason):
    """Scenario: US3-AS4

    選零題、選已成功題、在結果未定案時開新輪，全部被拒，狀態不變。
    """
    activity = setup(with_questions(new_activity()))
    transition = open_round(activity, **kwargs)
    assert transition.rejection is reason
    assert transition.activity == activity


def test_open_again_during_round_is_rules_locked():
    """Scenario: US3-AS5

    搶答中再送開輪（修改題目、模式或截止時間）回傳 RULES_LOCKED，規則不變。
    """
    opened = open_round(with_questions(new_activity()), question_numbers=(1,)).activity
    transition = open_round(
        opened, question_numbers=(2,), fair_mode=True, countdown_raw=30
    )
    assert transition.rejection is RejectionReason.RULES_LOCKED
    assert transition.activity == opened


@pytest.mark.parametrize("raw", [0, 3601, 2.5, "10"])
def test_invalid_countdown_creates_no_round(raw):
    """Scenario: US3-AS6"""
    activity = with_questions(new_activity())
    transition = open_round(activity, countdown_raw=raw)
    assert transition.rejection is RejectionReason.INVALID_COUNTDOWN
    assert transition.activity == activity


@pytest.mark.parametrize("seconds", [1, 60, 3600])
def test_countdown_sets_deadline(seconds):
    transition = open_round(
        with_questions(new_activity()), countdown_raw=seconds, fair_mode=True
    )
    rules = transition.activity.current_round.rules
    assert rules.countdown_seconds == seconds
    assert rules.deadline == NOW + timedelta(seconds=seconds)
    assert rules.fair_mode is True
