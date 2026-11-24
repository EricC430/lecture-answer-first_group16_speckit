"""找表頭（FR-006、FR-007；research R4 步驟 2）。

只認文字去除首尾空白後**完全等於**「題號」「作答」的儲存格；不接受同義詞，
也不以文字以外的結構猜測。位置完全由內容與合併範圍推導，不含固定座標。
"""

from dataclasses import dataclass

from lecture_quiz.core.guided_notes_import.grid import (
    merge_containing,
    text_at,
    value_at,
)
from lecture_quiz.core.guided_notes_import.hints import hint_for, quote
from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    IssueKind,
    SheetSnapshot,
    ValidationIssue,
)

HEADER_NUMBER = "題號"
HEADER_ANSWER = "作答"


@dataclass(frozen=True)
class HeaderLayout:
    """表頭定位的結果。

    Attributes:
        header_number: 「題號」表頭位置。
        header_answer: 「作答」表頭位置。
        number_col: 題號欄（表頭合併範圍的起始欄）。
        answer_cols: 作答表頭涵蓋的欄範圍（首欄, 末欄），含。
        data_start_row: 資料起始列（兩個表頭合併範圍結束列的下一列）。
    """

    header_number: CellRef
    header_answer: CellRef
    number_col: int
    answer_cols: tuple[int, int]
    data_start_row: int


def _issue(
    snapshot: SheetSnapshot, kind: IssueKind, at: CellRef | None
) -> ValidationIssue:
    value = value_at(snapshot, at) if at is not None else None
    return ValidationIssue(
        kind=kind,
        at=at,
        quoted=quote(value.display) if value is not None else None,
        hint=hint_for(kind),
    )


def find_headers(
    snapshot: SheetSnapshot,
) -> tuple[HeaderLayout | None, tuple[ValidationIssue, ...]]:
    """在工作表中找「題號」「作答」表頭。

    Args:
        snapshot: 工作表快照。

    Returns:
        (定位結果, 問題)：成功時問題為空；缺少或歧義時定位結果為 `None`。
    """
    numbers = sorted(
        (ref for ref in snapshot.cells if text_at(snapshot, ref) == HEADER_NUMBER),
        key=lambda r: (r.row, r.col),
    )
    answers = sorted(
        (ref for ref in snapshot.cells if text_at(snapshot, ref) == HEADER_ANSWER),
        key=lambda r: (r.row, r.col),
    )
    issues: list[ValidationIssue] = []
    if not numbers:
        issues.append(_issue(snapshot, IssueKind.MISSING_HEADER_NUMBER, None))
    if not answers:
        issues.append(_issue(snapshot, IssueKind.MISSING_HEADER_ANSWER, None))
    if issues:
        return None, tuple(issues)
    if len(numbers) != 1 or len(answers) != 1 or numbers[0].row != answers[0].row:
        if len(numbers) > 1:
            at = numbers[1]
        elif len(answers) > 1:
            at = answers[1]
        else:
            at = answers[0]
        return None, (_issue(snapshot, IssueKind.AMBIGUOUS_HEADER, at),)
    number_ref, answer_ref = numbers[0], answers[0]
    number_merge = merge_containing(snapshot, number_ref.row, number_ref.col)
    answer_merge = merge_containing(snapshot, answer_ref.row, answer_ref.col)
    number_col = number_merge.first_col if number_merge else number_ref.col
    answer_cols = (
        (answer_merge.first_col, answer_merge.last_col)
        if answer_merge
        else (answer_ref.col, answer_ref.col)
    )
    end_row = max(
        number_merge.last_row if number_merge else number_ref.row,
        answer_merge.last_row if answer_merge else answer_ref.row,
    )
    layout = HeaderLayout(
        header_number=number_ref,
        header_answer=answer_ref,
        number_col=number_col,
        answer_cols=answer_cols,
        data_start_row=end_row + 1,
    )
    return layout, ()
