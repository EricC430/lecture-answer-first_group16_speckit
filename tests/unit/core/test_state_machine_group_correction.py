"""T071：離開本組、刪除空組與提交標記（US7、alignment 2026-11-23 B4、B5）。"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import (
    Anonymous,
    DeleteGroup,
    Device,
    JoinGroup,
    LeaveGroup,
    MarkGroupSubmitted,
    System,
)
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    describe_rejection,
)
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, TEACHER, joining_activity

apply = ActivityStateMachine.apply
X, Y = "1" * 64, "2" * 64


def _join(activity, device, number, credential=None, new_cred="AAAAAA"):
    t = apply(
        activity,
        JoinGroup(Anonymous(), number, credential),
        NOW,
        IssuedSecrets(device_token_hash=device, group_credential=new_cred),
    )
    assert t.ok, t
    return t.activity


def two_devices_in_group_one(stage=Stage.JOINING):
    activity = _join(joining_activity(), X, 1)
    activity = _join(activity, Y, 1, "AAAAAA")
    groups = dict(activity.groups)
    groups[1] = dataclasses.replace(groups[1], success_count=2)
    return dataclasses.replace(activity, groups=groups, stage=stage)


@pytest.mark.parametrize(
    "stage", [Stage.JOINING, Stage.RESULT_PENDING, Stage.RESULT_FINAL]
)
def test_leave_removes_only_that_device(stage):
    """Scenario: US7-AS1

    準備中、結果未定案、結果已定案時離開，只移除該裝置；組別、其他裝置與成功次數不變。
    """
    activity = two_devices_in_group_one(stage)
    t = apply(activity, LeaveGroup(Device(X)), NOW)
    assert t.ok and t.changed
    assert X not in t.activity.devices
    assert t.activity.devices[Y].group_number == 1
    assert t.activity.groups[1] == activity.groups[1]


def test_after_leaving_device_can_join_another_group():
    """Scenario: US7-AS2

    離開第 1 組後，同一個裝置可以加入第 2 組。
    """
    activity = two_devices_in_group_one()
    activity = apply(activity, LeaveGroup(Device(X)), NOW).activity
    t = apply(
        activity,
        JoinGroup(Device(X), 2, None),
        NOW,
        IssuedSecrets(device_token_hash=X, group_credential="BBBBBB"),
    )
    assert t.ok
    assert t.activity.devices[X].group_number == 2


def test_leave_during_round_open_is_rejected():
    """Scenario: US7-AS3

    搶答中離開被拒，說明搶答中不能換組，身分不變。
    """
    activity = two_devices_in_group_one(Stage.ROUND_OPEN)
    command = LeaveGroup(Device(X))
    t = apply(activity, command, NOW)
    assert t.rejection is RejectionReason.NO_GROUP_SWITCH_DURING_ROUND
    assert t.activity == activity
    assert "搶答進行中不能換組" in describe_rejection(
        t.rejection, activity.stage, command, activity
    )


def test_submissions_stay_with_original_group_after_leave():
    """Scenario: US7-AS4

    原組的提交紀錄在裝置離開後仍屬於原組。
    """
    activity = two_devices_in_group_one(Stage.ROUND_OPEN)
    activity = apply(activity, MarkGroupSubmitted(System(), 1), NOW).activity
    activity = dataclasses.replace(activity, stage=Stage.RESULT_PENDING)
    t = apply(activity, LeaveGroup(Device(X)), NOW)
    assert t.activity.groups[1].has_submissions is True


def test_delete_empty_group_removes_group_and_devices_and_frees_number():
    """Scenario: US7-AS5

    刪除沒有提交的組：組與其裝置都移除；組號可再使用，會建立新組與新憑證。
    """
    activity = _join(joining_activity(), X, 5)
    t = apply(activity, DeleteGroup(TEACHER, 5), NOW)
    assert t.ok and t.changed
    assert 5 not in t.activity.groups
    assert X not in t.activity.devices
    again = _join(t.activity, Y, 5, new_cred="CCCCCC")
    assert again.groups[5].join_credential == "CCCCCC"


def test_delete_group_with_submissions_is_rejected():
    """Scenario: US7-AS6

    已有提交紀錄的組不能刪除，活動不變。
    """
    activity = two_devices_in_group_one(Stage.ROUND_OPEN)
    activity = apply(activity, MarkGroupSubmitted(System(), 1), NOW).activity
    activity = dataclasses.replace(activity, stage=Stage.RESULT_PENDING)
    t = apply(activity, DeleteGroup(TEACHER, 1), NOW)
    assert t.rejection is RejectionReason.GROUP_HAS_SUBMISSIONS
    assert t.activity == activity


def test_delete_missing_group_and_permission_and_leave_without_group():
    """刪除不存在的組號、學生刪除組別、未加入任何組的裝置離開，都被拒絕。"""
    activity = _join(joining_activity(), X, 1)
    missing = DeleteGroup(TEACHER, 4)
    t = apply(activity, missing, NOW)
    assert t.rejection is RejectionReason.GROUP_NOT_FOUND
    assert describe_rejection(t.rejection, activity.stage, missing, activity) == (
        "找不到第 4 組。"
    )
    assert (
        apply(activity, DeleteGroup(Device(X), 1), NOW).rejection
        is RejectionReason.NOT_TEACHER
    )
    for actor in (Anonymous(), Device(Y)):
        assert (
            apply(activity, LeaveGroup(actor), NOW).rejection
            is RejectionReason.NOT_IN_GROUP
        )


def test_mark_group_submitted_only_during_round_open():
    """MarkGroupSubmitted 只在搶答中生效；重複標記不改變版本。"""
    activity = _join(joining_activity(), X, 1)
    assert (
        apply(activity, MarkGroupSubmitted(System(), 1), NOW).rejection
        is RejectionReason.STAGE_NOT_ALLOWED
    )
    open_ = dataclasses.replace(activity, stage=Stage.ROUND_OPEN)
    first = apply(open_, MarkGroupSubmitted(System(), 1), NOW)
    assert first.changed and first.activity.groups[1].has_submissions
    second = apply(first.activity, MarkGroupSubmitted(System(), 1), NOW)
    assert second.ok and not second.changed
