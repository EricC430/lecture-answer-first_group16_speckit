"""核心單元測試共用的建構函式。"""

import dataclasses
from types import MappingProxyType

from lecture_quiz.core.activity.commands import CreateActivity, Teacher
from lecture_quiz.core.activity.models import Activity, Group
from lecture_quiz.core.activity.results import IssuedSecrets
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.conftest import FAKE_CLOCK_START

NOW = FAKE_CLOCK_START
TEACHER_HASH = "a" * 64
OTHER_TEACHER_HASH = "b" * 64
TEACHER = Teacher(TEACHER_HASH)
MAX_GROUPS = 6


def new_activity(code: str = "K7QH2M") -> Activity:
    """以狀態機建立一個準備中的活動。"""
    transition = ActivityStateMachine.apply(
        None,
        CreateActivity(TEACHER, max_groups_raw=MAX_GROUPS),
        NOW,
        IssuedSecrets(activity_code=code, teacher_token_hash=TEACHER_HASH),
    )
    assert transition.ok and transition.activity is not None
    return transition.activity


def with_questions(activity: Activity, *numbers: int) -> Activity:
    return dataclasses.replace(activity, question_numbers=numbers or (1, 2, 3, 4))


def with_groups(activity: Activity, *numbers: int) -> Activity:
    groups = {**activity.groups, **{n: Group(n, f"CRED{n:02d}") for n in numbers}}
    return dataclasses.replace(activity, groups=MappingProxyType(groups))
