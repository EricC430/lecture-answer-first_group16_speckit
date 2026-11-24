"""005 應用層的資料型別（data-model.md「應用層」）。

服務不拋業務錯誤：失敗時 `Result.ok=False`、`rejection` 為 `ExportRejection`
（訊息與 HTTP 狀態碼在 `messages.py`）。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

from lecture_quiz.core.result_export.models import (
    CellCheck,
    ResultSnapshot,
    StructureCheck,
    StructureDifference,
    WritePlanItem,
)

T = TypeVar("T")


class AttemptKind(StrEnum):
    """第一次確認寫回，或重試。"""

    WRITE = "WRITE"
    RETRY = "RETRY"


class AttemptStatus(StrEnum):
    """寫回嘗試的狀態；`IN_PROGRESS` 只是暫時狀態，不屬於 spec 的三種結果。"""

    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


class AttemptReason(StrEnum):
    """失敗或待確認的原因類別（只有代碼，說明在 `messages.py`）。"""

    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    REJECTED = "REJECTED"
    RATE_LIMITED = "RATE_LIMITED"
    STRUCTURE_CHANGED = "STRUCTURE_CHANGED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    READ_FAILED = "READ_FAILED"
    NOT_WRITTEN = "NOT_WRITTEN"
    UNKNOWN = "UNKNOWN"


class ExportRejection(StrEnum):
    """業務失敗的代碼（http-api.md 的錯誤表）。"""

    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_TEACHER = "NOT_TEACHER"
    ACTIVITY_NOT_FOUND = "ACTIVITY_NOT_FOUND"
    ACTIVITY_CANCELLED = "ACTIVITY_CANCELLED"
    NO_RESULTS = "NO_RESULTS"
    STALE_SNAPSHOT = "STALE_SNAPSHOT"
    ATTEMPT_NOT_FOUND = "ATTEMPT_NOT_FOUND"
    NOT_LATEST_ATTEMPT = "NOT_LATEST_ATTEMPT"
    WRITE_IN_PROGRESS = "WRITE_IN_PROGRESS"
    NO_IMPORT_RECORD = "NO_IMPORT_RECORD"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    READ_FAILED = "READ_FAILED"
    GOOGLE_NOT_CONFIGURED = "GOOGLE_NOT_CONFIGURED"


@dataclass(frozen=True)
class Result(Generic[T]):
    """與 001 `Outcome`、002 `Result` 同形的結果。

    Attributes:
        ok: 是否成功。
        value: 成功時的值。
        rejection: 失敗原因。
    """

    ok: bool
    value: T | None = None
    rejection: ExportRejection | None = None

    @staticmethod
    def success(value: T) -> "Result[T]":
        """建立成功結果。"""
        return Result(ok=True, value=value)

    @staticmethod
    def failure(rejection: ExportRejection) -> "Result[T]":
        """建立失敗結果。"""
        return Result(ok=False, rejection=rejection)


@dataclass(frozen=True)
class WriteAttempt:
    """一次寫回（或重試、核對後更新）的紀錄。

    Attributes:
        attempt_id: 活動內從 1 遞增的編號。
        kind: 第一次寫回或重試。
        snapshot_id: 所依據的成果快照識別。
        items: 這次嘗試對應的快照內容（重試與核對都用它）。
        status: 狀態。
        reason: 失敗或待確認的原因類別。
        started_at: 開始時間（由 `Clock` 取得）。
        differences: 結構差異（結構不符時）。
        cell_checks: 核對時逐格的結果。
        finished_at: 結束時間；進行中為 `None`。
        confirmed_cells: 已確認寫入的格數。
        not_written_cells: 確認未寫入的格數。
        pending_cells: 待確認的格數。
        already_in_progress: 回覆的是已在進行中的嘗試（不是新開始的；不存入存放區）。
    """

    attempt_id: int
    kind: AttemptKind
    snapshot_id: str
    items: tuple[WritePlanItem, ...]
    status: AttemptStatus
    reason: AttemptReason | None
    started_at: datetime
    differences: tuple[StructureDifference, ...] = ()
    cell_checks: tuple[CellCheck, ...] = ()
    finished_at: datetime | None = None
    confirmed_cells: int = 0
    not_written_cells: int = 0
    pending_cells: int = 0
    already_in_progress: bool = False

    @property
    def total_cells(self) -> int:
        """快照涵蓋的子空格數。"""
        return len(self.items)


@dataclass(frozen=True)
class PreviewView:
    """預覽。

    Attributes:
        snapshot: 成果快照。
        structure: 結構比對結論。
        sheet_title: 目前的工作表標題（讀不到時為匯入時的標題）。
    """

    snapshot: ResultSnapshot
    structure: StructureCheck
    sheet_title: str

    @property
    def can_confirm(self) -> bool:
        """結構相符且至少有一個目標格時才可確認。"""
        return self.structure.ok and bool(self.snapshot.items)
