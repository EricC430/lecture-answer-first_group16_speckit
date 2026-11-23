"""學習單匯入的核心資料型別（data-model.md「核心層」）。

全部是不可變的資料類別，只用標準函式庫；座標一律 0 起算的（列, 欄）。
任何型別都不含題目敘述（FR-008），也不含時間或 I/O，所以解析是確定性的。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class CellRef:
    """一個儲存格位置（0 起算）。

    Attributes:
        row: 列。
        col: 欄。
    """

    row: int
    col: int


@dataclass(frozen=True)
class CellValue:
    """一個儲存格的值。

    `number` 與 `text` 來自 Google 的 `effectiveValue`，
    才能區分「數值 1.0」與「文字『1』」（FR-013）。布林、錯誤值等兩者都為 `None`。

    Attributes:
        number: 數值；不是數值時為 `None`。
        text: 文字；不是文字時為 `None`。
        display: 顯示用字串，只用於訊息引用。
    """

    number: float | None = None
    text: str | None = None
    display: str = ""


@dataclass(frozen=True)
class MergeRange:
    """合併範圍（四個邊界皆含）。

    Attributes:
        first_row: 起始列。
        first_col: 起始欄。
        last_row: 結束列（含）。
        last_col: 結束欄（含）。
    """

    first_row: int
    first_col: int
    last_row: int
    last_col: int

    @property
    def top_left(self) -> CellRef:
        """合併範圍的左上角。"""
        return CellRef(self.first_row, self.first_col)

    def contains(self, row: int, col: int) -> bool:
        """儲存格是否落在這個範圍內。

        Args:
            row: 列。
            col: 欄。

        Returns:
            落在範圍內時為 True。
        """
        return (
            self.first_row <= row <= self.last_row
            and self.first_col <= col <= self.last_col
        )


@dataclass(frozen=True)
class SheetSnapshot:
    """一張工作表在某次讀取當下的內容（只含有內容的儲存格）。

    Attributes:
        spreadsheet_id: 試算表識別。
        sheet_id: 工作表識別。
        sheet_name: 工作表名稱（解析不依賴它）。
        row_count: 列總數，用來判斷「右側沒有儲存格」。
        col_count: 欄總數。
        cells: 有內容的儲存格。
        merges: 合併範圍。
    """

    spreadsheet_id: str
    sheet_id: int
    sheet_name: str
    row_count: int
    col_count: int
    cells: Mapping[CellRef, CellValue] = field(default_factory=dict)
    merges: tuple[MergeRange, ...] = ()


class IssueKind(StrEnum):
    """驗證問題的種類（FR-007、FR-015）。"""

    MISSING_HEADER_NUMBER = "MISSING_HEADER_NUMBER"
    MISSING_HEADER_ANSWER = "MISSING_HEADER_ANSWER"
    AMBIGUOUS_HEADER = "AMBIGUOUS_HEADER"
    NON_NUMERIC_NUMBER = "NON_NUMERIC_NUMBER"
    NUMBER_GAP = "NUMBER_GAP"
    NON_ADJACENT_DUPLICATE = "NON_ADJACENT_DUPLICATE"
    SUB_INDEX_MISSING = "SUB_INDEX_MISSING"
    SUB_INDEX_DUPLICATE = "SUB_INDEX_DUPLICATE"
    ORPHAN_SUB_BLANK = "ORPHAN_SUB_BLANK"
    MISSING_ANSWER_CELL = "MISSING_ANSWER_CELL"
    TARGET_OVERLAP = "TARGET_OVERLAP"


@dataclass(frozen=True)
class ValidationIssue:
    """一個驗證問題。

    Attributes:
        kind: 問題種類。
        at: 位置；缺表頭這類沒有位置的問題為 `None`。
        quoted: 被引用的儲存格文字（已截斷，當純文字顯示）。
        hint: 老師可照做的修正建議。
    """

    kind: IssueKind
    at: CellRef | None
    quoted: str | None
    hint: str


@dataclass(frozen=True)
class Question:
    """一個競賽題目；題組算一題（FR-018）。

    Attributes:
        number: 邏輯題號。
        blank_count: 空格數。
        is_group: 是否題組。
    """

    number: int
    blank_count: int
    is_group: bool


@dataclass(frozen=True)
class Blank:
    """一個空格與它的精確答案位置（來源映射的一筆）。

    Attributes:
        question_number: 所屬題號。
        sub_index: 子編號；單題為 `None`。
        target: 答案格（合併範圍的左上角），永遠不是編號格（FR-010）。
    """

    question_number: int
    sub_index: int | None
    target: CellRef


@dataclass(frozen=True)
class StructureSnapshot:
    """匯入當下的結構，供寫回前比對來源有沒有被改動（FR-024）。

    Attributes:
        header_number: 「題號」表頭位置。
        header_answer: 「作答」表頭位置。
        answer_cols: 作答表頭涵蓋的欄範圍（首欄, 末欄），含。
        data_start_row: 資料起始列。
        merges: 與表頭列及資料區相交的合併範圍。
        row_numbers: 各資料列對應的題號（含繼承）。
        answer_cells: (題號, 子編號) 對應的答案格。
    """

    header_number: CellRef
    header_answer: CellRef
    answer_cols: tuple[int, int]
    data_start_row: int
    merges: tuple[MergeRange, ...]
    row_numbers: Mapping[int, int]
    answer_cells: Mapping[tuple[int, int | None], CellRef]


@dataclass(frozen=True)
class ParseResult:
    """解析結果。

    `ok` 為真時 `issues` 為空；為假時 `questions`、`blanks`、`structure` 全空
    （原子，FR-016）。

    Attributes:
        ok: 是否成功。
        questions: 題目清單。
        blanks: 每個空格的來源映射。
        structure: 匯入時結構。
        issues: 驗證問題（全部收集）。
    """

    ok: bool
    questions: tuple[Question, ...] = ()
    blanks: tuple[Blank, ...] = ()
    structure: StructureSnapshot | None = None
    issues: tuple[ValidationIssue, ...] = ()
