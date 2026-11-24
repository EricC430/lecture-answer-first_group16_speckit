"""Google Sheets／Drive 的唯讀存取（research R3）。

- 只呼叫讀取方法（`files.get`、`spreadsheets.get`），絕不修改老師的試算表（FR-023）。
- 同步的官方程式庫以 `asyncio.to_thread` 呼叫，不阻塞其他活動的同步推送（技術限制 4）。
- 回應轉成核心的 `SheetSnapshot`；Google 的型別與例外不得外洩到核心與應用層。
- `GridRange` 的結束索引採「不含」的假設
  （⚠ 待真實驗證，plan「待真實驗證的假設」第 2 項），
  轉成核心 `MergeRange` 的「含」。
"""

import asyncio
from collections.abc import Callable
from typing import Any, Protocol

from googleapiclient.discovery import build

from lecture_quiz.adapters.google.errors import CAUGHT, map_exception
from lecture_quiz.app.guided_notes_import.models import (
    ImportRejection,
    Result,
    SheetInfo,
    SourceRef,
    SpreadsheetInfo,
)
from lecture_quiz.core.guided_notes_import.models import (
    CellRef,
    CellValue,
    MergeRange,
    SheetSnapshot,
)

SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
INSPECT_FIELDS = (
    "properties.title,sheets.properties(sheetId,title,hidden,gridProperties)"
)
TITLE_FIELDS = "sheets.properties(sheetId,title)"
READ_FIELDS = (
    "sheets(properties(sheetId,title,gridProperties),merges,"
    "data(startRow,startColumn,rowData(values(effectiveValue,formattedValue))))"
)
DRIVE_FIELDS = "id,name,mimeType"


class CredentialsProvider(Protocol):
    """提供某個活動老師目前有效的憑證（由 `GoogleAuthGateway` 實作）。"""

    async def valid_credentials(self, code: str) -> Result[Any]:
        """取得有效憑證；未授權或已失效時為對應拒絕。"""
        ...


Services = tuple[Any, Any]
"""(Drive v3 資源, Sheets v4 資源)。"""
ServiceFactory = Callable[[Any], Services]


def default_service_factory(credentials: Any) -> Services:
    """以憑證建立真實的 Drive 與 Sheets 資源。

    Args:
        credentials: 有效的 Google 憑證。

    Returns:
        (Drive v3, Sheets v4)。
    """
    drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
    sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    return drive, sheets


def quote_sheet_title(title: str) -> str:
    """把工作表標題包成 A1 範圍：以單引號包住，標題內的單引號重複一次。

    Args:
        title: 工作表標題。

    Returns:
        可用於 `ranges` 的字串。
    """
    return "'" + title.replace("'", "''") + "'"


def _cell_value(raw: dict[str, Any]) -> CellValue | None:
    """把 `CellData` 轉成 `CellValue`；沒有值時為 `None`。"""
    effective = raw.get("effectiveValue")
    if not effective:
        return None
    display = str(raw.get("formattedValue", ""))
    if "numberValue" in effective:
        number = float(effective["numberValue"])
        return CellValue(number=number, text=None, display=display or str(number))
    if "stringValue" in effective:
        text = str(effective["stringValue"])
        return CellValue(number=None, text=text, display=display or text)
    # 布林、錯誤值等：不是數字也不是文字，保留顯示字串
    return CellValue(number=None, text=None, display=display or "?")


def to_snapshot(spreadsheet_id: str, sheet: dict[str, Any]) -> SheetSnapshot:
    """把 `spreadsheets.get` 回應中的一張工作表轉成核心的 `SheetSnapshot`。

    `rowData` 會省略結尾的空儲存格，並以 `startRow`、`startColumn` 位移，
    這裡還原成絕對的（列, 欄）座標，並保存工作表的列欄總數。

    Args:
        spreadsheet_id: 試算表識別。
        sheet: 回應中的 `Sheet` 物件。

    Returns:
        工作表快照。
    """
    properties = sheet.get("properties", {})
    grid = properties.get("gridProperties", {})
    cells: dict[CellRef, CellValue] = {}
    max_row = -1
    max_col = -1
    for data in sheet.get("data", []):
        start_row = int(data.get("startRow", 0))
        start_col = int(data.get("startColumn", 0))
        for r, row in enumerate(data.get("rowData", [])):
            for c, raw in enumerate(row.get("values", [])):
                value = _cell_value(raw)
                if value is not None:
                    ref = CellRef(start_row + r, start_col + c)
                    cells[ref] = value
                    max_row, max_col = max(max_row, ref.row), max(max_col, ref.col)
    merges: list[MergeRange] = []
    for merge in sheet.get("merges", []):
        first_row = int(merge.get("startRowIndex", 0))
        first_col = int(merge.get("startColumnIndex", 0))
        # GridRange 的結束索引是「不含」；核心的 MergeRange 是「含」
        last_row = int(merge.get("endRowIndex", first_row + 1)) - 1
        last_col = int(merge.get("endColumnIndex", first_col + 1)) - 1
        merges.append(MergeRange(first_row, first_col, last_row, last_col))
        max_row, max_col = max(max_row, last_row), max(max_col, last_col)
    return SheetSnapshot(
        spreadsheet_id=spreadsheet_id,
        sheet_id=int(properties.get("sheetId", 0)),
        sheet_name=str(properties.get("title", "")),
        row_count=int(grid.get("rowCount", max_row + 1)),
        col_count=int(grid.get("columnCount", max_col + 1)),
        cells=cells,
        merges=tuple(merges),
    )


