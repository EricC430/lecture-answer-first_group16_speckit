"""T031：組別加入（US2）。"""

import dataclasses

import pytest

from lecture_quiz.core.activity.commands import Anonymous, Device, JoinGroup
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    describe_rejection,
)
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from tests.unit.core.helpers import NOW, new_activity

apply = ActivityStateMachine.apply
CRED = "Q8MZ3R"


def issued(device: str, credential: str = CRED) -> IssuedSecrets:
    return IssuedSecrets(device_token_hash=device * 64, group_credential=credential)


def joined(number_raw: object = 3):
    activity = new_activity()
    t = apply(activity, JoinGroup(Anonymous(), number_raw, None), NOW, issued("1"))
    assert t.ok and t.changed, t
    return t.activity


def test_new_group_number_creates_group_and_device():
    """Scenario: US2-AS1

    組號「 ０３ 」建立第 3 組，裝置取得第 3 組身分，憑證來自服務層。
    """
    activity = joined(" ０３ ")
    assert set(activity.groups) == {3}
    group = activity.groups[3]
    assert group.number == 3
    assert group.join_credential == CRED
    assert group.success_count == 0
    assert activity.devices["1" * 64].group_number == 3
    assert activity.version == 2


def test_existing_group_with_correct_credential_adds_device():
    """Scenario: US2-AS2

    既有組號加上正確憑證（大小寫與首尾空白不影響），只新增裝置、不新增組。
    """
    activity = joined()
    t = apply(
        activity,
        JoinGroup(Anonymous(), 3, " q8mz3r "),
        NOW,
        issued("2", "ZZZZZZ"),
    )
    assert t.ok and t.changed
    assert set(t.activity.groups) == {3}
    assert t.activity.groups[3].join_credential == CRED
    assert t.activity.devices["2" * 64].group_number == 3


@pytest.mark.parametrize("credential", [None, "", "WRONG1", "Q8MZ3"])
def test_existing_group_without_or_wrong_credential_rejected(credential):
    """Scenario: US2-AS4

    既有組號不附憑證或憑證錯誤時拒絕，活動不變，訊息含組號、不含憑證。
    """
    activity = joined()
    command = JoinGroup(Anonymous(), 3, credential)
    t = apply(activity, command, NOW, issued("2"))
    assert t.rejection is RejectionReason.BAD_CREDENTIAL
    assert t.activity == activity
    message = describe_rejection(t.rejection, activity.stage, command, activity)
    assert "第 3 組" in message
    assert "向同組同學查看本組加入憑證" in message
    assert CRED not in message


@pytest.mark.parametrize("raw", ["", "0", 7, "三", 2.5, None])
def test_invalid_group_number_rejected(raw):
    """Scenario: US2-AS5

    組號格式錯誤或超出 1～N 時拒絕，訊息帶入 N，活動不變。
    """
    activity = new_activity()
    command = JoinGroup(Anonymous(), raw, None)
    t = apply(activity, command, NOW, issued("1"))
    assert t.rejection is RejectionReason.INVALID_GROUP_NUMBER
    assert t.activity == activity
    assert (
        describe_rejection(t.rejection, activity.stage, command, activity)
        == "組號須為 1～6 的整數。"
    )


@pytest.mark.parametrize(
    ("stage", "word"), [(Stage.ENDED, "已結束"), (Stage.CANCELLED, "已取消")]
)
def test_terminal_stage_rejects_join(stage, word):
    """Scenario: US2-AS6

    已結束或已取消時拒絕加入，訊息依階段說明。
    """
    activity = dataclasses.replace(new_activity(), stage=stage)
    command = JoinGroup(Anonymous(), 1, None)
    t = apply(activity, command, NOW, issued("1"))
    assert t.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert describe_rejection(t.rejection, stage, command) == f"活動{word}，無法加入。"


def test_join_during_round_open_keeps_stage():
    """Scenario: US2-AS7

    搶答中加入新組，成功次數為零，階段不變。
    """
    activity = dataclasses.replace(new_activity(), stage=Stage.ROUND_OPEN)
    t = apply(activity, JoinGroup(Anonymous(), 2, None), NOW, issued("1"))
    assert t.ok
    assert t.activity.stage is Stage.ROUND_OPEN
    assert t.activity.groups[2].success_count == 0


def test_device_already_in_group_cannot_join_again():
    """Scenario: US2-AS9

    已是某一組成員的裝置再加入時拒絕，訊息提示先離開本組，活動不變。
    """
    activity = joined()
    command = JoinGroup(Device("1" * 64), 4, None)
    t = apply(activity, command, NOW, issued("1"))
    assert t.rejection is RejectionReason.ALREADY_IN_GROUP
    assert t.activity == activity
    assert (
        describe_rejection(t.rejection, activity.stage, command, activity)
        == "這台裝置已經在第 3 組，請先離開本組。"
    )
