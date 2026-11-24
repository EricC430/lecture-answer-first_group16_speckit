"""001 為 003 新增的 `RecordSubmission` 指令（003 研究 R2、R5）。

只在搶答中、尚未截止、組別存在時成功；每次成功都算變更（revision + 1），
但公開狀態不變，所以 version 與 changed_at 不變。
"""

import dataclasses
from datetime import timedelta

import pytest

from lecture_quiz.core.activity.commands import (
    OpenRound,
    RecordSubmission,
    System,
)
from lecture_quiz.core.activity.models import Activity, Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import (
    NOW,
    TEACHER,
    joining_activity,
    with_groups,
    with_questions,
)


def _open(countdown: int | None = 60) -> Activity:
    base = with_groups(with_questions(joining_activity()), 1, 2)
    transition = ActivityStateMachine.apply(
        base, OpenRound(TEACHER, None, False, countdown), NOW
    )
    assert transition.ok and transition.activity is not None
    return transition.activity


def _record(activity: Activity, group: int = 1, *, seconds: float = 1):
    return ActivityStateMachine.apply(
        activity, RecordSubmission(System(), group), NOW + timedelta(seconds=seconds)
    )


def test_first_record_marks_group_and_bumps_revision_only():
    """第一次記錄：標記組別有提交，revision + 1，version 與 changed_at 不變。"""
    activity = _open()
    transition = _record(activity)
    assert transition.ok and transition.changed
    new = transition.activity
    assert new.groups[1].has_submissions
    assert new.revision == activity.revision + 1
    assert new.version == activity.version
    assert new.changed_at == activity.changed_at


def test_every_record_counts_as_change():
    """同組第二題：已標記過仍算變更，老師快照才能以 revision 分辨新舊。"""
    first = _record(_open()).activity
    second = _record(first, seconds=2)
    assert second.ok and second.changed
    assert second.activity.revision == first.revision + 1
    assert second.activity.version == first.version


@pytest.mark.parametrize("stage", [s for s in Stage if s is not Stage.ROUND_OPEN])
def test_other_stages_are_rejected(stage):
    """搶答中以外的 6 個階段一律拒絕，狀態不變。"""
    activity = dataclasses.replace(_open(), stage=stage)
    transition = _record(activity)
    assert not transition.ok
    assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert transition.activity == activity


def test_deadline_is_strict():
    """有截止時間：now < deadline 成功；恰好截止與之後都拒絕。"""
    activity = _open(countdown=60)
    assert _record(activity, seconds=59.999).ok
    for seconds in (60, 60.001):
        transition = _record(activity, seconds=seconds)
        assert not transition.ok
        assert transition.rejection is RejectionReason.STAGE_NOT_ALLOWED
        assert transition.activity == activity


def test_no_deadline_accepts_any_time():
    """沒有倒數的輪次：任何時間都可以記錄，直到老師關輪。"""
    assert _record(_open(countdown=None), seconds=3600 * 5).ok


def test_unknown_group_is_rejected():
    """組別不存在：GROUP_NOT_FOUND，狀態不變。"""
    activity = _open()
    transition = _record(activity, group=5)
    assert not transition.ok
    assert transition.rejection is RejectionReason.GROUP_NOT_FOUND
    assert transition.activity == activity
