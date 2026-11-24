"""Google Sheets 的目標格讀取與原子寫入（005；research R3、R4、R6）。

依據：已安裝 google-api-python-client 2.202.0 內附的 Sheets v4 文件（revision
20261019）：

- `spreadsheets.batchUpdate`：請求內任何一項無效就整批不套用，更新保證一起原子套用；
  所以 Google 回 4xx 就代表沒有任何格被改（明確失敗）。
- `ExtendedValue.stringValue`：字串型別，不會被解析成公式或數字。
- `UpdateCellsRequest.fields` 只列 `userEnteredValue` 時，只更新值，不動格式與合併。
- `drive.file` 列在 `batchUpdate` 可用的授權範圍內（實際是否足以寫入選定的檔案
  待真實驗證，research R17）。

同步的官方程式庫以 `asyncio.to_thread` 呼叫；Google 的型別與例外不得外洩到應用層；
日誌只記狀態碼，不記訊息本文、答案、儲存格內容與 token。
"""

import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any

from googleapiclient.errors import HttpError

from lecture_quiz.adapters.google.errors import CAUGHT, map_exception
from lecture_quiz.adapters.google.sheets_reader import (
    TITLE_FIELDS,
    CredentialsProvider,
    ServiceFactory,
    Services,
    default_service_factory,
    quote_sheet_title,
)
from lecture_quiz.app.guided_notes_import.models import (
    ImportRejection,
    Result,
    SourceRef,
)
from lecture_quiz.app.result_export.models import AttemptReason
from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import CellKind, CurrentCell, OutcomeStatus

logger = logging.getLogger(__name__)

CELL_FIELDS = (
    "sheets(properties(sheetId),"
    "data(startRow,startColumn,rowData(values(userEnteredValue))))"
)
"""只讀 `userEnteredValue`：才分得出公式與文字、數字與文字（research R4）。"""


def _current_cell(raw: Mapping[str, Any]) -> CurrentCell:
    """把 `CellData` 的 `userEnteredValue` 轉成 `CurrentCell`。"""
    entered = raw.get("userEnteredValue")
    if not entered:
        return CurrentCell(CellKind.EMPTY, None, "")
    if "stringValue" in entered:
        text = str(entered["stringValue"])
        return CurrentCell(CellKind.TEXT, text, text)
    if "numberValue" in entered:
        number = float(entered["numberValue"])
        shown = str(int(number)) if number.is_integer() else str(number)
        return CurrentCell(CellKind.OTHER, None, shown)
    if "boolValue" in entered:
        return CurrentCell(
            CellKind.OTHER, None, "TRUE" if entered["boolValue"] else "FALSE"
        )
    if "formulaValue" in entered:
        return CurrentCell(CellKind.OTHER, None, str(entered["formulaValue"]))
    return CurrentCell(CellKind.OTHER, None, "?")


def _credential_reason(rejection: ImportRejection | None) -> AttemptReason:
    """憑證取得失敗對應成原因類別。"""
    mapping = {
        ImportRejection.NOT_AUTHORIZED: AttemptReason.NOT_AUTHORIZED,
        ImportRejection.AUTH_EXPIRED: AttemptReason.AUTH_EXPIRED,
        ImportRejection.PERMISSION_DENIED: AttemptReason.PERMISSION_DENIED,
        ImportRejection.GOOGLE_NOT_CONFIGURED: AttemptReason.NOT_CONFIGURED,
    }
    if rejection is None:
        return AttemptReason.READ_FAILED
    return mapping.get(rejection, AttemptReason.READ_FAILED)


def _classify_http_status(status: int) -> WriteResult:
    """依 HTTP 狀態碼分類（research R6）。

    `batchUpdate` 有整批原子性：4xx 代表請求在驗證階段被拒、沒有任何格被改（明確失敗）；
    5xx 與無法判定的狀態無法證實請求有沒有被處理（待確認）。
    """
    failed = OutcomeStatus.FAILED
    if status == 401:
        return WriteResult(failed, AttemptReason.AUTH_EXPIRED)
    if status in (403, 404):
        return WriteResult(failed, AttemptReason.PERMISSION_DENIED)
    if status == 429:
        return WriteResult(failed, AttemptReason.RATE_LIMITED)
    if 400 <= status < 500:
        return WriteResult(failed, AttemptReason.REJECTED)
    return WriteResult(OutcomeStatus.PENDING, AttemptReason.UNKNOWN)


