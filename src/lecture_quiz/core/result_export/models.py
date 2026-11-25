"""005 核心的不可變資料型別（data-model.md「核心層」）。

座標沿用 002 的 `CellRef`（0 起算的列, 欄）。核心不匯入 app 型別：001～004 的資料由
應用層轉成這裡的輸入型別。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from lecture_quiz.core.guided_notes_import.models import CellRef

CURRENT_DISPLAY_LIMIT = 40
"""覆寫影響中顯示的原內容最多保留的字元數。"""


class CellKind(StrEnum):
    """目標格目前內容的種類。"""

    EMPTY = "EMPTY"
    TEXT = "TEXT"
    OTHER = "OTHER"


class OverwriteImpact(StrEnum):
    """寫入對目標格原有內容的影響。"""

    EMPTY = "EMPTY"
    REPLACE = "REPLACE"
    SAME = "SAME"


class DiffKind(StrEnum):
    """來源結構差異的類別（research R5）。"""

    IDENTITY = "IDENTITY"
    UNRECOGNIZED = "UNRECOGNIZED"
    HEADER_POSITION = "HEADER_POSITION"
    QUESTION_NUMBER = "QUESTION_NUMBER"
    SUB_BLANK = "SUB_BLANK"
    ANSWER_CELL = "ANSWER_CELL"
    MERGE_RANGE = "MERGE_RANGE"


class OutcomeStatus(StrEnum):
    """寫回或核對的三種結果（spec FR-015）。"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"


@dataclass(frozen=True)
class FinalizedEntry:
    """一個已定案候選（來自 004）。

    Attributes:
        round_number: 輪次。
        question_number: 題號。
        group_number: 組號。
        rank: 名次；被判錯者為 `None`。
        judged_wrong: 是否被老師判錯。
    """

    round_number: int
    question_number: int
    group_number: int
    rank: int | None
    judged_wrong: bool


@dataclass(frozen=True)
class FinalizedQuestion:
    """某輪某題的搶答成功者（來自 004）。

    Attributes:
        round_number: 輪次。
        question_number: 題號。
        success_group: 搶答成功者的組號；沒有為 `None`。
    """

    round_number: int
    question_number: int
    success_group: int | None


@dataclass(frozen=True)
class SubmissionFact:
    """一筆已接受提交（來自 003）。

    Attributes:
        round_number: 輪次。
        question_number: 題號。
        group_number: 組號。
        answers: 各子空格答案原文，`answers[i]` 是第 i+1 格。
        received_at: 後端接收時間（含時區）。
    """

    round_number: int
    question_number: int
    group_number: int
    answers: tuple[str, ...]
    received_at: datetime


@dataclass(frozen=True)
class BlankTarget:
    """一個空格與它的目標位置（來自 002 的來源映射）。

    Attributes:
        question_number: 題號。
        sub_index: 子編號；單題為 `None`。
        target: 答案格（合併範圍的左上角）。
    """

    question_number: int
    sub_index: int | None
    target: CellRef


@dataclass(frozen=True)
class CurrentCell:
    """目標格目前的內容（`userEnteredValue`）。

    Attributes:
        kind: 種類。
        text: 只在 `TEXT` 有值。
        display: 純文字顯示（數字、公式、布林等）。
    """

    kind: CellKind
    text: str | None = None
    display: str = ""


@dataclass(frozen=True)
class WritePlanItem:
    """成果快照中的一個子空格（預覽一列）。

    Attributes:
        round_number: 輪次。
        question_number: 題號。
        sub_index: 子編號；單題為 `None`。
        group_number: 搶答成功者組號。
        answer: 答案（逐字文字值）。
        target: 目標位置。
        impact: 覆寫影響。
        current_display: 原內容；只在 `REPLACE` 時有值（純文字、已截斷至 40 字元）。
    """

    round_number: int
    question_number: int
    sub_index: int | None
    group_number: int
    answer: str
    target: CellRef
    impact: OverwriteImpact
    current_display: str | None


@dataclass(frozen=True)
class ResultSnapshot:
    """預覽當下的成果快照。

    Attributes:
        snapshot_id: 已定案輪次編號集合決定的識別。
        items: 依（題號, 子編號）排序的項目。
        unwritten_questions: 不會寫入的題號（未成功、全被判錯、無人提交），遞增。
    """

    snapshot_id: str
    items: tuple[WritePlanItem, ...]
    unwritten_questions: tuple[int, ...]


@dataclass(frozen=True)
class StructureDifference:
    """一項結構差異。

    Attributes:
        kind: 類別。
        at: 位置；沒有位置時為 `None`。
        detail: 固定的類別說明，不含試算表文字。
    """

    kind: DiffKind
    at: CellRef | None
    detail: str


@dataclass(frozen=True)
class StructureCheck:
    """結構比對結論；`ok` 為真時 `differences` 為空。

    Attributes:
        ok: 是否相符。
        differences: 依位置排序的差異。
    """

    ok: bool
    differences: tuple[StructureDifference, ...]


@dataclass(frozen=True)
class CellCheck:
    """核對時逐格的結果。

    Attributes:
        question_number: 題號。
        sub_index: 子編號；單題為 `None`。
        expected: 預期答案。
        current_display: 目前內容（純文字）。
        matches: 是否與預期逐字相同。
    """

    question_number: int
    sub_index: int | None
    expected: str
    current_display: str
    matches: bool


@dataclass(frozen=True)
class Reconciliation:
    """核對判定。

    Attributes:
        status: 結果。
        checks: 逐格結果。
    """

    status: OutcomeStatus
    checks: tuple[CellCheck, ...]


@dataclass(frozen=True)
class ExportRow:
    """CSV 的一筆資料列。

    Attributes:
        round_number: 輪次。
        question_number: 題號。
        sub_index: 子空格；單題為 `None`。
        group_number: 組號。
        answer: 答案。
        received_at: 後端接收時間（含時區）。
        rank: 順位；答錯為 `None`。
        succeeded: 是否成功（名次 1 且未被判錯）。
        judged_wrong: 是否被老師判錯（搶答失敗不算）。
    """

    round_number: int
    question_number: int
    sub_index: int | None
    group_number: int
    answer: str
    received_at: datetime
    rank: int | None
    succeeded: bool
    judged_wrong: bool
