"""GoogleSheetsWriter.write_text_cells 的請求形狀（US3；手寫 mock，不連 Google）。"""

import asyncio

import pytest

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import OutcomeStatus
from tests.unit.adapters.google.mock_google import ok
from tests.unit.adapters.google.writer_helpers import (
    SOURCE,
    body_of,
    make_writer,
    path_of,
    sequence,
)

TRICKY = [
    "=1+1",
    "00123",
    "1/2",
    "3.0",
    "第一行\n第二行",
    "  前後空白  ",
    "'單引號開頭",
    "+1",
    "@x",
]


def write(http, cells):
    writer = make_writer(http)
    return asyncio.run(writer.write_text_cells("ABC", SOURCE, cells))


def test_single_batch_update_one_update_cells_per_cell():
    """Scenario: US3-AS1：只送一個 batchUpdate，每格一個 updateCells。"""
    http = sequence(ok({"spreadsheetId": "S1", "replies": [{}, {}, {}]}))
    cells = [(CellRef(4, 7), "甲一"), (CellRef(5, 7), "甲二"), (CellRef(8, 6), "單題")]
    result = write(http, cells)
    assert result.outcome is OutcomeStatus.SUCCESS and result.reason is None
    assert len(http.request_sequence) == 1, "不得先查工作表名稱或送出第二個請求"
    assert path_of(http).endswith("/spreadsheets/S1:batchUpdate")
    requests = body_of(http)["requests"]
    assert len(requests) == 3
    first = requests[0]["updateCells"]
    assert first["range"] == {
        "sheetId": 0,
        "startRowIndex": 4,
        "endRowIndex": 5,
        "startColumnIndex": 7,
        "endColumnIndex": 8,
    }
    assert first["rows"] == [
        {"values": [{"userEnteredValue": {"stringValue": "甲一"}}]}
    ]


def test_fields_only_user_entered_value_and_no_value_input_option():
    """Scenario: US3-AS1、AS6：fields 恰為 userEnteredValue，不用 valueInputOption。"""
    http = sequence(ok({"replies": [{}]}))
    write(http, [(CellRef(8, 6), "答")])
    body = body_of(http)
    assert body["requests"][0]["updateCells"]["fields"] == "userEnteredValue"
    assert "valueInputOption" not in str(body)
    assert set(body) == {"requests"}


@pytest.mark.parametrize("answer", TRICKY)
def test_answers_are_sent_verbatim_as_string_values(answer):
    """Scenario: US3-AS3、AS4（類似公式的答案）：以 stringValue 逐字送出，不加前綴。"""
    http = sequence(ok({"replies": [{}]}))
    write(http, [(CellRef(0, 0), answer)])
    value = body_of(http)["requests"][0]["updateCells"]["rows"][0]["values"][0]
    assert value == {"userEnteredValue": {"stringValue": answer}}


def test_merged_cell_writes_top_left_only():
    """Scenario: US3-AS6：合併作答格只寫左上角一格（range 只有一格）。"""
    http = sequence(ok({"replies": [{}]}))
    write(http, [(CellRef(8, 6), "答")])
    r = body_of(http)["requests"][0]["updateCells"]["range"]
    assert r["endRowIndex"] - r["startRowIndex"] == 1
    assert r["endColumnIndex"] - r["startColumnIndex"] == 1
