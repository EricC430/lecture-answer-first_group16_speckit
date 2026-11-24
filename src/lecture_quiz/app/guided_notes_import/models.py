"""002 應用層的資料型別（data-model.md「應用層」）。

服務不拋業務錯誤：失敗以 `ImportRejection` 回傳（沿用 001 契約的風格）。
這裡完全看不到 Google 的型別。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from lecture_quiz.core.guided_notes_import.models import (
    Blank,
    StructureSnapshot,
    ValidationIssue,
)

T = TypeVar("T")


class ImportRejection(StrEnum):
    """業務失敗的代碼（research R8；訊息在 `messages.py`）。"""

    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTH_DENIED = "AUTH_DENIED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_A_SPREADSHEET = "NOT_A_SPREADSHEET"
    SHEET_NOT_FOUND = "SHEET_NOT_FOUND"
    SOURCE_NOT_SELECTED = "SOURCE_NOT_SELECTED"
    READ_FAILED = "READ_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    ACTIVITY_NOT_FOUND = "ACTIVITY_NOT_FOUND"
    NOT_TEACHER = "NOT_TEACHER"
    ROUND_STARTED = "ROUND_STARTED"
    ACTIVITY_CANCELLED = "ACTIVITY_CANCELLED"
    STAGE_NOT_PREPARING = "STAGE_NOT_PREPARING"
    GATEWAY_REJECTED = "GATEWAY_REJECTED"
    GOOGLE_NOT_CONFIGURED = "GOOGLE_NOT_CONFIGURED"
    INVALID_REQUEST = "INVALID_REQUEST"


@dataclass(frozen=True)
class Result(Generic[T]):
    """與 001 `Outcome` 同形的結果：成功帶值，失敗帶 `ImportRejection`。

    Attributes:
        ok: 是否成功。
        value: 成功時的值。
        rejection: 失敗原因。
    """

    ok: bool
    value: T | None = None
    rejection: ImportRejection | None = None

    @staticmethod
    def success(value: T) -> "Result[T]":
        """建立成功結果。"""
        return Result(ok=True, value=value)

    @staticmethod
    def failure(rejection: ImportRejection) -> "Result[T]":
        """建立失敗結果。"""
        return Result(ok=False, rejection=rejection)


@dataclass(frozen=True)
class SourceRef:
    """來源識別：一份試算表中的一張工作表（FR-002）。

    Attributes:
        spreadsheet_id: 試算表識別。
        sheet_id: 工作表識別。
    """

    spreadsheet_id: str
    sheet_id: int


@dataclass(frozen=True)
class SheetInfo:
    """試算表中的一張工作表。

    Attributes:
        sheet_id: 工作表識別。
        title: 工作表標題。
        hidden: 是否隱藏；隱藏的不列入選擇也不計張數（2026-11-23 澄清）。
    """

    sheet_id: int
    title: str
    hidden: bool = False


@dataclass(frozen=True)
class SpreadsheetInfo:
    """檢視一份試算表的結果。

    Attributes:
        spreadsheet_id: 試算表識別。
        title: 試算表標題。
        sheets: 可見的工作表（服務會濾除隱藏者）。
        auto_select_sheet_id: 可見工作表恰好一張時為其識別，否則為 `None`。
    """

    spreadsheet_id: str
    title: str
    sheets: tuple[SheetInfo, ...]
    auto_select_sheet_id: int | None = None


@dataclass(frozen=True)
class SourceSelection:
    """老師選定的來源；取消選檔不寫入。

    Attributes:
        source: 來源識別。
        sheet_title: 當時的工作表標題。
    """

    source: SourceRef
    sheet_title: str


@dataclass(frozen=True)
class ImportRecord:
    """最後一次成功匯入的結果；每次成功整份取代（FR-019、FR-024）。

    Attributes:
        source: 來源識別。
        sheet_title: 當時的工作表標題。
        blanks: 每個空格的來源映射。
        structure: 匯入時結構。
        question_numbers: 題號清單。
        version: 這次匯入時 001 回傳的新版本號（頁面重新整理後恢復預覽用）。
    """

    source: SourceRef
    sheet_title: str
    blanks: tuple[Blank, ...]
    structure: StructureSnapshot
    question_numbers: tuple[int, ...]
    version: int = 0


@dataclass(frozen=True)
class ImportPreview:
    """匯入預覽：題組只算一題，總格數累計子空格（FR-017、FR-018）。

    Attributes:
        question_numbers: 題號清單。
        blanks_per_question: 各題空格數。
        total_questions: 總題數。
        total_blanks: 總空格數。
    """

    question_numbers: tuple[int, ...]
    blanks_per_question: Mapping[int, int]
    total_questions: int
    total_blanks: int


@dataclass(frozen=True)
class ImportOutcome:
    """匯入的結果。

    Attributes:
        ok: 是否成功。
        preview: 成功時的預覽。
        issues: 驗證失敗時的問題清單。
        rejection: 失敗原因。
        version: 成功時 001 回傳的新版本號。
        sheet_title: 成功時的工作表標題。
    """

    ok: bool
    preview: ImportPreview | None = None
    issues: tuple[ValidationIssue, ...] = ()
    rejection: ImportRejection | None = None
    version: int | None = None
    sheet_title: str = ""


@dataclass(frozen=True)
class PickerConfig:
    """Picker 用的短效設定（只含 `drive.file` 範圍的 token）。

    Attributes:
        access_token: 短效 access token。
        api_key: Picker 用的 API 金鑰。
        app_id: Google Cloud 專案編號。
    """

    access_token: str
    api_key: str
    app_id: str

    def __repr__(self) -> str:
        """不顯示 token 與金鑰，避免被寫進日誌。"""
        return "PickerConfig(<redacted>)"


@dataclass(frozen=True)
class CallbackResult:
    """授權回呼的結果。

    Attributes:
        code: 活動代碼；`state` 無效時為 `None`。
        status: `ok`、`denied` 或 `error`。
    """

    code: str | None
    status: str
