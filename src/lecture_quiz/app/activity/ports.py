"""服務層對外的介面（contracts/service-interfaces.md）。

- 服務層依賴的外部能力：`Clock`、`CountdownScheduler`、`SyncPublisher`（由外層實作）。
- 提供給 002 的 `ActivityGateway`；`ActivityService` 以結構型別實作它。
- 共通型別：`Requester`、`Outcome[T]`。
- 給 003 的擴充點（003 研究 R2、R4）：`SubmissionWindow`、`HandlerStep`、
  `SubmissionHandler`、`SnapshotExtension` 與 `TeacherViewer`／`GroupViewer`。
"""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, Protocol, TypeVar

from lecture_quiz.core.activity.commands import Anonymous, Device, Teacher
from lecture_quiz.core.activity.models import Activity, Stage
from lecture_quiz.core.activity.results import RejectionReason

T = TypeVar("T")

Requester = Teacher | Device | Anonymous
"""服務層依 token 解析後的身分；只會是老師、裝置或匿名其中之一。"""

DeadlineCallback = Callable[[str, datetime], Awaitable[None]]
"""倒數到期時的回呼：`(活動代碼, 截止時間)`。"""

DisconnectReason = Literal["LEFT_GROUP", "GROUP_DELETED"]
"""裝置失去組別身分的原因（contracts/sync-websocket.md 的 `unauthorized.reason`）。"""


@dataclass(frozen=True)
class Outcome(Generic[T]):
    """服務方法的回傳值；業務錯誤不拋例外。

    Attributes:
        ok: 是否成功。
        value: 成功時的值。
        rejection: 失敗原因。
        message: 失敗時給使用者的中文訊息。
    """

    ok: bool
    value: T | None = None
    rejection: RejectionReason | None = None
    message: str = ""


class Clock(Protocol):
    """提供現在時間。"""

    def now(self) -> datetime:
        """回傳有時區資訊的現在時間。

        Returns:
            現在時間。
        """
        ...


class CountdownScheduler(Protocol):
    """倒數排程；到期時以截止時間呼叫已綁定的回呼。"""

    def set_callback(self, callback: DeadlineCallback) -> None:
        """綁定到期回呼（建立服務後設定一次）。

        Args:
            callback: 到期時呼叫的函式。
        """
        ...

    def schedule(self, code: str, deadline: datetime) -> None:
        """排程（同一活動已有排程時取代）。

        Args:
            code: 活動代碼。
            deadline: 截止時間。
        """
        ...

    def cancel(self, code: str) -> None:
        """取消該活動的排程；沒有排程時不做事。

        Args:
            code: 活動代碼。
        """
        ...


class SyncPublisher(Protocol):
    """把狀態變更推送到所有連線，各連線依角色裁切。"""

    async def publish(self, activity: Activity) -> None:
        """推送最新狀態。

        Args:
            activity: 變更後的活動。
        """
        ...

    async def disconnect_device(
        self, code: str, token_hash: str, reason: DisconnectReason
    ) -> None:
        """通知裝置已失去組別身分，並關閉它的所有連線。

        Args:
            code: 活動代碼。
            token_hash: 裝置 token 的雜湊。
            reason: 離開本組或組別被刪除。
        """
        ...


class ActivityGateway(Protocol):
    """提供給 002（Guided Notes 匯入）的介面。"""

    def stage(self, code: str) -> Stage | None:
        """目前階段；活動不存在時為 `None`。

        Args:
            code: 活動代碼。

        Returns:
            階段或 `None`。
        """
        ...

    def is_teacher(self, code: str, requester: Requester) -> bool:
        """`requester` 是否為該活動老師。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            是老師時為 True。
        """
        ...

    async def replace_questions(
        self, code: str, requester: Requester, question_numbers: tuple[int, ...]
    ) -> Outcome[int]:
        """以整份新題號取代舊的，只允許老師在準備中呼叫。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            question_numbers: 新題號。

        Returns:
            成功時 `value` 為新版本號；被拒時既有題目完全不變。
        """
        ...


@dataclass(frozen=True)
class SubmissionWindow:
    """`record_submission` 在活動鎖內組成、交給 003 判定的本輪資訊。

    Attributes:
        group_number: 依裝置 token 判定的組號（FR-012）。
        stage: 目前階段。
        round_number: 目前輪次編號；還沒有輪次時為 `None`。
        open_questions: 本輪開放題；不在搶答中時為空。
        deadline: 本輪截止時間；不在搶答中或沒有倒數時為 `None`。
        accepting: 搶答中，且沒有截止時間或 `now < deadline`。
    """

    group_number: int
    stage: Stage
    round_number: int | None
    open_questions: tuple[int, ...]
    deadline: datetime | None
    accepting: bool


@dataclass(frozen=True)
class HandlerStep(Generic[T]):
    """003 判定的結果：`accept` 要標記並保存；`no_change` 不保存也不推送。

    003 自己的拒絕也以 `no_change` 回傳，拒絕原因放在 `value` 裡，不經過 001 的
    `RejectionReason`。

    Attributes:
        kind: `accept` 或 `no_change`。
        value: 交回給呼叫端的值。
    """

    kind: Literal["accept", "no_change"]
    value: T

    @staticmethod
    def accept(value: T) -> "HandlerStep[T]":
        """要標記組別並保存的結果。

        Args:
            value: 交回給呼叫端的值。

        Returns:
            `kind == "accept"` 的結果。
        """
        return HandlerStep("accept", value)

    @staticmethod
    def no_change(value: T) -> "HandlerStep[T]":
        """不保存、不推送的結果（本組已送出或 003 的拒絕）。

        Args:
            value: 交回給呼叫端的值。

        Returns:
            `kind == "no_change"` 的結果。
        """
        return HandlerStep("no_change", value)


class SubmissionHandler(Protocol[T]):
    """003 交給 `record_submission` 的處理器；兩個方法都在活動鎖內被呼叫。"""

    def decide(self, window: SubmissionWindow, now: datetime) -> HandlerStep[T]:
        """判定這次提交；不得有副作用。

        Args:
            window: 本輪資訊。
            now: 鎖內取得的接收時間。

        Returns:
            判定結果。
        """
        ...

    def commit(self) -> None:
        """`RecordSubmission` 成功後保存提交（仍在鎖內）。"""
        ...


@dataclass(frozen=True)
class TeacherViewer:
    """以老師身分檢視快照。"""


@dataclass(frozen=True)
class GroupViewer:
    """以某一組的裝置身分檢視快照。

    Attributes:
        group_number: 組號。
    """

    group_number: int


Viewer = TeacherViewer | GroupViewer
"""快照的檢視者。"""


class SnapshotExtension(Protocol):
    """快照擴充：回傳要併入快照 `extra` 的欄位，可覆寫 001 的欄位。"""

    def __call__(self, activity: Activity, viewer: Viewer) -> Mapping[str, object]:
        """產生擴充欄位。

        Args:
            activity: 活動。
            viewer: 檢視者。

        Returns:
            要併入的欄位（已是 JSON 格式）。
        """
        ...