class GoogleSheetsWriter:
    """`SheetsWriter` 的真實實作。"""

    def __init__(
        self,
        credentials: CredentialsProvider,
        service_factory: ServiceFactory = default_service_factory,
    ) -> None:
        """建立寫入器。

        Args:
            credentials: 憑證提供者（沿用 002 的授權閘道）。
            service_factory: 建立 Drive／Sheets 資源；測試傳入 `HttpMockSequence` 版本。
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

    async def read_cells(
        self, code: str, source: SourceRef, targets: Sequence[CellRef]
    ) -> Result[Mapping[CellRef, CurrentCell]]:
        """讀取各目標格目前的 `userEnteredValue`（唯讀）。

        Args:
            code: 活動代碼。
            source: 來源識別。
            targets: 目標位置。

        Returns:
            成功時為各目標格內容（回應沒有的格為空）；失敗時為對應的拒絕。
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
                        fields=CELL_FIELDS,
                    )
                    .execute()
                )
            )
        except CAUGHT as exc:
            return Result.failure(map_exception(exc))
        wanted = set(targets)
        found: dict[CellRef, CurrentCell] = {}
        for sheet in body.get("sheets", []):
            if int(sheet.get("properties", {}).get("sheetId", -1)) != source.sheet_id:
                continue
            for data in sheet.get("data", []):
                start_row = int(data.get("startRow", 0))
                start_col = int(data.get("startColumn", 0))
                for r, row in enumerate(data.get("rowData", [])):
                    for c, raw in enumerate(row.get("values", [])):
                        ref = CellRef(start_row + r, start_col + c)
                        if ref in wanted:
                            found[ref] = _current_cell(raw)
        return Result.success(
            {ref: found.get(ref, CurrentCell(CellKind.EMPTY)) for ref in targets}
        )

    async def write_text_cells(
        self, code: str, source: SourceRef, cells: Sequence[tuple[CellRef, str]]
    ) -> WriteResult:
        """以單一 `batchUpdate` 把文字值原子寫入全部目標格。

        Args:
            code: 活動代碼。
            source: 來源識別。
            cells: （目標位置, 答案原文）。

        Returns:
            成功、明確失敗或待確認。
        """
        services = await self._services(code)
        if not services.ok or services.value is None:
            # 憑證取得失敗：尚未送出任何請求，沒有任何格被改動
            return WriteResult(
                OutcomeStatus.FAILED, _credential_reason(services.rejection)
            )
        _, sheets = services.value
        requests = [
            {
                "updateCells": {
                    "range": {
                        "sheetId": source.sheet_id,
                        "startRowIndex": ref.row,
                        "endRowIndex": ref.row + 1,
                        "startColumnIndex": ref.col,
                        "endColumnIndex": ref.col + 1,
                    },
                    "rows": [{"values": [{"userEnteredValue": {"stringValue": text}}]}],
                    "fields": "userEnteredValue",
                }
            }
            for ref, text in cells
        ]
        try:
            await asyncio.to_thread(
                lambda: (
                    sheets.spreadsheets()
                    .batchUpdate(
                        spreadsheetId=source.spreadsheet_id,
                        body={"requests": requests},
                    )
                    .execute(num_retries=0)
                )
            )
        except HttpError as exc:
            status = exc.resp.status if exc.resp is not None else 0
            logger.warning("Google 寫入錯誤：status=%s", status)  # 不記訊息本文
            return _classify_http_status(status)
        except CAUGHT:
            # 逾時、連線中斷等：無法證實請求有沒有被處理 → 待確認
            logger.warning("Google 寫入結果無法確認（網路錯誤或逾時）")
            return WriteResult(OutcomeStatus.PENDING, AttemptReason.UNKNOWN)
        return WriteResult(OutcomeStatus.SUCCESS, None)
