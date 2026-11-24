"""核心解析測試的輔助函式：把「文字矩陣＋合併範圍」轉成 `SheetSnapshot`。

矩陣的每個元素：
- `None` 或空字串：空儲存格（不進入 `cells`）。
- `float`／`int`：數值（`1.0` 與 `1` 都是數值，與文字 `"1"` 不同，FR-013）。
- `str`：文字。
- `bool`：布林（`number` 與 `text` 都是 `None`，模擬公式或布林值）。

合併範圍以 `(首列, 首欄, 末列, 末欄)`（含）表示，座標相對於矩陣左上角；
`origin` 會把整份內容平移。
"""

from collections.abc import Sequence

from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    CellValue,
    MergeRange,
    SheetSnapshot,
)

Cell = float | int | str | bool | None
Merge = tuple[int, int, int, int]


def to_cell_value(value: Cell) -> CellValue | None:
    """把矩陣元素轉成 `CellValue`；空儲存格回傳 `None`。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return CellValue(number=None, text=None, display="TRUE" if value else "FALSE")
    if isinstance(value, int | float):
        return CellValue(number=float(value), text=None, display=str(value))
    return CellValue(number=None, text=value, display=value)


def build_snapshot(
    matrix: Sequence[Sequence[Cell]],
    merges: Sequence[Merge] = (),
    *,
    sheet_name: str = "工作表1",
    origin: tuple[int, int] = (0, 0),
    row_count: int | None = None,
    col_count: int | None = None,
    spreadsheet_id: str = "sheet-test",
    sheet_id: int = 0,
) -> SheetSnapshot:
    """把文字矩陣與合併範圍轉成 `SheetSnapshot`。

    Args:
        matrix: 儲存格矩陣。
        merges: 合併範圍清單（相對於矩陣左上角，含）。
        sheet_name: 工作表名稱。
        origin: 整體平移（列, 欄）。
        row_count: 列總數；省略時為平移後的矩陣高度。
        col_count: 欄總數；省略時為平移後的矩陣寬度。
        spreadsheet_id: 試算表識別。
        sheet_id: 工作表識別。

    Returns:
        工作表快照。
    """
    dr, dc = origin
    cells: dict[CellRef, CellValue] = {}
    width = 0
    for r, row in enumerate(matrix):
        width = max(width, len(row))
        for c, value in enumerate(row):
            cell = to_cell_value(value)
            if cell is not None:
                cells[CellRef(r + dr, c + dc)] = cell
    shifted = tuple(
        MergeRange(r1 + dr, c1 + dc, r2 + dr, c2 + dc) for r1, c1, r2, c2 in merges
    )
    return SheetSnapshot(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        row_count=row_count if row_count is not None else dr + len(matrix),
        col_count=col_count if col_count is not None else dc + width,
        cells=cells,
        merges=shifted,
    )


class Sheet:
    """逐格建立測試工作表的小工具。"""

    def __init__(self, rows: int, cols: int) -> None:
        """建立 `rows` × `cols` 的空工作表。"""
        self.matrix: list[list[Cell]] = [[None] * cols for _ in range(rows)]
        self.merges: list[Merge] = []

    def set(self, row: int, col: int, value: Cell) -> "Sheet":
        """設定一個儲存格。"""
        self.matrix[row][col] = value
        return self

    def merge(self, r1: int, c1: int, r2: int, c2: int) -> "Sheet":
        """加入一個合併範圍。"""
        self.merges.append((r1, c1, r2, c2))
        return self

    def snapshot(
        self,
        sheet_name: str = "工作表1",
        origin: tuple[int, int] = (0, 0),
        **kwargs: object,
    ) -> SheetSnapshot:
        """轉成 `SheetSnapshot`。"""
        return build_snapshot(
            self.matrix,
            self.merges,
            sheet_name=sheet_name,
            origin=origin,
            **kwargs,  # type: ignore[arg-type]
        )
