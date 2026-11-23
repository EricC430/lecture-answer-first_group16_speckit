"""FR-027、FR-030：狀態版本只反映學生可見的變更（PR #15 第三次審查問題 2）。

- `version`／`changed_at`：只在學生也看得到的共同狀態改變時遞增
  （階段、輪次、題號、已成功題）。
- `revision`：任何變更都遞增，只出現在老師快照，供老師頁排序。
他組加入、離開、被刪除與第一次提交只改 `revision`，學生無法由版本跳動推知他組動態。
"""

from datetime import timedelta

from lecture_quiz.core.activity.commands import (
    Anonymous,
    CloseRound,
    DeleteGroup,
    Device,
    Finalize,
    JoinGroup,
    LeaveGroup,
    MarkGroupSubmitted,
    OpenRound,
    ReplaceQuestions,
    System,
)
from lecture_quiz.core.activity.results import IssuedSecrets
from lecture_quiz.core.activity.snapshot_view import SnapshotView
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, TEACHER, new_activity

apply = ActivityStateMachine.apply
LATER = NOW + timedelta(seconds=10)
X, Y = "1" * 64, "2" * 64


def _join(activity, device, number, at=NOW):
    t = apply(
        activity,
        JoinGroup(Anonymous(), number, None),
        at,
        IssuedSecrets(device_token_hash=device, group_credential="AAAAAA"),
    )
    assert t.ok and t.changed, t
    return t.activity


def test_new_activity_starts_at_version_and_revision_one():
    activity = new_activity()
    assert (activity.version, activity.revision) == (1, 1)


def test_group_changes_bump_only_revision():
    base = new_activity()
    joined = _join(base, X, 1, at=LATER)
    assert joined.version == base.version
    assert joined.changed_at == base.changed_at
    assert joined.revision == base.revision + 1

    second = _join(joined, Y, 2, at=LATER)
    left = apply(second, LeaveGroup(Device(Y)), LATER).activity
    assert left.version == base.version
    assert left.revision == second.revision + 1

    deleted = apply(left, DeleteGroup(TEACHER, 2), LATER).activity
    assert deleted.version == base.version
    assert deleted.revision == left.revision + 1


def test_first_submission_mark_bumps_only_revision():
    activity = apply(
        _join(new_activity(), X, 1), ReplaceQuestions(TEACHER, (1, 2)), NOW
    ).activity
    opened = apply(activity, OpenRound(TEACHER), NOW).activity
    marked = apply(opened, MarkGroupSubmitted(System(), 1), LATER)
    assert marked.changed
    assert marked.activity.version == opened.version
    assert marked.activity.changed_at == opened.changed_at
    assert marked.activity.revision == opened.revision + 1


def test_public_changes_bump_version_and_revision():
    activity = _join(new_activity(), X, 1)
    steps = [
        ReplaceQuestions(TEACHER, (1, 2)),
        OpenRound(TEACHER),
        CloseRound(TEACHER),
        Finalize(TEACHER),
    ]
    for command in steps:
        after = apply(activity, command, LATER).activity
        assert after.version == activity.version + 1, command
        assert after.revision == activity.revision + 1, command
        assert after.changed_at == LATER
        activity = after


def test_snapshots_carry_public_version_and_teacher_revision():
    activity = _join(_join(new_activity(), X, 1), Y, 2)
    teacher = SnapshotView.for_teacher(activity).to_json()
    student = SnapshotView.for_group(activity, 1).to_json()
    assert teacher["version"] == student["version"] == activity.version
    assert teacher["revision"] == activity.revision
    assert "revision" not in student
