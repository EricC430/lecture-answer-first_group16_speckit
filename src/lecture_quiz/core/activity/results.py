"""狀態機的輸出：轉移結果、拒絕原因與這次產生的秘密（data-model.md）。"""

from dataclasses import dataclass
from enum import StrEnum

from lecture_quiz.core.activity.commands import (
    CancelActivity,
    CloseRound,
    Command,
    DeleteGroup,
    EndActivity,
    Finalize,
    JoinGroup,
    OpenJoining,
    OpenRound,
    ReplaceQuestions,
)
from lecture_quiz.core.activity.models import Activity, Stage


class RejectionReason(StrEnum):
    """拒絕原因；每個值對應一個 HTTP 狀態碼與預設訊息。"""

    NOT_TEACHER = "NOT_TEACHER"
    STAGE_NOT_ALLOWED = "STAGE_NOT_ALLOWED"
    NO_QUESTIONS = "NO_QUESTIONS"
    INVALID_SELECTION = "INVALID_SELECTION"
    INVALID_COUNTDOWN = "INVALID_COUNTDOWN"
    INVALID_GROUP_NUMBER = "INVALID_GROUP_NUMBER"
    BAD_CREDENTIAL = "BAD_CREDENTIAL"
    ACTIVITY_GONE = "ACTIVITY_GONE"
    RULES_LOCKED = "RULES_LOCKED"
    NO_GROUP_SWITCH_DURING_ROUND = "NO_GROUP_SWITCH_DURING_ROUND"
    GROUP_HAS_SUBMISSIONS = "GROUP_HAS_SUBMISSIONS"
    INVALID_MAX_GROUPS = "INVALID_MAX_GROUPS"
    TEACHER_HAS_ACTIVE_ACTIVITY = "TEACHER_HAS_ACTIVE_ACTIVITY"
    ALREADY_IN_GROUP = "ALREADY_IN_GROUP"
    NOT_IN_GROUP = "NOT_IN_GROUP"
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    JOIN_NOT_OPEN = "JOIN_NOT_OPEN"
    GROUP_DELETE_DURING_ROUND = "GROUP_DELETE_DURING_ROUND"

    @property
    def http_status(self) -> int:
        """對應的 HTTP 狀態碼。"""
        return _HTTP_STATUS[self]

    @property
    def default_message(self) -> str:
        """預設的中文訊息。"""
        return _MESSAGES[self]


_HTTP_STATUS = {
    RejectionReason.NOT_TEACHER: 403,
    RejectionReason.STAGE_NOT_ALLOWED: 409,
    RejectionReason.NO_QUESTIONS: 409,
    RejectionReason.INVALID_SELECTION: 400,
    RejectionReason.INVALID_COUNTDOWN: 400,
    RejectionReason.INVALID_GROUP_NUMBER: 400,
    RejectionReason.BAD_CREDENTIAL: 403,
    RejectionReason.ACTIVITY_GONE: 410,
    RejectionReason.RULES_LOCKED: 409,
    RejectionReason.NO_GROUP_SWITCH_DURING_ROUND: 409,
    RejectionReason.GROUP_HAS_SUBMISSIONS: 409,
    RejectionReason.INVALID_MAX_GROUPS: 400,
    RejectionReason.TEACHER_HAS_ACTIVE_ACTIVITY: 409,
    RejectionReason.ALREADY_IN_GROUP: 409,
    RejectionReason.NOT_IN_GROUP: 403,
    RejectionReason.GROUP_NOT_FOUND: 404,
    RejectionReason.JOIN_NOT_OPEN: 409,
    RejectionReason.GROUP_DELETE_DURING_ROUND: 409,
}

_MESSAGES = {
    RejectionReason.NOT_TEACHER: "需要這個活動的老師身分才能操作。",
    RejectionReason.STAGE_NOT_ALLOWED: "目前的活動階段不能進行這個操作。",
    RejectionReason.NO_QUESTIONS: "請先成功匯入學習單，再開始搶答。",
    RejectionReason.INVALID_SELECTION: "請至少選擇一題尚未有人答對的題目。",
    RejectionReason.INVALID_COUNTDOWN: "倒數秒數須為 1～3600 的整數。",
    RejectionReason.INVALID_GROUP_NUMBER: "組號須為 1～N 的整數。",
    RejectionReason.BAD_CREDENTIAL: (
        "此組已有同學加入；若你是這一組的成員，請向同組同學查看本組加入憑證，"
        "否則請確認組號。"
    ),
    RejectionReason.ACTIVITY_GONE: "活動已失效，請重新建立或加入活動。",
    RejectionReason.RULES_LOCKED: "本輪進行中，題目、模式與截止時間不能修改。",
    RejectionReason.NO_GROUP_SWITCH_DURING_ROUND: (
        "搶答進行中不能換組，請在本輪關閉後再操作，這段期間可以用同組同學的裝置作答。"
    ),
    RejectionReason.GROUP_HAS_SUBMISSIONS: "此組已有作答紀錄，不能刪除。",
    RejectionReason.INVALID_MAX_GROUPS: "組數上限須為 1～99 的整數。",
    RejectionReason.TEACHER_HAS_ACTIVE_ACTIVITY: (
        "你已有一個進行中的活動，請先結束或取消它。"
    ),
    RejectionReason.ALREADY_IN_GROUP: "這個瀏覽器已經在某一組，請先離開本組。",
    RejectionReason.NOT_IN_GROUP: "這台裝置目前沒有加入任何組別。",
    RejectionReason.GROUP_NOT_FOUND: "找不到這個組別。",
    RejectionReason.JOIN_NOT_OPEN: "老師還沒開放加入，請稍後再試。",
    RejectionReason.GROUP_DELETE_DURING_ROUND: (
        "搶答進行中不能刪除組別，請在本輪關閉後再操作。"
    ),
}


