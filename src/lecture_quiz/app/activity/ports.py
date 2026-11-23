"""服務層對外的介面（contracts/service-interfaces.md）。

- 服務層依賴的外部能力：`Clock`、`CountdownScheduler`、`SyncPublisher`（由外層實作）。
- 提供給 002 的 `ActivityGateway`；`ActivityService` 以結構型別實作它。
- 共通型別：`Requester`、`Outcome[T]`。
"""

from collections.abc import Awaitable, Callable
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
