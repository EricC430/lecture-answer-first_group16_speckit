"""`read`：欄位遮罩、座標還原、`GridRange` 轉換（手寫回應 JSON）。"""

import asyncio
from urllib.parse import parse_qs, urlparse

from lecture_quiz.adapters.google.sheets_reader import (
    READ_FIELDS,
    quote_sheet_title,
    to_snapshot,
)
from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from lecture_quiz.core.guided_notes_import.models import CellRef, MergeRange
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.unit.adapters.google.mock_google import make_reader, ok, sheet_props, status

SOURCE = SourceRef("S1", 7)


def run(coro):
    return asyncio.run(coro)


def num(value: float, shown: str | None = None) -> dict:
    return {
        "effectiveValue": {"numberValue": value},
        "formattedValue": shown or str(value),
    }


def txt(value: str) -> dict:
    return {"effectiveValue": {"stringValue": value}, "formattedValue": value}


def listing(*sheets: dict) -> tuple:
    return ok({"sheets": list(sheets)})


def test_field_mask_ranges_and_read_only_requests():
    """FR-023"""
    sheet = {
        "properties": {
            "sheetId": 7,
            "title": "O'Brien 的表",
            "gridProperties": {"rowCount": 3, "columnCount": 3},
        },
        "data": [{"rowData": []}],
    }
    reader, http = make_reader(
        [listing(sheet_props(7, "O'Brien 的表")), ok({"sheets": [sheet]})]
    )
    result = run(reader.read("ABC234", SOURCE))
    assert result.ok
    assert all(r[1] == "GET" for r in http.request_sequence)  # 全程只送出讀取請求
    query = parse_qs(urlparse(http.request_sequence[1][0]).query)
    assert query["fields"] == [READ_FIELDS]
    assert query["ranges"] == ["'O''Brien 的表'"]  # 標題含單引號時跳脫
    assert "includeGridData" not in query  # 設定 fields 時不需要


def test_quote_sheet_title_escapes_single_quotes():
    assert quote_sheet_title("a") == "'a'"
    assert quote_sheet_title("it's") == "'it''s'"
    assert quote_sheet_title("''") == "''''''"


def test_offsets_are_restored_to_absolute_coordinates_and_trailing_blanks_omitted():
    """Scenario: US2-AS2"""
    sheet = {
        "properties": {
            "sheetId": 7,
            "title": "X",
            "gridProperties": {"rowCount": 100, "columnCount": 26},
        },
        "data": [
            {
                "startRow": 5,
                "startColumn": 2,
                "rowData": [
                    {"values": [txt("題號"), {}, txt("作答")]},
                    {"values": [num(1)]},  # 結尾空儲存格被省略
                    {},
                ],
            }
        ],
    }
    snapshot = to_snapshot("S1", sheet)
    assert snapshot.cells[CellRef(5, 2)].text == "題號"
    assert snapshot.cells[CellRef(5, 4)].text == "作答"
    assert snapshot.cells[CellRef(6, 2)].number == 1.0
    assert CellRef(5, 3) not in snapshot.cells  # 空儲存格不進入
    assert (snapshot.row_count, snapshot.col_count) == (100, 26)  # 保存列欄總數


def test_gridrange_end_index_exclusive_becomes_inclusive():
    """⚠ 待真實驗證：結束索引為「不含」的假設（research R3）"""
    sheet = {
        "properties": {
            "sheetId": 7,
            "title": "X",
            "gridProperties": {"rowCount": 10, "columnCount": 10},
        },
        "merges": [
            {
                "sheetId": 7,
                "startRowIndex": 4,
                "endRowIndex": 6,
                "startColumnIndex": 1,
                "endColumnIndex": 2,
            },
            {"sheetId": 7, "endRowIndex": 1, "endColumnIndex": 3},  # 起始索引省略 = 0
        ],
        "data": [{"rowData": []}],
    }
    snapshot = to_snapshot("S1", sheet)
    assert snapshot.merges == (MergeRange(4, 1, 5, 1), MergeRange(0, 0, 0, 2))


def test_number_and_string_values_are_distinguished():
    """Scenario: US2-AS4"""
    sheet = {
        "properties": {
            "sheetId": 7,
            "title": "X",
            "gridProperties": {"rowCount": 3, "columnCount": 3},
        },
        "data": [
            {
                "rowData": [
                    {
                        "values": [
                            num(1.0, "1"),
                            txt("1"),
                            {
                                "effectiveValue": {"boolValue": True},
                                "formattedValue": "TRUE",
                            },
                        ]
                    },
                ]
            }
        ],
    }
    cells = to_snapshot("S1", sheet).cells
    assert cells[CellRef(0, 0)].number == 1.0 and cells[CellRef(0, 0)].text is None
    assert cells[CellRef(0, 1)].text == "1" and cells[CellRef(0, 1)].number is None
    boolean = cells[CellRef(0, 2)]
    assert boolean.number is None and boolean.text is None and boolean.display == "TRUE"


def test_handwritten_response_goes_through_the_adapter_into_the_parser():
    """走轉接層的入口測試（手寫回應；不等於真實回應已驗證）。"""
    sheet = {
        "properties": {
            "sheetId": 7,
            "title": "學習單",
            "gridProperties": {"rowCount": 6, "columnCount": 6},
        },
        "merges": [
            {
                "sheetId": 7,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 3,
                "endColumnIndex": 5,
            }
        ],
        "data": [
            {
                "startRow": 0,
                "startColumn": 0,
                "rowData": [
                    {"values": [txt("題號"), txt("題目"), {}, txt("作答")]},
                    {"values": [num(1), txt("敘述")]},
                    {"values": [txt("2"), txt("敘述")]},
                ],
            }
        ],
    }
    reader, _ = make_reader(
        [listing(sheet_props(7, "學習單")), ok({"sheets": [sheet]})]
    )
    snapshot = run(reader.read("ABC234", SOURCE)).value
    assert snapshot is not None
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert [(b.question_number, b.target) for b in result.blanks] == [
        (1, CellRef(1, 3)),
        (2, CellRef(2, 3)),
    ]


def test_missing_sheet_is_reported():
    """Edge: 選檔後檔案消失或失去權限"""
    reader, _ = make_reader([listing(sheet_props(1, "別張"))])
    assert (
        run(reader.read("ABC234", SOURCE)).rejection is ImportRejection.SHEET_NOT_FOUND
    )


def test_google_errors_during_read_become_rejections():
    """Scenario: US1-AS4"""
    for code, expected in (
        (403, ImportRejection.PERMISSION_DENIED),
        (500, ImportRejection.READ_FAILED),
    ):
        reader, _ = make_reader([status(code)])
        assert run(reader.read("ABC234", SOURCE)).rejection is expected
