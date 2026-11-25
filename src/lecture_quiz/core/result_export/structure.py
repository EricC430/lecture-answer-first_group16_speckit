"""來源結構比對（純函式；FR-007～FR-009，research R5）。

輸入是 002 匯入時保存的 `StructureSnapshot` 與以同一個 `parse` 重新辨識目前工作表的
`ParseResult`；輸出逐項差異。作答格的文字內容不在結構內，所以只改作答文字不算變更。
"""

from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    ParseResult,
    StructureSnapshot,
)
from lecture_quiz.core.result_export.models import (
    DiffKind,
    StructureCheck,
    StructureDifference,
)

_DETAIL = {
    DiffKind.IDENTITY: "試算表或工作表已不是匯入時的那一份",
    DiffKind.UNRECOGNIZED: "目前的內容已無法辨識為合法的學習單",
    DiffKind.HEADER_POSITION: "表頭或資料區的位置與匯入時不同",
    DiffKind.QUESTION_NUMBER: "這一列的題號與匯入時不同",
    DiffKind.SUB_BLANK: "子空格與匯入時不同",
    DiffKind.ANSWER_CELL: "答案格的位置與匯入時不同",
    DiffKind.MERGE_RANGE: "合併範圍與匯入時不同",
}


def identity_difference() -> StructureDifference:
    """工作表已不存在或被換掉時的差異（由應用層在讀取失敗時使用）。"""
    return StructureDifference(DiffKind.IDENTITY, None, _DETAIL[DiffKind.IDENTITY])


def _diff(kind: DiffKind, at: CellRef | None) -> StructureDifference:
    return StructureDifference(kind, at, _DETAIL[kind])


def _sort_key(diff: StructureDifference) -> tuple[int, int, str]:
    if diff.at is None:
        return (-1, -1, diff.kind.value)
    return (diff.at.row, diff.at.col, diff.kind.value)


def compare_structure(
    imported: StructureSnapshot, reparsed: ParseResult
) -> StructureCheck:
    """逐項比對匯入時的結構與重新辨識的結果。

    Args:
        imported: 002 保存的匯入時結構。
        reparsed: 對目前工作表重新辨識的結果。

    Returns:
        相符時 `ok` 為真；否則列出全部差異（依位置排序，相同輸入輸出相同）。
    """
    current = reparsed.structure
    if not reparsed.ok or current is None:
        return StructureCheck(False, (_diff(DiffKind.UNRECOGNIZED, None),))
    diffs: list[StructureDifference] = []
    if imported.header_number != current.header_number:
        diffs.append(_diff(DiffKind.HEADER_POSITION, imported.header_number))
    if imported.header_answer != current.header_answer:
        diffs.append(_diff(DiffKind.HEADER_POSITION, imported.header_answer))
    if imported.answer_cols != current.answer_cols:
        diffs.append(_diff(DiffKind.HEADER_POSITION, imported.header_answer))
    if imported.data_start_row != current.data_start_row:
        diffs.append(
            _diff(DiffKind.HEADER_POSITION, CellRef(imported.data_start_row, 0))
        )
    for row in sorted(set(imported.row_numbers) | set(current.row_numbers)):
        if imported.row_numbers.get(row) != current.row_numbers.get(row):
            diffs.append(_diff(DiffKind.QUESTION_NUMBER, CellRef(row, 0)))
    for key in sorted(
        set(imported.answer_cells) | set(current.answer_cells),
        key=lambda k: (k[0], k[1] or 0),
    ):
        before = imported.answer_cells.get(key)
        after = current.answer_cells.get(key)
        if before is None or after is None:
            diffs.append(_diff(DiffKind.SUB_BLANK, before or after))
        elif before != after:
            diffs.append(_diff(DiffKind.ANSWER_CELL, before))
    for merge in set(imported.merges) ^ set(current.merges):
        diffs.append(
            _diff(DiffKind.MERGE_RANGE, CellRef(merge.first_row, merge.first_col))
        )
    diffs.sort(key=_sort_key)
    return StructureCheck(not diffs, tuple(diffs))
