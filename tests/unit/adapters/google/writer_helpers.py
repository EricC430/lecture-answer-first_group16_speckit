"""005 寫入器的測試輔助（手寫 JSON 與 mock，不是真實 Google 回應）。"""

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from lecture_quiz.adapters.google.sheets_writer import GoogleSheetsWriter
from lecture_quiz.app.guided_notes_import.models import SourceRef
from tests.unit.adapters.google.mock_google import FakeCredentials

SOURCE = SourceRef("S1", 0)


def make_writer(
    http: Any, credentials: FakeCredentials | None = None
) -> GoogleSheetsWriter:
    """以指定的 http 物件（`HttpMockSequence` 或會丟例外的替身）建立寫入器。"""

    def factory(_credentials: Any) -> tuple[Any, Any]:
        drive = build("drive", "v3", http=http, static_discovery=True)
        sheets = build("sheets", "v4", http=http, static_discovery=True)
        return drive, sheets

    return GoogleSheetsWriter(credentials or FakeCredentials(), factory)


def sequence(*responses: tuple[dict[str, str], str]) -> HttpMockSequence:
    """以一串回應驅動的 mock。"""
    return HttpMockSequence(list(responses))


def body_of(http: HttpMockSequence, index: int = -1) -> dict[str, Any]:
    """第 index 個請求的 JSON 本文。"""
    return json.loads(http.request_sequence[index][2])


def query_of(http: HttpMockSequence, index: int = -1) -> dict[str, list[str]]:
    """第 index 個請求的查詢字串。"""
    return parse_qs(urlparse(http.request_sequence[index][0]).query)


def path_of(http: HttpMockSequence, index: int = -1) -> str:
    """第 index 個請求的路徑。"""
    return urlparse(http.request_sequence[index][0]).path
