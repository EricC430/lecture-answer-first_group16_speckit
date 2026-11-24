"""逐列分類（research R4 步驟 3）。

每一列只可能是：有題號與子編號的子空格列、有題號沒有子編號的單題列，或被忽略的列
（沒有題號也沒有子編號；空白題號只在縱向合併範圍內繼承）。
"""

import re
from dataclasses import dataclass

from lecture_quiz.core.guided_notes_import.grid import (
    last_data_row,
    merge_containing,
    origin_of,
    text_at,
    value_at,
)
from lecture_quiz.core.guided_notes_import.headers import HeaderLayout
from lecture_quiz.core.guided_notes_import.hints import hint_for, quote
from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    IssueKind,
    SheetSnapshot,
    ValidationIssue,
)
from lecture_quiz.core.guided_notes_import.numbers import is_blank, normalize_number

SUB_INDEX_PATTERN = re.compile(r"[（(]([0-9]{1,9})[）)]")
"""子編號：半形或全形括號、半形數字；全形數字與括號內夾空白都不接受。"""


@dataclass(frozen=True)
class RowEntry:
    """一個被辨識的題目列。

    Attributes:
        row: 列。
        number: 題號（含從縱向合併繼承的值）。
        number_cell: 題號值所在的儲存格（合併範圍的左上角），回報問題時引用。
        sub_index: 子編號；單題列為 `None`。
        sub_cell: 子編號儲存格；單題列為 `None`。
        target: 答案格（合併範圍的左上角）；找不到時為 `None`。
    """

    row: int
    number: int
    number_cell: CellRef
    sub_index: int | None
    sub_cell: CellRef | None
    target: CellRef | None


def _find_sub_index(
    snapshot: SheetSnapshot, row: int, answer_cols: tuple[int, int]
) -> tuple[int, CellRef] | None:
    """在作答表頭涵蓋的欄範圍內找子編號；回傳 (子編號, 儲存格)。"""
    for col in range(answer_cols[0], answer_cols[1] + 1):
        ref = CellRef(row, col)
        match = SUB_INDEX_PATTERN.fullmatch(text_at(snapshot, ref))
        if match:
            return int(match.group(1)), ref
    return None


def _answer_target(snapshot: SheetSnapshot, row: int, col: int) -> CellRef | None:
    """指定儲存格作為答案格：必須在工作表範圍內；屬於合併範圍則取左上角。"""
    if col >= snapshot.col_count or row >= snapshot.row_count or col < 0:
        return None
    return origin_of(snapshot, row, col)


def classify_rows(
    snapshot: SheetSnapshot, layout: HeaderLayout
) -> tuple[list[RowEntry], list[ValidationIssue]]:
    """逐列分類資料列。

    Args:
        snapshot: 工作表快照。
        layout: 表頭定位結果。

    Returns:
        (題目列, 問題)。問題只含題號格式與孤立子空格；其餘由分組與整體檢查回報。
    """
    entries: list[RowEntry] = []
    issues: list[ValidationIssue] = []
    for row in range(layout.data_start_row, last_data_row(snapshot) + 1):
        origin = origin_of(snapshot, row, layout.number_col)
        merge = merge_containing(snapshot, row, layout.number_col)
        inherited = merge is not None and merge.top_left.row != row
        value = value_at(snapshot, origin)
        sub = _find_sub_index(snapshot, row, layout.answer_cols)

        if is_blank(value):
            if sub is not None:
                # 沒有題號（也不在有值的縱向合併範圍內）卻有子編號 → 孤立子空格
                _, sub_cell = sub
                issues.append(
                    ValidationIssue(
                        kind=IssueKind.ORPHAN_SUB_BLANK,
                        at=sub_cell,
                        quoted=quote(text_at(snapshot, sub_cell)),
                        hint=hint_for(IssueKind.ORPHAN_SUB_BLANK),
                    )
                )
            continue  # 沒有題號也沒有子編號：間隔列，忽略（FR-026）

        assert value is not None
        number = normalize_number(value)
        if number is None:
            if not inherited:  # 縱向合併的續列不重複回報同一個壞值
                issues.append(
                    ValidationIssue(
                        kind=IssueKind.NON_NUMERIC_NUMBER,
                        at=origin,
                        quoted=quote(value.display),
                        hint=hint_for(IssueKind.NON_NUMERIC_NUMBER),
                    )
                )
            continue

        if sub is not None:
            sub_index, sub_cell = sub
            sub_merge = merge_containing(snapshot, sub_cell.row, sub_cell.col)
            right = (sub_merge.last_col if sub_merge else sub_cell.col) + 1
            entries.append(
                RowEntry(
                    row=row,
                    number=number,
                    number_cell=origin,
                    sub_index=sub_index,
                    sub_cell=sub_cell,
                    target=_answer_target(snapshot, row, right),
                )
            )
        elif not inherited:
            # 明寫題號、沒有子編號：單題，答案位置取作答欄範圍首欄
            entries.append(
                RowEntry(
                    row=row,
                    number=number,
                    number_cell=origin,
                    sub_index=None,
                    sub_cell=None,
                    target=_answer_target(snapshot, row, layout.answer_cols[0]),
                )
            )
        # 空白題號繼承來的列且沒有子編號：合併範圍內的間隔列，忽略
    return entries, issues
