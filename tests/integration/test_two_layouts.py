"""T058：兩份版面的格數（憲章原則 III、SC-009）。

格數走 002 真實的匯入路徑：`PUT import/source` → `POST import` → 002 的
`ImportService`（`blanks_per_question`）→ 003 判定。版面 A（課程範本 [2, 2, 1, 1]）
與版面 B（整體移位、工作表更名、含三格題組 [1, 2, 3, 1]）各完成「格數錯誤被拒 →
正確格數接受 → 關輪公開」。格數只來自匯入結果，程式沒有假設固定格數，也沒有任何
繞過匯入的後門。

注意：Google 端用 002 的 Fake Sheets 讀取器（手寫版面），所以這不等於真實 Google
回應已驗證（見 002 quickstart B 區）。
"""

import pytest

from tests.conftest import create_activity, join_group, submit
from tests.fixtures.guided_notes_layouts import layout_a, layout_b

# 版面 → (fake_sheets_reader 內的工作表 ID, 期望)
LAYOUTS = {"A": (0, layout_a()[1]), "B": (7, layout_b()[1])}


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_layout_blanks_drive_validation(import_client, layout):
    client = import_client
    sheet_id, expected = LAYOUTS[layout]
    blanks = [count for _, count, _ in expected.questions]

    teacher = create_activity(client)
    code = teacher.code
    headers = teacher.headers
    put = client.put(
        f"/api/activities/{code}/import/source",
        json={"spreadsheetId": "sheet-1", "sheetId": sheet_id},
        headers=headers,
    )
    assert put.status_code == 200, put.text
    imported = client.post(f"/api/activities/{code}/import", json={}, headers=headers)
    assert imported.status_code == 200, imported.text

    # 格數來自 002 的匯入結果，而不是測試寫死的數字
    shapes = client.app.state.import_service.blanks_per_question(code)
    assert dict(shapes) == {n: b for n, b in enumerate(blanks, start=1)}

    client.post(f"/api/activities/{code}/open-joining", json={}, headers=headers)
    device = join_group(client, code, 1)
    client.post(f"/api/activities/{code}/rounds", json={}, headers=headers)

    snapshot = client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()
    assert snapshot["questionShapes"] == {
        str(n): b for n, b in enumerate(blanks, start=1)
    }

    widest = max(range(len(blanks)), key=lambda i: blanks[i]) + 1
    need = blanks[widest - 1]
    wrong = submit(client, code, device, 1, widest, ["x"] * (need + 1))
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "WRONG_BLANK_COUNT"
    right = submit(client, code, device, 1, widest, [f"格{i}" for i in range(need)])
    assert right.status_code == 201
    assert len(right.json()["submission"]["answers"]) == need

    closed = client.post(
        f"/api/activities/{code}/rounds/current/close", json={}, headers=headers
    )
    assert closed.status_code == 200
    published = client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()["submissions"]["published"]
    question = next(
        q for q in published[0]["questions"] if q["questionNumber"] == widest
    )
    assert question["entries"][0]["answers"] == [f"格{i}" for i in range(need)]
    assert len(published[0]["questions"]) == len(blanks)