class GoogleSheetsReader:
    """`SheetsReader` 的真實實作。"""

    def __init__(
        self,
        credentials: CredentialsProvider,
        service_factory: ServiceFactory = default_service_factory,
    ) -> None:
        """建立讀取器。

        Args:
            credentials: 憑證提供者（授權閘道）。
            service_factory: 建立 Drive／Sheets 資源；
                測試傳入以 `HttpMockSequence` 建的資源。
        """
        self._credentials = credentials
        self._service_factory = service_factory

    async def _services(self, code: str) -> Result[Services]:
        creds = await self._credentials.valid_credentials(code)
        if not creds.ok or creds.value is None:
            return Result.failure(creds.rejection or ImportRejection.NOT_AUTHORIZED)
        return Result.success(
            await asyncio.to_thread(self._service_factory, creds.value)
        )

    async def inspect(self, code: str, spreadsheet_id: str) -> Result[SpreadsheetInfo]:
        """先以 Drive 確認是 Google 試算表，再取得工作表清單（含隱藏旗標）。

        Args:
            code: 活動代碼。
            spreadsheet_id: 試算表識別。

        Returns:
            成功時為檢視結果；不是試算表為 `NOT_A_SPREADSHEET`。
        """
        services = await self._services(code)
        if not services.ok or services.value is None:
            return Result.failure(services.rejection or ImportRejection.READ_FAILED)
        drive, sheets = services.value
        try:
            meta = await asyncio.to_thread(
                lambda: (
                    drive.files()
                    .get(
                        fileId=spreadsheet_id,
                        fields=DRIVE_FIELDS,
                        supportsAllDrives=True,
                    )
                    .execute()
                )
            )
            if meta.get("mimeType") != SPREADSHEET_MIME:
                return Result.failure(ImportRejection.NOT_A_SPREADSHEET)
            body = await asyncio.to_thread(
                lambda: (
                    sheets.spreadsheets()
                    .get(spreadsheetId=spreadsheet_id, fields=INSPECT_FIELDS)
                    .execute()
                )
            )
        except CAUGHT as exc:
            return Result.failure(map_exception(exc))
        infos = tuple(
            SheetInfo(
                sheet_id=int(s["properties"]["sheetId"]),
                title=str(s["properties"].get("title", "")),
                hidden=bool(s["properties"].get("hidden", False)),
            )
            for s in body.get("sheets", [])
        )
        title = str(body.get("properties", {}).get("title", ""))
        return Result.success(SpreadsheetInfo(spreadsheet_id, title, infos))

    async def read(self, code: str, source: SourceRef) -> Result[SheetSnapshot]:
        """以欄位遮罩讀取一張工作表並轉成 `SheetSnapshot`（唯讀）。

        先以輕量請求取得該工作表的標題（組 `ranges` 用），再以一次欄位遮罩請求讀取內容。

        Args:
            code: 活動代碼。
            source: 來源識別。

        Returns:
            成功時為快照；工作表不存在為 `SHEET_NOT_FOUND`。
        """
        services = await self._services(code)
        if not services.ok or services.value is None:
            return Result.failure(services.rejection or ImportRejection.READ_FAILED)
        _, sheets = services.value
        try:
            listing = await asyncio.to_thread(
                lambda: (
                    sheets.spreadsheets()
                    .get(spreadsheetId=source.spreadsheet_id, fields=TITLE_FIELDS)
                    .execute()
                )
            )
            title = next(
                (
                    s["properties"]["title"]
                    for s in listing.get("sheets", [])
                    if int(s["properties"]["sheetId"]) == source.sheet_id
                ),
                None,
            )
            if title is None:
                return Result.failure(ImportRejection.SHEET_NOT_FOUND)
            body = await asyncio.to_thread(
                lambda: (
                    sheets.spreadsheets()
                    .get(
                        spreadsheetId=source.spreadsheet_id,
                        ranges=[quote_sheet_title(str(title))],
                        fields=READ_FIELDS,
                    )
                    .execute()
                )
            )
        except CAUGHT as exc:
            return Result.failure(map_exception(exc))
        for sheet in body.get("sheets", []):
            if int(sheet.get("properties", {}).get("sheetId", -1)) == source.sheet_id:
                return Result.success(to_snapshot(source.spreadsheet_id, sheet))
        return Result.failure(ImportRejection.SHEET_NOT_FOUND)
