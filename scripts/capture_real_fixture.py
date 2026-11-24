"""把真實的 `spreadsheets.get` 回應去識別化，存成 `tests/fixtures/real/<名稱>.json`。

只在真實路徑驗證通過後使用（quickstart B 區、tasks T072）：沒有這份真實 fixture，
就不得宣稱「JSON → 轉接層 → 解析」的入口路徑已驗證。

取得原始回應的方式（任選，只在本機操作，原始檔不要提交、不要貼到聊天或 Issue）：
用 Google 官方的 API Explorer（Sheets API `spreadsheets.get`）、以你自己的帳號對你自己的
試算表，`fields` 填
`sheets(properties(sheetId,title,gridProperties),merges,data(startRow,startColumn,rowData(values(effectiveValue,formattedValue))))`，
`ranges` 填工作表標題，把回應存成 JSON。

用法::

    python scripts/capture_real_fixture.py RAW.json 版面1

去識別化規則：試算表標題、工作表標題、帳號與檔案 ID 全部移除或改成固定字樣；
儲存格文字只保留解析需要的（「題號」「作答」、「（n）」子編號、純數字題號），
其他文字（題目敘述、答案）改成「文字」。數字題號與合併範圍、列欄位置原樣保留。
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

OUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "real"
KEEP = re.compile(r"^\s*(題號|作答|[（(][0-9]{1,9}[）)]|[0-9]{1,9})\s*$")
DROP_KEYS = {"spreadsheetId", "spreadsheetUrl", "hyperlink", "userEnteredFormat"}


def redact_cell(cell: dict[str, Any]) -> dict[str, Any]:
    """保留解析需要的內容，其餘文字改成固定字樣。"""
    effective = cell.get("effectiveValue")
    if not effective:
        return {}
    if "numberValue" in effective:
        return {
            "effectiveValue": {"numberValue": effective["numberValue"]},
            "formattedValue": str(cell.get("formattedValue", effective["numberValue"])),
        }
    if "stringValue" in effective:
        text = str(effective["stringValue"])
        kept = text if KEEP.match(text) else "文字"
        return {"effectiveValue": {"stringValue": kept}, "formattedValue": kept}
    return {
        "effectiveValue": {k: v for k, v in effective.items() if k != "formulaValue"}
    }


def deidentify(raw: dict[str, Any]) -> dict[str, Any]:
    """去識別化一份 `spreadsheets.get` 回應（只保留 `sheets`）。"""
    sheets = []
    for sheet in raw.get("sheets", []):
        props = sheet.get("properties", {})
        data = []
        for grid in sheet.get("data", []):
            rows = [
                {"values": [redact_cell(c) for c in row.get("values", [])]}
                for row in grid.get("rowData", [])
            ]
            data.append(
                {
                    "startRow": grid.get("startRow", 0),
                    "startColumn": grid.get("startColumn", 0),
                    "rowData": rows,
                }
            )
        sheets.append(
            {
                "properties": {
                    "sheetId": props.get("sheetId", 0),
                    "title": "工作表",
                    "gridProperties": props.get("gridProperties", {}),
                },
                "merges": [
                    {k: v for k, v in m.items() if k not in DROP_KEYS}
                    for m in sheet.get("merges", [])
                ],
                "data": data,
            }
        )
    return {"sheets": sheets}


def main(argv: list[str]) -> int:
    """命令列進入點：`RAW.json` 與輸出名稱。"""
    if len(argv) != 3:
        print(__doc__)
        return 2
    raw_path, name = Path(argv[1]), argv[2]
    if not re.fullmatch(r"[\w\-]+", name):
        print("輸出名稱只能是文字、數字、底線與連字號")
        return 2
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.json"
    out.write_text(
        json.dumps(deidentify(raw), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shown = out.relative_to(OUT_DIR.parents[2])
    print(f"已寫入 {shown}；請檢查內容沒有任何個人資料後再提交。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
