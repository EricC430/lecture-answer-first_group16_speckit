"""005 真實 Google 路徑驗證（手動執行：`pytest -m real_google`）。

這支測試**明確指定真實後端**：對已啟動的本機伺服器（`python -m lecture_quiz`，使用真實的
Google 轉接器與真實試算表）送 HTTP 請求；不使用任何 Fake，也不跟隨預設的離線設定。
**會真的寫入你指定的試算表**，請只用測試用的複本。

前置（人工；見 specs/005-result-export/quickstart.md 的 C 節）：
1. 設定好 `.env` 並以 `python -m lecture_quiz` 啟動後端。
2. 在瀏覽器完成：建立活動、Google 授權、Picker 選檔、匯入、搶答、定案（活動中必須已有
   至少一個已定案且有搶答成功者的題目；本測試不負責製造搶答資料）。
3. 設定下列環境變數（缺任何一項會**明確失敗**並說明缺什麼，不跳過、不退回 mock）：

   REAL_GOOGLE_BASE_URL        例如 http://localhost:8000
   REAL_GOOGLE_ACTIVITY_CODE   活動代碼
   REAL_GOOGLE_TEACHER_TOKEN   老師 token（瀏覽器 localStorage；不要貼到任何追蹤的檔案）
   REAL_GOOGLE_ALLOW_WRITE     必須是 yes：確認你知道這支測試會寫入試算表
   REAL_GOOGLE_SPREADSHEET_ID_B  第二份（版面不同）試算表識別（只檢查有設定）
   REAL_GOOGLE_SHEET_ID_B        第二份工作表識別

驗證 research R17 第 3 項：寫入後讀回的內容與提交的答案逐字相同（含以等號、加號、減號、
@、單引號開頭、前導零、類日期與換行的答案，需要在搶答時送出這些答案）；再預覽時結構仍相符。
"""

import os

import httpx
import pytest

pytestmark = pytest.mark.real_google

REQUIRED = (
    "REAL_GOOGLE_BASE_URL",
    "REAL_GOOGLE_ACTIVITY_CODE",
    "REAL_GOOGLE_TEACHER_TOKEN",
    "REAL_GOOGLE_ALLOW_WRITE",
    "REAL_GOOGLE_SPREADSHEET_ID_B",
    "REAL_GOOGLE_SHEET_ID_B",
)


def require_env() -> dict[str, str]:
    """缺少任何環境變數就明確失敗（不跳過、不退回離線路徑）。"""
    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        pytest.fail(
            "真實 Google 寫回驗證缺少環境變數："
            + "、".join(missing)
            + "。請依本檔開頭的說明設定後再執行 `pytest -m real_google`。"
        )
    env = {name: os.environ[name].strip() for name in REQUIRED}
    if env["REAL_GOOGLE_ALLOW_WRITE"].lower() != "yes":
        pytest.fail(
            "REAL_GOOGLE_ALLOW_WRITE 必須是 yes（這支測試會寫入真實的試算表）。"
        )
    return env


def test_real_preview_write_recheck_and_second_preview():
    env = require_env()
    base = env["REAL_GOOGLE_BASE_URL"].rstrip("/")
    code = env["REAL_GOOGLE_ACTIVITY_CODE"]
    headers = {"Authorization": f"Bearer {env['REAL_GOOGLE_TEACHER_TOKEN']}"}
    root = f"/api/activities/{code}/export"
    with httpx.Client(base_url=base, headers=headers, timeout=60.0) as client:
        preview = client.post(f"{root}/preview", json={})
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body["structure"]["ok"] is True, body["structure"]
        assert body["items"], "活動中沒有已定案且有搶答成功者的題目"
        written = client.post(f"{root}/writes", json={"snapshotId": body["snapshotId"]})
        assert written.status_code == 200, written.text
        attempt = written.json()
        assert attempt["status"] == "SUCCESS", attempt
        checked = client.post(f"{root}/writes/{attempt['attemptId']}/recheck", json={})
        assert checked.status_code == 200, checked.text
        assert checked.json()["status"] == "SUCCESS"
        assert all(c["matches"] for c in checked.json()["cellChecks"]), (
            "讀回內容與答案不同"
        )
        again = client.post(f"{root}/preview", json={})
        assert again.status_code == 200, again.text
        assert again.json()["structure"]["ok"] is True, "寫入後結構應仍相符（研究 R5）"
        assert {i["impact"] for i in again.json()["items"]} == {"SAME"}
        csv = client.get(f"{root}/csv")
        assert csv.status_code == 200 and csv.content.startswith("\ufeff".encode())
