"""以 `HttpMockSequence` 餵入手寫回應的測試輔助（手寫 JSON，不是真實 Google 回應）。

真實 `spreadsheets.get` 回應只在真實驗證通過後由擷取腳本產生（quickstart B 區）；
這裡的 JSON 依官方欄位形狀手寫，用來驗證欄位遮罩、座標還原與錯誤對應。
"""

import json
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from lecture_quiz.adapters.google.sheets_reader import GoogleSheetsReader
from lecture_quiz.app.guided_notes_import.models import ImportRejection, Result


class FakeCredentials:
    """永遠有效的憑證提供者；或回傳指定的拒絕。"""

    def __init__(self, rejection: ImportRejection | None = None) -> None:
        self.rejection = rejection

    async def valid_credentials(self, code: str) -> Result[Any]:
        if self.rejection is not None:
            return Result.failure(self.rejection)
        return Result.success(object())


def ok(body: dict[str, Any]) -> tuple[dict[str, str], str]:
    return {"status": "200", "content-type": "application/json"}, json.dumps(body)


def status(code: int) -> tuple[dict[str, str], str]:
    return {"status": str(code), "content-type": "application/json"}, "{}"


def make_reader(
    responses: list[tuple[dict[str, str], str]],
    credentials: FakeCredentials | None = None,
) -> tuple[GoogleSheetsReader, HttpMockSequence]:
    """建立以一串回應驅動的讀取器；回傳它與可檢查請求的 mock。"""
    http = HttpMockSequence(list(responses))

    def factory(_credentials: Any) -> tuple[Any, Any]:
        drive = build("drive", "v3", http=http, static_discovery=True)
        sheets = build("sheets", "v4", http=http, static_discovery=True)
        return drive, sheets

    return GoogleSheetsReader(credentials or FakeCredentials(), factory), http


def sheet_props(sheet_id: int, title: str, hidden: bool = False) -> dict[str, Any]:
    props: dict[str, Any] = {"sheetId": sheet_id, "title": title}
    if hidden:
        props["hidden"] = True
    return {"properties": props}
