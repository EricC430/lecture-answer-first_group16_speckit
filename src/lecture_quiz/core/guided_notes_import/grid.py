"""工作表快照的小工具：合併範圍查詢與儲存格文字。"""

from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    CellValue,
    MergeRange,
    SheetSnapshot,
)


def merge_containing(snapshot: SheetSnapshot, row: int, col: int) -> MergeRange | None:
    """回傳包含該儲存格的合併範圍；沒有時為 `None`。

    Args:
        snapshot: 工作表快照。
        row: 列。
        col: 欄。

    Returns:
        合併範圍或 `None`。
    """
    for merge in snapshot.merges:
        if merge.contains(row, col):
            return merge
    return None


def origin_of(snapshot: SheetSnapshot, row: int, col: int) -> CellRef:
    """合併範圍的左上角；不在任何合併範圍內時為該儲存格本身。

    Args:
        snapshot: 工作表快照。
        row: 列。
        col: 欄。

    Returns:
        值所在的儲存格位置。
    """
    merge = merge_containing(snapshot, row, col)
    return merge.top_left if merge is not None else CellRef(row, col)


def value_at(snapshot: SheetSnapshot, ref: CellRef) -> CellValue | None:
    """取得儲存格值；沒有內容時為 `None`。

    Args:
        snapshot: 工作表快照。
        ref: 位置。

    Returns:
        儲存格值或 `None`。
    """
    return snapshot.cells.get(ref)


def text_at(snapshot: SheetSnapshot, ref: CellRef) -> str:
    """取得儲存格的文字並去除首尾空白（含全形空白）；不是文字時為空字串。

    Args:
        snapshot: 工作表快照。
        ref: 位置。

    Returns:
        去除首尾空白後的文字。
    """
    value = snapshot.cells.get(ref)
    if value is None or value.text is None:
        return ""
    return value.text.strip()


def last_data_row(snapshot: SheetSnapshot) -> int:
    """工作表最後一列的索引（取列總數與最後一個有內容的列較大者）。

    Args:
        snapshot: 工作表快照。

    Returns:
        最後一列的索引。
    """
    last_cell = max((ref.row for ref in snapshot.cells), default=-1)
    return max(snapshot.row_count - 1, last_cell)
