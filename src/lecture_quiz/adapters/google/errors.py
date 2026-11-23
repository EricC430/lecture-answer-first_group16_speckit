"""Google 的例外 → `ImportRejection`（轉接層不得把 Google 的例外往上拋）。

對應：401 → `AUTH_EXPIRED`；403／404 → `PERMISSION_DENIED`；
429、逾時、5xx 與其他網路錯誤
→ `READ_FAILED`。回傳的只是代碼；訊息由應用層的固定對照表提供，不含憑證與內部細節。
"""

import json
import logging
import socket

import httplib2
from google.auth.exceptions import GoogleAuthError, TransportError
from googleapiclient.errors import HttpError

from lecture_quiz.app.guided_notes_import.models import ImportRejection

logger = logging.getLogger(__name__)

CAUGHT = (
    HttpError,
    GoogleAuthError,
    TransportError,
    httplib2.HttpLib2Error,
    socket.timeout,
    TimeoutError,
    OSError,
)
"""轉接層會攔下並轉成拒絕的例外；其他（程式錯誤）照常往上拋。"""


def _reason_code(exc: HttpError) -> str:
    """取出 Google 錯誤回應中的原因代碼（如 `notFound`、`SERVICE_DISABLED`）。

    只回傳代碼字串；解析失敗時為 `unknown`。不回傳訊息本文。
    """
    try:
        body = json.loads(exc.content.decode("utf-8"))
        error = body.get("error", {})
        details = error.get("details") or []
        for detail in details:
            reason = detail.get("reason")
            if isinstance(reason, str):
                return reason
        errors = error.get("errors") or []
        if errors and isinstance(errors[0].get("reason"), str):
            return str(errors[0]["reason"])
        return str(error.get("status", "unknown"))
    except (ValueError, AttributeError, TypeError):
        return "unknown"


def map_exception(exc: BaseException) -> ImportRejection:
    """把 Google 相關例外轉成拒絕代碼。

    Args:
        exc: 例外。

    Returns:
        對應的 `ImportRejection`。
    """
    if isinstance(exc, HttpError):
        status = exc.resp.status if exc.resp is not None else 0
        # 只記狀態碼與 Google 的原因代碼（不含訊息本文、token、標題），供診斷 403／404
        logger.warning(
            "Google API 錯誤：status=%s reason=%s", status, _reason_code(exc)
        )
        if status == 401:
            return ImportRejection.AUTH_EXPIRED
        if status in (403, 404):
            return ImportRejection.PERMISSION_DENIED
        return ImportRejection.READ_FAILED
    if isinstance(exc, GoogleAuthError) and not isinstance(exc, TransportError):
        # 例如 RefreshError：token 已被撤銷或過期，需要重新授權
        return ImportRejection.AUTH_EXPIRED
    return ImportRejection.READ_FAILED
