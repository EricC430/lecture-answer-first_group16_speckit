"""分組與整體檢查（research R4 步驟 4～6）。

忽略空白列後，**相鄰**且題號相同的列歸為同一題（涵蓋縱向合併與逐列重複兩種表示）。
所有問題一起收集，不在第一個問題就停（FR-015）。
"""

from lecture_quiz.core.guided_notes_import.grid import text_at
from lecture_quiz.core.guided_notes_import.headers import HeaderLayout
from lecture_quiz.core.guided_notes_import.hints import a1, hint_for, quote
from lecture_quiz.core.guided_notes_import.models import (
    Blank,
    CellRef,
    IssueKind,
    Question,
    SheetSnapshot,
    ValidationIssue,
)
from lecture_quiz.core.guided_notes_import.rows import RowEntry


def _issue(
    snapshot: SheetSnapshot, kind: IssueKind, at: CellRef | None, **details: object
) -> ValidationIssue:
    value = snapshot.cells.get(at) if at is not None else None
    quoted = quote(value.display) if value is not None else None
    return ValidationIssue(
        kind=kind, at=at, quoted=quoted, hint=hint_for(kind, **details)
    )


def group_entries(
    entries: list[RowEntry],
) -> tuple[list[list[RowEntry]], list[RowEntry]]:
    """把題目列依相鄰且相同題號分組。

    Args:
        entries: 依列順序的題目列。

    Returns:
        (群組, 非相鄰重複題號的列)；後者不會進入任何群組。
    """
    groups: list[list[RowEntry]] = []
    closed: set[int] = set()
    duplicates: list[RowEntry] = []
    for entry in entries:
        if groups and groups[-1][0].number == entry.number:
            groups[-1].append(entry)
        elif entry.number in closed:
            duplicates.append(entry)
        else:
            if groups:
                closed.add(groups[-1][0].number)
            groups.append([entry])
    return groups, duplicates


def validate(
    snapshot: SheetSnapshot,
    layout: HeaderLayout,
    entries: list[RowEntry],
    *,
    has_row_issues: bool = False,
) -> tuple[tuple[Question, ...], tuple[Blank, ...], list[ValidationIssue]]:
    """分組並做整體檢查。

    Args:
        snapshot: 工作表快照（用來引用儲存格文字）。
        layout: 表頭定位結果。
        entries: 逐列分類後的題目列。
        has_row_issues: 逐列分類時已有問題（例如題號格式錯誤）；此時「找不到任何題號」
            只是它們的後果，不重複回報。

    Returns:
        (題目, 空格, 問題)。有任何問題時呼叫端必須丟棄題目與空格（原子）。
    """
    issues: list[ValidationIssue] = []
    groups, duplicates = group_entries(entries)
    for entry in duplicates:
        issues.append(
            _issue(snapshot, IssueKind.NON_ADJACENT_DUPLICATE, entry.number_cell)
        )

    questions: list[Question] = []
    blanks: list[Blank] = []
    expected_number = 1
    for group in groups:
        number = group[0].number
        if number != expected_number:
            issues.append(
                _issue(
                    snapshot,
                    IssueKind.NUMBER_GAP,
                    group[0].number_cell,
                    expected=expected_number,
                )
            )
        expected_number = number + 1

        with_sub = [e for e in group if e.sub_index is not None]
        without = [e for e in group if e.sub_index is None]
        if with_sub and without:
            issues.append(
                _issue(snapshot, IssueKind.SUB_INDEX_MISSING, without[0].number_cell)
            )
        elif not with_sub and len(without) > 1:
            issues.append(
                _issue(snapshot, IssueKind.SUB_INDEX_MISSING, without[1].number_cell)
            )
        seen: set[int] = set()
        expected_sub = 1
        for entry in with_sub:
            assert entry.sub_index is not None and entry.sub_cell is not None
            if entry.sub_index in seen:
                issues.append(
                    _issue(snapshot, IssueKind.SUB_INDEX_DUPLICATE, entry.sub_cell)
                )
            elif entry.sub_index != expected_sub:
                issues.append(
                    _issue(snapshot, IssueKind.SUB_INDEX_MISSING, entry.sub_cell)
                )
            seen.add(entry.sub_index)
            expected_sub = max(expected_sub, entry.sub_index) + 1

        for entry in group:
            if entry.target is None:
                at = entry.sub_cell if entry.sub_cell is not None else entry.number_cell
                issues.append(_issue(snapshot, IssueKind.MISSING_ANSWER_CELL, at))
            else:
                blanks.append(Blank(number, entry.sub_index, entry.target))
        questions.append(Question(number, len(group), bool(with_sub)))

    if not groups and not duplicates and not has_row_issues:
        issues.append(
            ValidationIssue(
                kind=IssueKind.NUMBER_GAP,
                at=layout.header_number,
                quoted=quote(text_at(snapshot, layout.header_number)),
                hint="表頭之下找不到任何題號。請從 1 開始填入題號與作答格。",
            )
        )

    owner: dict[CellRef, RowEntry] = {}
    for entry in entries:
        if entry.target is None:
            continue
        if entry.target in owner:
            at = entry.sub_cell if entry.sub_cell is not None else entry.number_cell
            issues.append(
                _issue(
                    snapshot,
                    IssueKind.TARGET_OVERLAP,
                    at,
                    other=(
                        f"{a1(entry.target)}"
                        f"（與第 {owner[entry.target].number} 題共用）"
                    ),
                )
            )
        else:
            owner[entry.target] = entry
    return tuple(questions), tuple(blanks), issues
