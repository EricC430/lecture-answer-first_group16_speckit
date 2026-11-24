"""兩份版面不同的學習單，走完整入口（原則 III、SC-003）。

路徑：`TestClient` → 真實 `GoogleSheetsReader`（`HttpMockSequence` 餵入**手寫**的
`spreadsheets.get` 回應 JSON）→ `parse` → 001 真實 `ActivityService`。
這驗證轉接層與解析的整合；它**不等於**真實 Google 回應已驗證（見 quickstart B 區）。
"""

import json

import pytest
from fastapi.testclient import TestClient

from lecture_quiz.adapters.google.sheets_reader import GoogleSheetsReader
from lecture_quiz.core.guided_notes_import.models import SheetSnapshot
from tests.conftest import FakeClock, ManualScheduler, create_activity, make_app
from tests.fixtures.google_json import to_google_sheet
from tests.fixtures.guided_notes_layouts import Expected, layout_a, layout_b
from tests.unit.adapters.google.mock_google import make_reader, ok, sheet_props
from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway

SHEET_ID = 42


def run_import(snapshot: SheetSnapshot) -> tuple[dict, dict, GoogleSheetsReader]:
    """以一份手寫回應走完 PUT source → POST import，回傳匯入結果與 001 快照。"""
    sheet = to_google_sheet(snapshot)
    sheet["properties"]["sheetId"] = SHEET_ID
    other = sheet_props(1, "無關的另一張")  # 試算表另有一張無關工作表
    responses = [
        # PUT source → inspect：Drive 類型檢查、工作表清單
        ok(
            {
                "id": "S1",
                "name": "x",
                "mimeType": "application/vnd.google-apps.spreadsheet",
            }
        ),
        ok(
            {
                "properties": {"title": "試算表"},
                "sheets": [other, sheet_props(SHEET_ID, snapshot.sheet_name)],
            }
        ),
        # POST import → read：先取標題，再以欄位遮罩讀內容
        ok({"sheets": [sheet_props(SHEET_ID, snapshot.sheet_name)]}),
        ok({"sheets": [sheet]}),
    ]
    reader, _ = make_reader(responses)
    app = make_app(
        FakeClock(),
        ManualScheduler(),
        import_auth_gateway=FakeAuthGateway(authorized=True),
        import_sheets_reader=reader,
    )
    with TestClient(app) as client:
        teacher = create_activity(client)
        put = client.put(
            f"/api/activities/{teacher.code}/import/source",
            json={"spreadsheetId": "S1", "sheetId": SHEET_ID},
            headers=teacher.headers,
        )
        assert put.status_code == 200, put.text
        imported = client.post(
            f"/api/activities/{teacher.code}/import", json={}, headers=teacher.headers
        )
        assert imported.status_code == 200, imported.text
        snap = client.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        )
        record = client.app.state.import_service.get_import_record(teacher.code)
        assert record is not None
        body = imported.json()
        body["_record"] = [
            (b.question_number, b.sub_index, (b.target.row, b.target.col))
            for b in record.blanks
        ]
        return body, snap.json(), reader


def check(snapshot: SheetSnapshot, expected: Expected) -> dict:
    body, activity_snapshot, _ = run_import(snapshot)
    assert body["totalQuestions"] == len(expected.questions)
    assert body["totalBlanks"] == expected.total_blanks
    assert body["questionNumbers"] == [q[0] for q in expected.questions]
    assert body["_record"] == list(expected.blanks)  # 每格答案位置
    # 001 只得到題號清單
    assert json.dumps(activity_snapshot).count("版面") == 0
    return body


def test_layout_a_course_template_four_questions_six_blanks():
    """Scenario: US3-AS1、US5-AS1"""
    snapshot, expected = layout_a()
    body = check(snapshot, expected)
    assert body["blanksPerQuestion"] == {"1": 2, "2": 2, "3": 1, "4": 1}


def test_layout_b_shifted_renamed_mixed_layout():
    """Scenario: US2-AS2、US3-AS5"""
    snapshot, expected = layout_b()
    check(snapshot, expected)


@pytest.mark.parametrize("origin", [(0, 0), (4, 2), (11, 6)])
def test_same_content_shifted_gives_same_counts_and_shifted_positions(origin):
    """SC-003：整體移位且工作表更名後，題數與格數相同，位置對應新位置。"""
    base, base_expected = layout_a((0, 0), "學習單")
    moved, moved_expected = layout_a(origin, f"改名{origin}")
    body_base = check(base, base_expected)
    body_moved = check(moved, moved_expected)
    for key in (
        "totalQuestions",
        "totalBlanks",
        "questionNumbers",
        "blanksPerQuestion",
    ):
        assert body_moved[key] == body_base[key]
    dr, dc = origin
    assert body_moved["_record"] == [
        (q, sub, (r + dr, c + dc)) for q, sub, (r, c) in body_base["_record"]
    ]
