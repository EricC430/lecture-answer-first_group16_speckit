"""Google 的例外 → `ImportRejection`（轉接層不得把 Google 的例外往上拋）。

對應：401 → `AUTH_EXPIRED`；403／404 → `PERMISSION_DENIED`；
429、逾時、5xx 與其他網路錯誤
→ `READ_FAILED`。回傳的只是代碼；訊息由應用層的固定對照表提供，不含憑證與內部細節。
"""

import socket

import httplib2
from google.auth.exceptions import GoogleAuthError, TransportError
from googleapiclient.errors import HttpError

from lecture_quiz.app.guided_notes_import.models import ImportRejection

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


def map_exception(exc: BaseException) -> ImportRejection:
    """把 Google 相關例外轉成拒絕代碼。

    Args:
        exc: 例外。

    Returns:
        對應的 `ImportRejection`。
    """
    if isinstance(exc, HttpError):
        status = exc.resp.status if exc.resp is not None else 0
        if status == 401:
            return ImportRejection.AUTH_EXPIRED
        if status in (403, 404):
            return ImportRejection.PERMISSION_DENIED
        return ImportRejection.READ_FAILED
    if isinstance(exc, GoogleAuthError) and not isinstance(exc, TransportError):
        # 例如 RefreshError：token 已被撤銷或過期，需要重新授權
        return ImportRejection.AUTH_EXPIRED
    return ImportRejection.READ_FAILED
