"""擷取腳本的去識別化（以手寫的原始回應測試；不是真實回應）。"""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "capture_real_fixture.py"
spec = importlib.util.spec_from_file_location("capture_real_fixture", SCRIPT)
assert spec and spec.loader
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

RAW = {
    "spreadsheetId": "1AbC-secret-file-id",
    "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/1AbC-secret-file-id",
    "properties": {"title": "王小明的期中學習單", "locale": "zh_TW"},
    "sheets": [
        {
            "properties": {
                "sheetId": 7,
                "title": "第三週 資料",
                "gridProperties": {"rowCount": 20, "columnCount": 8},
            },
            "merges": [
                {
                    "sheetId": 7,
                    "startRowIndex": 3,
                    "endRowIndex": 4,
                    "startColumnIndex": 6,
                    "endColumnIndex": 8,
                }
            ],
            "data": [
                {
                    "startRow": 3,
                    "startColumn": 1,
                    "rowData": [
                        {
                            "values": [
                                {
                                    "effectiveValue": {"stringValue": "題號"},
                                    "formattedValue": "題號",
                                }
                            ]
                        },
                        {
                            "values": [
                                {
                                    "effectiveValue": {"numberValue": 1},
                                    "formattedValue": "1",
                                },
                                {
                                    "effectiveValue": {
                                        "stringValue": "請問王小明的學號是多少？"
                                    }
                                },
                                {
                                    "effectiveValue": {"stringValue": "(1)"},
                                    "formattedValue": "(1)",
                                },
                                {
                                    "effectiveValue": {
                                        "stringValue": "s123456@example.edu"
                                    }
                                },
                            ]
                        },
                    ],
                }
            ],
        }
    ],
}


def test_identifying_information_is_removed_but_structure_is_kept():
    out = capture.deidentify(RAW)
    dump = json.dumps(out, ensure_ascii=False)
    for secret in (
        "1AbC-secret-file-id",
        "王小明",
        "第三週",
        "s123456",
        "學號",
        "docs.google.com",
    ):
        assert secret not in dump
    sheet = out["sheets"][0]
    assert sheet["properties"]["sheetId"] == 7
    assert sheet["properties"]["gridProperties"] == {"rowCount": 20, "columnCount": 8}
    assert sheet["merges"] == [
        {
            "sheetId": 7,
            "startRowIndex": 3,
            "endRowIndex": 4,
            "startColumnIndex": 6,
            "endColumnIndex": 8,
        }
    ]
    values = sheet["data"][0]["rowData"]
    assert values[0]["values"][0]["effectiveValue"]["stringValue"] == "題號"
    assert values[1]["values"][0]["effectiveValue"]["numberValue"] == 1
    assert values[1]["values"][2]["effectiveValue"]["stringValue"] == "(1)"
    assert values[1]["values"][1]["effectiveValue"]["stringValue"] == "文字"
    assert sheet["data"][0]["startRow"] == 3 and sheet["data"][0]["startColumn"] == 1


def test_bad_output_name_is_refused():
    assert capture.main(["x", "RAW.json", "../escape"]) == 2
