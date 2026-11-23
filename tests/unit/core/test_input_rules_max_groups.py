"""T089：組數上限的輸入規則（US1-AS7、FR-036）。"""

import pytest

from lecture_quiz.core.activity.commands import CreateActivity
from lecture_quiz.core.activity.input_rules import InputRules, InvalidInputError
from lecture_quiz.core.activity.results import IssuedSecrets, RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, TEACHER, TEACHER_HASH, new_activity

ISSUED = IssuedSecrets(activity_code="K7QH2M", teacher_token_hash=TEACHER_HASH)


@pytest.mark.parametrize("raw", [1, 6, 99])
def test_valid_max_groups(raw):
    assert InputRules.validate_max_groups(raw) == raw


@pytest.mark.parametrize("raw", [0, -1, 100, 2.5, "6", "", None, True, [6]])
def test_invalid_max_groups(raw):
    with pytest.raises(InvalidInputError) as exc:
        InputRules.validate_max_groups(raw)
    assert exc.value.reason is RejectionReason.INVALID_MAX_GROUPS


@pytest.mark.parametrize("raw", [0, 100, 2.5, "6", None])
def test_create_with_invalid_max_groups_is_rejected(raw):
    """Scenario: US1-AS7

    組數上限是 0、小數、非數字、空白或大於 99 時拒絕建立，不產生活動。
    """
    transition = ActivityStateMachine.apply(
        None, CreateActivity(TEACHER, max_groups_raw=raw), NOW, ISSUED
    )
    assert transition.ok is False
    assert transition.activity is None
    assert transition.rejection is RejectionReason.INVALID_MAX_GROUPS


@pytest.mark.parametrize("raw", [1, 99])
def test_create_with_boundary_max_groups(raw):
    """Scenario: US1-AS7

    組數上限為 1 或 99 時可以正常建立。
    """
    transition = ActivityStateMachine.apply(
        None, CreateActivity(TEACHER, max_groups_raw=raw), NOW, ISSUED
    )
    assert transition.ok and transition.activity is not None
    assert transition.activity.max_groups == raw


def test_create_records_max_groups():
    """Scenario: US1-AS1

    建立時指定的組數上限寫入活動。
    """
    assert new_activity().max_groups == 6
