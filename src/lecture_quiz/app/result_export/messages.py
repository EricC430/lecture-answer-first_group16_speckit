"""005 的訊息與狀態碼對照表（集中管理；測試逐項檢查不含內部細節，FR-031）。

訊息一律用繁體中文，讓老師知道原因與如何處理；不含堆疊、檔案路徑、憑證、授權碼，也不
出現環境變數名稱。
"""

from lecture_quiz.app.result_export.models import AttemptReason, ExportRejection

_HTTP_STATUS = {
    ExportRejection.INVALID_REQUEST: 400,
    ExportRejection.NOT_TEACHER: 403,
    ExportRejection.ACTIVITY_NOT_FOUND: 404,
    ExportRejection.ACTIVITY_CANCELLED: 409,
    ExportRejection.NO_RESULTS: 409,
    ExportRejection.STALE_SNAPSHOT: 409,
    ExportRejection.ATTEMPT_NOT_FOUND: 404,
    ExportRejection.NOT_LATEST_ATTEMPT: 409,
    ExportRejection.WRITE_IN_PROGRESS: 409,
    ExportRejection.NO_IMPORT_RECORD: 409,
    ExportRejection.NOT_AUTHORIZED: 401,
    ExportRejection.AUTH_EXPIRED: 401,
    ExportRejection.PERMISSION_DENIED: 403,
    ExportRejection.READ_FAILED: 502,
    ExportRejection.GOOGLE_NOT_CONFIGURED: 503,
}

_MESSAGES = {
    ExportRejection.INVALID_REQUEST: "請求內容不正確，請檢查後再試一次。",
    ExportRejection.NOT_TEACHER: "需要這個活動的老師身分才能操作。",
    ExportRejection.ACTIVITY_NOT_FOUND: "找不到這個活動，請確認活動代碼。",
    ExportRejection.ACTIVITY_CANCELLED: "活動已取消，不提供寫回與 CSV 下載。",
    ExportRejection.NO_RESULTS: "目前沒有可寫回的結果。",
    ExportRejection.STALE_SNAPSHOT: "成果已更新，請重新預覽後再確認。",
    ExportRejection.ATTEMPT_NOT_FOUND: "找不到這次寫回紀錄。",
    ExportRejection.NOT_LATEST_ATTEMPT: "只能對最新一次寫回進行核對或重試。",
    ExportRejection.WRITE_IN_PROGRESS: "寫回正在進行中，請稍後再試。",
    ExportRejection.NO_IMPORT_RECORD: "找不到匯入學習單的記錄，無法對應寫回位置。",
    ExportRejection.NOT_AUTHORIZED: "尚未授權存取 Google 試算表，請先重新授權。",
    ExportRejection.AUTH_EXPIRED: "Google 授權已失效，請重新授權後再試。",
    ExportRejection.PERMISSION_DENIED: (
        "沒有權限存取這份試算表，請確認帳號對該檔案有編輯權限，或重新授權。"
    ),
    ExportRejection.READ_FAILED: "暫時無法讀取試算表，請稍後再試。",
    ExportRejection.GOOGLE_NOT_CONFIGURED: "尚未設定 Google 連線。",
}

_REASON_TEXT = {
    AttemptReason.NOT_AUTHORIZED: "尚未授權存取 Google 試算表，請重新授權。",
    AttemptReason.AUTH_EXPIRED: "Google 授權已失效，請重新授權。",
    AttemptReason.PERMISSION_DENIED: "沒有編輯這份試算表的權限，或該範圍受保護。",
    AttemptReason.REJECTED: "Google 拒絕了這次寫入，沒有任何儲存格被改動。",
    AttemptReason.RATE_LIMITED: "Google 暫時限制請求，沒有儲存格被改動，請稍後重試。",
    AttemptReason.STRUCTURE_CHANGED: "學習單的結構與匯入時不同，已停止寫入。",
    AttemptReason.NOT_CONFIGURED: "尚未設定 Google 連線。",
    AttemptReason.READ_FAILED: "暫時無法讀取試算表，沒有任何儲存格被改動。",
    AttemptReason.NOT_WRITTEN: "記錄的位置上沒有預期的內容，看起來尚未寫入。",
    AttemptReason.UNKNOWN: "無法確認寫入結果，請重新讀取核對或重試。",
}


def http_status(rejection: ExportRejection) -> int:
    """拒絕原因對應的 HTTP 狀態碼。"""
    return _HTTP_STATUS[rejection]


def message_of(rejection: ExportRejection) -> str:
    """拒絕原因的預設中文訊息。"""
    return _MESSAGES[rejection]


def reason_text(reason: AttemptReason) -> str:
    """寫回失敗或待確認的原因說明。"""
    return _REASON_TEXT[reason]
