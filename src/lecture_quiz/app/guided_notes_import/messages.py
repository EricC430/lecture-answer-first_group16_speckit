"""老師看到的固定中文訊息（FR-022、SC-005）。

所有訊息集中在這裡，測試逐項檢查不含 token、授權碼、`state`、client secret、
檔案路徑與堆疊字樣。儲存格引用（表頭、題號文字）由核心截斷在 40 字元以內，
前端一律以 `textContent` 輸出。每個 `IssueKind` 的修正建議在核心的 `hints.py`。
"""

from lecture_quiz.app.guided_notes_import.models import ImportRejection

MESSAGES: dict[ImportRejection, str] = {
    ImportRejection.NOT_AUTHORIZED: (
        "尚未授權，未匯入任何題目。請按「重新授權」，同意讀取你的 Google 試算表。"
    ),
    ImportRejection.AUTH_DENIED: (
        "授權被取消或拒絕，未匯入任何題目。需要匯入時請重新授權。"
    ),
    ImportRejection.AUTH_EXPIRED: (
        "授權已失效或過期，未匯入任何題目。請重新授權後再試一次。"
    ),
    ImportRejection.PERMISSION_DENIED: (
        "沒有這份試算表的讀取權限，未匯入任何題目。"
        "請調整檔案的分享權限，或重新選擇檔案。"
    ),
    ImportRejection.NOT_A_SPREADSHEET: "請選擇 Google 試算表，其他類型的檔案無法匯入。",
    ImportRejection.SHEET_NOT_FOUND: (
        "沒有可選的工作表，或所選工作表不存在。請重新選擇。"
    ),
    ImportRejection.SOURCE_NOT_SELECTED: "尚未選好試算表與工作表，請先選檔。",
    ImportRejection.READ_FAILED: "暫時無法讀取試算表，未匯入任何題目。請稍後再試。",
    ImportRejection.VALIDATION_FAILED: (
        "學習單有問題，整份未匯入，既有題目沒有變動。請依下列位置修正後再匯入。"
    ),
    ImportRejection.ACTIVITY_NOT_FOUND: "找不到這個活動代碼，請確認後再輸入。",
    ImportRejection.NOT_TEACHER: "只有這個活動的老師可以匯入學習單。",
    ImportRejection.ROUND_STARTED: "搶答已開始，題目不可更動。",
    ImportRejection.ACTIVITY_CANCELLED: "活動已取消，無法匯入學習單。",
    ImportRejection.STAGE_NOT_PREPARING: "目前的活動階段不可匯入學習單。",
    ImportRejection.GATEWAY_REJECTED: (
        "活動階段或身分剛好改變，未匯入任何題目。請重新整理頁面後再試。"
    ),
    ImportRejection.GOOGLE_NOT_CONFIGURED: "尚未設定 Google 連線，請聯絡系統管理者。",
    ImportRejection.INVALID_REQUEST: "請求格式不正確，請檢查欄位。",
}


def message_for(rejection: ImportRejection) -> str:
    """取得拒絕原因對應的固定訊息。

    Args:
        rejection: 拒絕代碼。

    Returns:
        給老師看、可照著修正的中文訊息。
    """
    return MESSAGES[rejection]
