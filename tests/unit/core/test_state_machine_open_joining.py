"""T102：開放加入階段、空組免憑證與刪除組別的新規則（alignment 2026-11-23 後的決議）。

- 準備中拆成「準備中」與「開放加入」：老師按「開放加入」（須已匯入題目）後學生才能加入。
- 最後一台裝置主動離開且從未提交：釋放組號；已有提交則保留組別與憑證
  （2026-11-24 修訂）。
- 老師在開放加入或結果階段可刪除從未提交的組別（即使還有裝置）；搶答中禁止刪除。
"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import (
    Anonymous,
    CancelActivity,
    DeleteGroup,
    Device,
    EndActivity,
    JoinGroup,
    LeaveGroup,
    MarkGroupSubmitted,
    OpenJoining,
    OpenRound,
    ReplaceQuestions,
    System,
    Teacher,
)
from lecture_quiz.core.activity.models import Stage, freeze
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    describe_rejection,
)
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import (
    NOW,
    OTHER_TEACHER_HASH,
    TEACHER,
    new_activity,
    with_questions,
)

apply = ActivityStateMachine.apply
X, Y = "1" * 64, "2" * 64


def _join(activity, device, number, credential=None, new_cred="AAAAAA"):
    return apply(
        activity,
        JoinGroup(Anonymous(), number, credential),
        NOW,
        IssuedSecrets(device_token_hash=device, group_credential=new_cred),
    )


def joining_activity(*numbers):
    """已匯入題目、已開放加入，並建立指定組號的活動（每組一台裝置）。"""
    activity = apply(with_questions(new_activity()), OpenJoining(TEACHER), NOW).activity
    for i, number in enumerate(numbers):
        t = _join(activity, f"{i + 1}" * 64, number, new_cred=f"CRED{number:02d}")
        assert t.ok, t
        activity = t.activity
    return activity


# ── 開放加入 ─────────────────────────────────────────


def test_open_joining_moves_prepared_activity_to_joining():
    """Scenario: US8-AS1

    已匯入題目的活動，老師按「開放加入」後進入「開放加入」，版本加一。
    """
    activity = with_questions(new_activity())
    t = apply(activity, OpenJoining(TEACHER), NOW)
    assert t.ok and t.changed
    assert t.activity.stage is Stage.JOINING
    assert t.activity.version == activity.version + 1
    assert Stage.JOINING.label == "開放加入"


def test_open_joining_requires_imported_questions():
    """Scenario: US8-AS2

    還沒有成功匯入題目時開放加入被拒（NO_QUESTIONS），階段不變。
    """
    activity = new_activity()
    t = apply(activity, OpenJoining(TEACHER), NOW)
    assert t.rejection is RejectionReason.NO_QUESTIONS
    assert t.activity == activity


@pytest.mark.parametrize("actor", [Device(X), Teacher(OTHER_TEACHER_HASH), Anonymous()])
def test_open_joining_is_teacher_only(actor):
    """Scenario: US8-AS3

    學生、別的活動的老師與匿名請求都不能開放加入。
    """
    activity = with_questions(new_activity())
    t = apply(activity, OpenJoining(actor), NOW)
    assert t.rejection is RejectionReason.NOT_TEACHER
    assert t.activity == activity


@pytest.mark.parametrize(
    "stage",
    [Stage.JOINING, Stage.ROUND_OPEN, Stage.RESULT_PENDING, Stage.RESULT_FINAL],
)
def test_open_joining_only_from_preparing(stage):
    """Scenario: US8-AS3

    已經開放加入或更後面的階段，再開放加入被拒（STAGE_NOT_ALLOWED），階段不變。
    """
    activity = dataclasses.replace(with_questions(new_activity()), stage=stage)
    t = apply(activity, OpenJoining(TEACHER), NOW)
    assert t.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert t.activity == activity


def test_join_before_joining_is_open_is_rejected():
    """Scenario: US8-AS4

    準備中學生加入被拒（JOIN_NOT_OPEN），訊息說明老師還沒開放加入，不建立組別。
    """
    activity = with_questions(new_activity())
    command = JoinGroup(Anonymous(), 1, None)
    t = apply(
        activity, command, NOW, IssuedSecrets(device_token_hash=X, group_credential="A")
    )
    assert t.rejection is RejectionReason.JOIN_NOT_OPEN
    assert t.activity == activity
    assert t.rejection.http_status == 409
    message = describe_rejection(t.rejection, activity.stage, command, activity)
    assert "還沒開放加入" in message


def test_join_allowed_once_joining_is_open():
    """Scenario: US8-AS5

    開放加入後，新組號可以加入，階段維持「開放加入」。
    """
    activity = joining_activity(1)
    assert activity.stage is Stage.JOINING
    assert set(activity.groups) == {1}


def test_open_round_requires_joining_stage():
    """Scenario: US8-AS6

    準備中直接開輪被拒（STAGE_NOT_ALLOWED）；開放加入後才能開輪。
    """
    prepared = with_questions(new_activity())
    t = apply(prepared, OpenRound(TEACHER), NOW)
    assert t.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert "開放加入" in describe_rejection(
        t.rejection, prepared.stage, OpenRound(TEACHER), prepared
    )
    t = apply(joining_activity(), OpenRound(TEACHER), NOW)
    assert t.ok and t.activity.stage is Stage.ROUND_OPEN


@pytest.mark.parametrize("stage", [Stage.PREPARING, Stage.JOINING])
def test_cancel_and_replace_questions_allowed_before_first_round(stage):
    """Scenario: US8-AS7

    開輪前（準備中、開放加入）都可以重新匯入題目與取消活動。
    """
    activity = dataclasses.replace(with_questions(new_activity()), stage=stage)
    t = apply(activity, ReplaceQuestions(TEACHER, (5, 6)), NOW)
    assert t.ok and t.activity.question_numbers == (5, 6)
    t = apply(activity, CancelActivity(TEACHER), NOW)
    assert t.ok and t.activity.stage is Stage.CANCELLED


def test_end_activity_before_first_round_says_cancel_instead():
    """Scenario: US8-AS7

    準備中與開放加入只能取消活動，不能結束活動。
    """
    for stage in (Stage.PREPARING, Stage.JOINING):
        activity = dataclasses.replace(new_activity(), stage=stage)
        t = apply(activity, EndActivity(TEACHER), NOW)
        assert t.rejection is RejectionReason.STAGE_NOT_ALLOWED
        assert "只能取消活動" in describe_rejection(
            t.rejection, stage, EndActivity(TEACHER), activity
        )


# ── 最後一台裝置離開與重新加入（alignment 2026-11-24 修訂「空組免憑證」）──


def _submitted(activity, number):
    """讓指定組別有提交紀錄（搶答中標記），再回到結果未定案。"""
    opened = dataclasses.replace(activity, stage=Stage.ROUND_OPEN)
    marked = apply(opened, MarkGroupSubmitted(System(), number), NOW).activity
    return dataclasses.replace(marked, stage=Stage.RESULT_PENDING)


def test_last_device_leaving_unsubmitted_group_releases_number():
    """Scenario: US2-AS10

    最後一台裝置主動離開、該組從未提交：釋放組號，舊憑證失效；下一位不需憑證，
    直接建立同組號並取得新憑證。
    """
    activity = joining_activity(3)
    t = apply(activity, LeaveGroup(Device(X)), NOW)
    assert t.ok and t.changed
    assert 3 not in t.activity.groups
    rejoined = _join(t.activity, Y, 3, new_cred="NEW003")
    assert rejoined.ok
    assert rejoined.activity.groups[3].join_credential == "NEW003"
    late = _join(rejoined.activity, "3" * 64, 3, "CRED03")
    assert late.rejection is RejectionReason.BAD_CREDENTIAL


def test_group_with_submissions_keeps_credential_after_all_devices_leave():
    """Scenario: US2-AS10

    已有提交紀錄的組，所有裝置都離開後仍保留組別、憑證、提交與成功次數；
    重新加入必須附原憑證。
    """
    activity = _submitted(joining_activity(3), 3)
    groups = dict(activity.groups)
    groups[3] = dataclasses.replace(groups[3], success_count=1)
    activity = dataclasses.replace(activity, groups=groups)
    original = activity.groups[3]
    left = apply(activity, LeaveGroup(Device(X)), NOW).activity
    assert not left.devices
    assert left.groups[3] == original
    for credential in (None, "WRONG1"):
        t = _join(left, Y, 3, credential)
        assert t.rejection is RejectionReason.BAD_CREDENTIAL
        assert t.activity == left
    message = describe_rejection(
        RejectionReason.BAD_CREDENTIAL,
        left.stage,
        JoinGroup(Anonymous(), 3, None),
        left,
    )
    assert "老師" in message
    t = _join(left, Y, 3, "cred03")
    assert t.ok
    assert t.activity.groups[3] == original
    assert t.activity.devices[Y].group_number == 3


def test_leaving_with_other_devices_keeps_group_and_credential():
    """Scenario: US2-AS10

    還有其他裝置留在組內：保留原組與憑證，新裝置仍須提供憑證。
    """
    activity = _join(joining_activity(3), Y, 3, "CRED03").activity
    left = apply(activity, LeaveGroup(Device(X)), NOW).activity
    assert left.groups[3] == activity.groups[3]
    newcomer = "3" * 64
    assert _join(left, newcomer, 3).rejection is RejectionReason.BAD_CREDENTIAL
    assert _join(left, newcomer, 3, "CRED03").ok


def test_unsubmitted_group_without_devices_is_recreated_on_join():
    """防禦：從未提交且沒有裝置的組別（不經離開產生的狀態）也視為已釋放。"""
    activity = joining_activity(3)
    empty = dataclasses.replace(activity, devices=freeze({}))
    t = _join(empty, Y, 3, "CRED03", new_cred="NEW003")
    assert t.ok
    assert t.activity.groups[3].join_credential == "NEW003"


def test_group_with_a_device_still_requires_credential():
    """Scenario: US2-AS4

    組別只要還有一台裝置，加入就必須附正確憑證。
    """
    activity = joining_activity(3)
    t = _join(activity, Y, 3)
    assert t.rejection is RejectionReason.BAD_CREDENTIAL
    assert t.activity == activity
    assert _join(activity, Y, 3, "CRED03").ok


# ── 刪除組別 ─────────────────────────────────────────


@pytest.mark.parametrize(
    "stage", [Stage.JOINING, Stage.RESULT_PENDING, Stage.RESULT_FINAL]
)
def test_delete_group_with_devices_and_no_submissions(stage):
    """Scenario: US7-AS5

    開放加入或結果階段，老師可刪除從未提交的組別，即使還有裝置：
    組別與其所有裝置身分一併解除。
    """
    activity = dataclasses.replace(joining_activity(1, 2), stage=stage)
    t = apply(activity, DeleteGroup(TEACHER, 1), NOW)
    assert t.ok and t.changed
    assert set(t.activity.groups) == {2}
    assert all(d.group_number == 2 for d in t.activity.devices.values())


def test_delete_group_is_rejected_during_round():
    """Scenario: US7-AS7

    搶答中禁止刪除組別（GROUP_DELETE_DURING_ROUND），資料不變。
    """
    activity = dataclasses.replace(joining_activity(1), stage=Stage.ROUND_OPEN)
    command = DeleteGroup(TEACHER, 1)
    t = apply(activity, command, NOW)
    assert t.rejection is RejectionReason.GROUP_DELETE_DURING_ROUND
    assert t.rejection.http_status == 409
    assert t.activity == activity
    message = describe_rejection(t.rejection, activity.stage, command, activity)
    assert "搶答進行中不能刪除組別" in message


def test_deleted_group_number_can_be_recreated_with_a_new_credential():
    """Scenario: US7-AS8

    刪除後同一組號可以重新建立，取得新憑證；舊憑證不再有效。
    """
    activity = joining_activity(1)
    old = activity.groups[1].join_credential
    activity = apply(activity, DeleteGroup(TEACHER, 1), NOW).activity
    assert not activity.groups and not activity.devices
    t = _join(activity, Y, 1, new_cred="NEWCRD")
    assert t.ok
    assert t.activity.groups[1].join_credential == "NEWCRD" != old
    # 舊憑證對重新建立的組別無效
    t2 = _join(t.activity, "3" * 64, 1, old)
    assert t2.rejection is RejectionReason.BAD_CREDENTIAL


def test_delete_group_with_submissions_is_still_rejected():
    """Scenario: US7-AS6

    已有提交紀錄的組別不能刪除，資料不變。
    """
    activity = dataclasses.replace(joining_activity(1), stage=Stage.RESULT_FINAL)
    group = dataclasses.replace(activity.groups[1], has_submissions=True)
    activity = dataclasses.replace(activity, groups={1: group})
    t = apply(activity, DeleteGroup(TEACHER, 1), NOW)
    assert t.rejection is RejectionReason.GROUP_HAS_SUBMISSIONS
    assert t.activity == activity


def test_leave_group_stages_follow_joining():
    """Scenario: US7-AS1

    離開本組在開放加入與結果階段允許，搶答中拒絕。
    """
    for stage, ok in [
        (Stage.JOINING, True),
        (Stage.RESULT_PENDING, True),
        (Stage.RESULT_FINAL, True),
        (Stage.ROUND_OPEN, False),
    ]:
        activity = dataclasses.replace(joining_activity(1), stage=stage)
        t = apply(activity, LeaveGroup(Device("1" * 64)), NOW)
        assert t.ok is ok, stage


def test_system_actor_cannot_open_joining():
    """Scenario: US8-AS3

    系統（倒數排程）不能代替老師開放加入。
    """
    activity = with_questions(new_activity())
    t = apply(activity, OpenJoining(System()), NOW)
    assert t.rejection is RejectionReason.NOT_TEACHER
