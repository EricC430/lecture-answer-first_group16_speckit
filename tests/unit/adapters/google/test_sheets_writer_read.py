"""GoogleSheetsWriter.read_cells（US3；手寫 mock，不連 Google）。"""

import asyncio

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import CellKind
from tests.unit.adapters.google.mock_google import ok, sheet_props
from tests.unit.adapters.google.writer_helpers import (
    SOURCE,
    make_writer,
    query_of,
    sequence,
)


def cells_response(start_row, start_col, rows):
    return {
        "sheets": [
            {
                "properties": {"sheetId": 0, "title": "學習單"},
                "data": [
                    {
                        "startRow": start_row,
                        "startColumn": start_col,
                        "rowData": [{"values": row} for row in rows],
                    }
                ],
            }
        ]
    }


def read(http, targets):
    return asyncio.run(make_writer(http).read_cells("ABC", SOURCE, targets))


def test_value_kinds_are_classified():
    """userEnteredValue：stringValue → TEXT；無值 → EMPTY；數字、布林、公式 → OTHER。"""
    http = sequence(
        ok({"sheets": [sheet_props(0, "學習單")]}),
        ok(
            cells_response(
                4,
                6,
                [
                    [{}, {"userEnteredValue": {"stringValue": "文字"}}],
                    [
                        {"userEnteredValue": {"numberValue": 123}},
                        {"userEnteredValue": {"formulaValue": "=1+1"}},
                    ],
                    [{"userEnteredValue": {"boolValue": True}}],
                ],
            )
        ),
    )
    targets = [
        CellRef(4, 6),
        CellRef(4, 7),
        CellRef(5, 6),
        CellRef(5, 7),
        CellRef(6, 6),
    ]
    result = read(http, targets)
    assert result.ok
    got = result.value
    assert got[CellRef(4, 6)].kind is CellKind.EMPTY
    assert (
        got[CellRef(4, 7)].kind is CellKind.TEXT and got[CellRef(4, 7)].text == "文字"
    )
    assert (
        got[CellRef(5, 6)].kind is CellKind.OTHER
        and got[CellRef(5, 6)].display == "123"
    )
    assert (
        got[CellRef(5, 7)].kind is CellKind.OTHER
        and got[CellRef(5, 7)].display == "=1+1"
    )
    assert (
        got[CellRef(6, 6)].kind is CellKind.OTHER
        and got[CellRef(6, 6)].display == "TRUE"
    )


def test_requests_only_user_entered_value_fields():
    """欄位遮罩只要 userEnteredValue，不要 effectiveValue。"""
    http = sequence(
        ok({"sheets": [sheet_props(0, "學習單")]}), ok(cells_response(0, 0, [[{}]]))
    )
    read(http, [CellRef(0, 0)])
    fields = query_of(http)["fields"][0]
    assert "userEnteredValue" in fields and "effectiveValue" not in fields
    assert "startRow" in fields and "startColumn" in fields


def test_offsets_are_restored_and_missing_targets_are_empty():
    """rowData 以 startRow／startColumn 位移；目標格不在回應內 → EMPTY。"""
    http = sequence(
        ok({"sheets": [sheet_props(0, "學習單")]}),
        ok(cells_response(8, 6, [[{"userEnteredValue": {"stringValue": "答"}}]])),
    )
    result = read(http, [CellRef(8, 6), CellRef(30, 30)])
    assert result.value[CellRef(8, 6)].text == "答"
    assert result.value[CellRef(30, 30)].kind is CellKind.EMPTY