@dataclass(frozen=True)
class IssuedSecrets:
    """由服務層產生後傳入核心的新秘密；核心本身不產生亂數。

    Attributes:
        activity_code: 新活動代碼（建立活動）。
        teacher_token_hash: 新老師 token 的雜湊（建立活動）。
        device_token_hash: 新裝置 token 的雜湊（加入組別）。
        group_credential: 新組別加入憑證（US2 使用）。
    """

    activity_code: str | None = None
    teacher_token_hash: str | None = None
    device_token_hash: str | None = None
    group_credential: str | None = None


@dataclass(frozen=True)
class Transition:
    """一次 `apply` 的結果。

    Attributes:
        ok: 是否成功。
        activity: 成功時為新狀態；失敗或無變化時為原狀態。
        changed: 是否真的改變（決定版本是否加 1、是否推送）。
        rejection: 失敗原因。
        issued: 這次操作使用的新秘密。
    """

    ok: bool
    activity: Activity | None
    changed: bool = False
    rejection: RejectionReason | None = None
    issued: IssuedSecrets | None = None


def describe_rejection(
    reason: RejectionReason,
    stage: Stage | None,
    command: Command | None,
    activity: Activity | None = None,
) -> str:
    """產生可修正的中文拒絕訊息。

    `STAGE_NOT_ALLOWED` 依「階段 × 操作」產生；組別相關的訊息依活動帶入組號或組數上限。

    Args:
        reason: 拒絕原因。
        stage: 被拒絕時的活動階段。
        command: 被拒絕的操作。
        activity: 被拒絕時的活動（用來帶入組號、組數上限）。

    Returns:
        中文訊息，不含任何 token 或憑證。
    """
    group_message = _describe_group_rejection(reason, command, activity)
    if group_message is not None:
        return group_message
    if reason is not RejectionReason.STAGE_NOT_ALLOWED or stage is None:
        return reason.default_message
    if stage.is_terminal:
        if isinstance(command, JoinGroup):
            return f"活動{stage.label}，無法加入。"
        return f"活動{stage.label}，無法再進行這個操作。"
    if isinstance(command, OpenRound) and stage is Stage.RESULT_PENDING:
        return "目前是「結果未定案」，請先確認定案本輪結果。"
    if isinstance(command, OpenRound) and stage is Stage.PREPARING:
        return "請先按「開放加入」，再開始搶答。"
    if isinstance(command, OpenJoining):
        if stage is Stage.JOINING:
            return "已經開放加入了。"
        return f"目前是「{stage.label}」，不能再開放加入。"
    if isinstance(command, EndActivity):
        if stage in (Stage.PREPARING, Stage.JOINING):
            return f"{stage.label}只能取消活動。"
        return f"目前是「{stage.label}」，請先關輪並確認定案，再結束活動。"
    if isinstance(command, CancelActivity):
        return "只有準備中與開放加入可以取消活動；已開始搶答的活動請在定案後結束活動。"
    if isinstance(command, CloseRound):
        return "目前沒有進行中的輪次。"
    if isinstance(command, Finalize):
        if stage is Stage.ROUND_OPEN:
            return "請先關輪，再確認定案。"
        return "目前沒有待定案的輪次。"
    if isinstance(command, ReplaceQuestions):
        return "只有準備中與開放加入可以匯入學習單。"
    return f"目前是「{stage.label}」，不能進行這個操作。"


def _describe_group_rejection(
    reason: RejectionReason, command: Command | None, activity: Activity | None
) -> str | None:
    """組別相關拒絕的訊息（帶入組號或 N）；不屬於這類時回傳 `None`。"""
    if activity is None:
        return None
    if reason is RejectionReason.INVALID_GROUP_NUMBER:
        return f"組號須為 1～{activity.max_groups} 的整數。"
    if reason is RejectionReason.BAD_CREDENTIAL and isinstance(command, JoinGroup):
        number = _parse_number(command.number_raw, activity.max_groups)
        if number is not None:
            return (
                f"第 {number} 組已有同學加入或已有作答紀錄；若你是這一組的成員，"
                "請向同組同學查看本組加入憑證（沒有同學在線時請老師查看），"
                "否則請確認組號。"
            )
    if reason is RejectionReason.GROUP_NOT_FOUND and isinstance(command, DeleteGroup):
        number = _parse_number(command.number_raw, activity.max_groups)
        if number is not None:
            return f"找不到第 {number} 組。"
    if reason is RejectionReason.ALREADY_IN_GROUP and isinstance(command, JoinGroup):
        # 007：先用指令帶的瀏覽器雜湊（同時加入落敗者的請求者仍是 Anonymous）
        token_hash = command.device_token_hash or getattr(
            command.actor, "token_hash", None
        )
        device = activity.devices.get(token_hash) if token_hash else None
        if device is not None:
            return f"這個瀏覽器已是第 {device.group_number} 組成員，請先離開本組。"
    return None


def _parse_number(raw: object, max_groups: int) -> int | None:
    from lecture_quiz.core.activity.input_rules import InputRules, InvalidInputError

    try:
        return InputRules.normalize_group_number(raw, max_groups)
    except InvalidInputError:
        return None
