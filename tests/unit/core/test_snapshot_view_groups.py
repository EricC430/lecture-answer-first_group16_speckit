"""T032：快照中的組別資料裁切（US2-AS3、FR-030）。"""

import json

from lecture_quiz.core.activity.commands import Anonymous, JoinGroup
from lecture_quiz.core.activity.results import IssuedSecrets
from lecture_quiz.core.activity.snapshot_view import SnapshotView
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, new_activity


def two_groups():
    activity = new_activity()
    for number, device, cred in ((5, "1", "AAAAAA"), (2, "2", "BBBBBB")):
        t = ActivityStateMachine.apply(
            activity,
            JoinGroup(Anonymous(), number, None),
            NOW,
            IssuedSecrets(device_token_hash=device * 64, group_credential=cred),
        )
        activity = t.activity
    return activity


def test_group_view_contains_only_own_group_with_credential():
    """Scenario: US2-AS3

    學生版只含本組組號、憑證與成功次數；老師版依組號排序並含每一組憑證。
    """
    activity = two_groups()
    student = SnapshotView.for_group(activity, 5).to_json()
    assert student["ownGroup"] == {
        "number": 5,
        "credential": "AAAAAA",
        "successCount": 0,
    }
    teacher = SnapshotView.for_teacher(activity).to_json()
    assert [g["number"] for g in teacher["groups"]] == [2, 5]
    assert {g["number"]: g["credential"] for g in teacher["groups"]} == {
        2: "BBBBBB",
        5: "AAAAAA",
    }
    assert teacher["groups"][0]["deviceCount"] == 1


def test_group_view_leaks_nothing_about_other_groups():
    """FR-030：學生版序列化後不含其他組的組號、憑證、組別清單或組數上限。"""
    student = SnapshotView.for_group(two_groups(), 5).to_json()
    text = json.dumps(student, ensure_ascii=False)
    assert "BBBBBB" not in text
    assert "groups" not in student
    assert "maxGroups" not in student
