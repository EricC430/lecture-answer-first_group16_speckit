"""學習單解析器：`parse(snapshot) -> ParseResult`（純函式）。

輸入不可變的工作表快照，輸出題目、每格的來源映射與匯入時結構；沒有時間參數、沒有 I/O。
任一驗證失敗就整份拒絕，不產生任何題目（原子，FR-016）。題目敘述欄完全不讀取（FR-008）。
"""

from lecture_quiz.core.guided_notes_import.headers import HeaderLayout, find_headers
from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    ParseResult,
    SheetSnapshot,
    StructureSnapshot,
    ValidationIssue,
)
from lecture_quiz.core.guided_notes_import.rows import classify_rows
from lecture_quiz.core.guided_notes_import.validator import validate


def _sorted(issues: list[ValidationIssue]) -> tuple[ValidationIssue, ...]:
    """依位置排序，沒有位置的排最前面；結果是確定性的。"""

    def key(issue: ValidationIssue) -> tuple[int, int, int]:
        if issue.at is None:
            return (-1, -1, 0)
        return (issue.at.row, issue.at.col, 0)

    return tuple(sorted(issues, key=key))


def _structure(
    snapshot: SheetSnapshot,
    layout: HeaderLayout,
    row_numbers: dict[int, int],
    answer_cells: dict[tuple[int, int | None], CellRef],
) -> StructureSnapshot:
    header_row = min(layout.header_number.row, layout.header_answer.row)
    merges = tuple(m for m in snapshot.merges if m.last_row >= header_row)
    return StructureSnapshot(
        header_number=layout.header_number,
        header_answer=layout.header_answer,
        answer_cols=layout.answer_cols,
        data_start_row=layout.data_start_row,
        merges=merges,
        row_numbers=row_numbers,
        answer_cells=answer_cells,
    )


class GuidedNotesParser:
    """依「題號」「作答」表頭與合併範圍動態解析學習單。"""

    @staticmethod
    def parse(snapshot: SheetSnapshot) -> ParseResult:
        """解析一張工作表。

        Args:
            snapshot: 工作表快照。

        Returns:
            成功時含題目、空格與匯入時結構；任何問題都使結果整份失敗並列出全部問題。
        """
        layout, header_issues = find_headers(snapshot)
        if layout is None:
            return ParseResult(ok=False, issues=_sorted(list(header_issues)))
        entries, row_issues = classify_rows(snapshot, layout)
        questions, blanks, issues = validate(
            snapshot, layout, entries, has_row_issues=bool(row_issues)
        )
        all_issues = [*row_issues, *issues]
        if all_issues:
            return ParseResult(ok=False, issues=_sorted(all_issues))
        row_numbers = {e.row: e.number for e in entries}
        answer_cells = {(b.question_number, b.sub_index): b.target for b in blanks}
        return ParseResult(
            ok=True,
            questions=questions,
            blanks=blanks,
            structure=_structure(snapshot, layout, row_numbers, answer_cells),
        )
