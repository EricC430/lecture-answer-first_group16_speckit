"""真實 Google 路徑驗證（手動執行：`pytest -m real_google`）。

這支測試**明確指定真實後端**：對已啟動的本機伺服器（`python -m lecture_quiz`，使用真實的
Google 轉接器與真實試算表）送 HTTP 請求；不使用任何 Fake，也不跟隨預設的離線設定。

前置（人工，一次性；見 specs/002-guided-notes-import/quickstart.md）：
1. 設定好 `.env` 並以 `python -m lecture_quiz` 啟動後端。
2. 在瀏覽器建立活動、在老師頁面完成 Google 授權，並用 Picker 選過要測試的試算表
   （`drive.file` 範圍只能讀取 Picker 選過的檔案）。
3. 設定下列環境變數（缺任何一項測試會**明確失敗**並說明缺什麼，不會跳過）：

   REAL_GOOGLE_BASE_URL        例如 http://localhost:8000
   REAL_GOOGLE_ACTIVITY_CODE   活動代碼
   REAL_GOOGLE_TEACHER_TOKEN   老師 token（瀏覽器 localStorage；不要貼到任何追蹤的檔案）
   REAL_GOOGLE_SPREADSHEET_ID  試算表識別
   REAL_GOOGLE_SHEET_ID        工作表識別（整數）
   REAL_GOOGLE_EXPECT_QUESTIONS 預期題數
   REAL_GOOGLE_EXPECT_BLANKS    預期總格數
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.real_google

REQUIRED = (
    "REAL_GOOGLE_BASE_URL",
    "REAL_GOOGLE_ACTIVITY_CODE",
    "REAL_GOOGLE_TEACHER_TOKEN",
    "REAL_GOOGLE_SPREADSHEET_ID",
    "REAL_GOOGLE_SHEET_ID",
    "REAL_GOOGLE_EXPECT_QUESTIONS",
    "REAL_GOOGLE_EXPECT_BLANKS",
)


def require_env() -> dict[str, str]:
    """缺少任何環境變數就明確失敗（不跳過、不退回離線路徑）。"""
    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        pytest.fail(
            "真實 Google 路徑驗證缺少環境變數："
            + "、".join(missing)
            + "。請依本檔開頭的說明設定後再執行 `pytest -m real_google`。"
        )
    return {name: os.environ[name].strip() for name in REQUIRED}


def test_real_import_end_to_end_through_the_running_backend():
    env = require_env()
    base = env["REAL_GOOGLE_BASE_URL"].rstrip("/")
    code = env["REAL_GOOGLE_ACTIVITY_CODE"]
    headers = {"Authorization": f"Bearer {env['REAL_GOOGLE_TEACHER_TOKEN']}"}
    with httpx.Client(base_url=base, headers=headers, timeout=30.0) as client:
        status = client.get(f"/api/activities/{code}/import/auth/status")
        assert status.status_code == 200, status.text
        assert status.json() == {"authorized": True}, "請先在老師頁面完成 Google 授權"
        inspected = client.post(
            f"/api/activities/{code}/import/source/inspect",
            json={"spreadsheetId": env["REAL_GOOGLE_SPREADSHEET_ID"]},
        )
        assert inspected.status_code == 200, inspected.text
        sheet_id = int(env["REAL_GOOGLE_SHEET_ID"])
        assert sheet_id in [s["sheetId"] for s in inspected.json()["sheets"]]
        selected = client.put(
            f"/api/activities/{code}/import/source",
            json={
                "spreadsheetId": env["REAL_GOOGLE_SPREADSHEET_ID"],
                "sheetId": sheet_id,
            },
        )
        assert selected.status_code == 200, selected.text
        imported = client.post(f"/api/activities/{code}/import", json={})
        assert imported.status_code == 200, imported.text
        body = imported.json()
        assert body["totalQuestions"] == int(env["REAL_GOOGLE_EXPECT_QUESTIONS"])
        assert body["totalBlanks"] == int(env["REAL_GOOGLE_EXPECT_BLANKS"])
