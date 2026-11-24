"""把 `SheetSnapshot` 還原成 `spreadsheets.get` 形狀的**手寫** JSON。

測試用，不是真實回應。

用來讓「走入口」的測試經過真實的 `GoogleSheetsReader`（`HttpMockSequence`）：
手寫 JSON → 轉接層 → 解析。真實回應 fixture 只在真實驗證通過後才存在
（`scripts/capture_real_fixture.py`）；在那之前不得宣稱入口路徑已驗證。
"""

from typing import Any

from lecture_quiz.core.guided_notes_import.models import CellRef, SheetSnapshot


def cell_json(snapshot: SheetSnapshot, row: int, col: int) -> dict[str, Any]:
    """單一儲存格的 `CellData`；空儲存格為 `{}`。"""
    value = snapshot.cells.get(CellRef(row, col))
    if value is None:
        return {}
    if value.number is not None:
        return {
            "effectiveValue": {"numberValue": value.number},
            "formattedValue": value.display,
        }
    if value.text is not None:
        return {
            "effectiveValue": {"stringValue": value.text},
            "formattedValue": value.display,
        }
    return {"effectiveValue": {"boolValue": True}, "formattedValue": value.display}


def to_google_sheet(snapshot: SheetSnapshot) -> dict[str, Any]:
    """依 `READ_FIELDS` 的形狀產生一張工作表的回應。

    列尾空儲存格照 Google 的行為省略。
    """
    last_row = max((r.row for r in snapshot.cells), default=-1)
    row_data = []
    for row in range(last_row + 1):
        cols = [r.col for r in snapshot.cells if r.row == row]
        width = max(cols) + 1 if cols else 0
        row_data.append({"values": [cell_json(snapshot, row, c) for c in range(width)]})
    return {
        "properties": {
            "sheetId": snapshot.sheet_id,
            "title": snapshot.sheet_name,
            "gridProperties": {
                "rowCount": snapshot.row_count,
                "columnCount": snapshot.col_count,
            },
        },
        "merges": [
            {
                "sheetId": snapshot.sheet_id,
                "startRowIndex": m.first_row,
                "endRowIndex": m.last_row + 1,  # GridRange 的結束索引為「不含」
                "startColumnIndex": m.first_col,
                "endColumnIndex": m.last_col + 1,
            }
            for m in snapshot.merges
        ],
        "data": [{"startRow": 0, "startColumn": 0, "rowData": row_data}],
    }
