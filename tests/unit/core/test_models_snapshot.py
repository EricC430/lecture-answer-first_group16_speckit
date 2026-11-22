"""T007、T011：核心資料的衍生屬性與快照共同欄位（contracts/sync-websocket.md）。"""

import dataclasses
import json
from datetime import timedelta
from types import MappingProxyType

import pytest

from lecture_quiz.core.activity.models import (
    Activity,
    Group,
    Round,
    RoundRules,
    Stage,
    TeacherIdentity,
)
from lecture_quiz.core.activity.snapshot_view import SnapshotView
from tests.conftest import FAKE_CLOCK_START

NOW = FAKE_CLOCK_START


def make_activity(**overrides):
    base = Activity(
        code="K7QH2M",
        stage=Stage.PREPARING,
        version=1,
        changed_at=NOW,
        teacher=TeacherIdentity("t" * 64),
    )
    return dataclasses.replace(base, **overrides)


def test_stage_terminal_flags():
    assert {s for s in Stage if s.is_terminal} == {Stage.ENDED, Stage.CANCELLED}


def test_activity_is_immutable():
    activity = make_activity()
    with pytest.raises(dataclasses.FrozenInstanceError):
        activity.stage = Stage.ENDED  # type: ignore[misc]
    assert isinstance(activity.groups, MappingProxyType)


def test_derived_current_round_and_unsolved_questions():
    rules = RoundRules((2, 4), False, None, None)
    round1 = Round(1, rules, NOW, MappingProxyType({}))
    activity = make_activity(
        question_numbers=(1, 2, 3, 4), solved_questions=frozenset({2}), rounds=(round1,)
    )
    assert activity.current_round == round1
    assert activity.unsolved_questions == (1, 3, 4)
    assert make_activity().current_round is None


def test_common_snapshot_fields_for_teacher_and_group():
    deadline = NOW + timedelta(seconds=60)
    rules = RoundRules((1, 3), True, 60, deadline)
    activity = make_activity(
        stage=Stage.ROUND_OPEN,
        version=12,
        question_numbers=(1, 2, 3),
        groups=MappingProxyType({"第一組": Group("第一組")}),
        rounds=(Round(1, rules, NOW, MappingProxyType({"第一組": 0})),),
    )
    for snap in (
        SnapshotView.for_teacher(activity).to_json(),
        SnapshotView.for_group(activity, "第一組").to_json(),
    ):
        assert snap["type"] == "snapshot"
        assert snap["code"] == "K7QH2M"
        assert snap["version"] == 12
        assert snap["changedAt"] == "2026-11-21T09:00:00.000+08:00"
        assert snap["stage"] == "ROUND_OPEN"
        assert snap["roundNumber"] == 1
        assert snap["openQuestions"] == [1, 3]
        assert snap["deadline"] == deadline.isoformat()
        assert snap["fairMode"] is True
        assert snap["unsolvedQuestions"] == []
        json.dumps(snap)  # 必須可以序列化


def test_snapshot_without_rounds():
    snap = SnapshotView.for_teacher(make_activity()).to_json()
    assert snap["roundNumber"] is None
    assert snap["openQuestions"] == []
    assert snap["deadline"] is None
    assert snap["fairMode"] is False
