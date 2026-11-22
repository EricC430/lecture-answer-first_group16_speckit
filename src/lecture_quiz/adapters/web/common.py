"""HTTP 共用基礎：錯誤格式、例外處理、請求日誌與共用標頭解析。

各子功能的 router（`adapters/web/<能力>.py`）都使用這裡的工具，讓所有端點的錯誤格式
與日誌欄位一致（contracts/http-api.md「共通規則」「日誌」）。

錯誤回應一律是 `{"error": {"code": "...", "message": "..."}}`，不含堆疊追蹤、檔案路徑、
token 或憑證（憲章原則 V）。請求日誌只記錄白名單欄位，不記錄標頭與本文（技術限制 3）。
"""

import logging
import time
from typing import Annotated
from urllib.parse import unquote

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("lecture_quiz.request")
_error_logger = logging.getLogger("lecture_quiz.error")

INVALID_REQUEST = "INVALID_REQUEST"
INTERNAL_ERROR = "INTERNAL_ERROR"
NOT_FOUND = "NOT_FOUND"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
HTTP_ERROR = "HTTP_ERROR"

_INTERNAL_ERROR_MESSAGE = "伺服器發生未預期的錯誤，請稍後再試。"
_STATUS_MESSAGES: dict[int, tuple[str, str]] = {
    404: (NOT_FOUND, "找不到這個路徑。"),
    405: (METHOD_NOT_ALLOWED, "不支援這個操作方式。"),
}
_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}

# 請求日誌的白名單欄位，處理函式以 `annotate_request_log` 填入。
_LOG_STATE_KEY = "lecture_quiz_log"


class ApiError(Exception):
    """可預期的業務錯誤；拋出後由例外處理器轉成統一的錯誤回應。

    Attributes:
        status_code: HTTP 狀態碼。
        code: 錯誤代碼，例如 `NOT_TEACHER`。
        message: 給使用者看、可修正的中文說明；不得含 token 或憑證。
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        """建立業務錯誤。

        Args:
            status_code: HTTP 狀態碼。
            code: 錯誤代碼。
            message: 可修正的中文說明。
        """
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """產生統一格式的錯誤回應。

    Args:
        status_code: HTTP 狀態碼。
        code: 錯誤代碼。
        message: 可修正的中文說明。

    Returns:
        本文為 `{"error": {"code", "message"}}` 的 `JSONResponse`。
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _field_name(loc: tuple[int | str, ...]) -> str:
    """把 pydantic 錯誤位置轉成欄位名稱，去掉 body／query 等前綴。"""
    parts = [str(p) for p in loc]
    if parts and parts[0] in _LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(parts) or "本文"


async def _handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    """把 `ApiError` 轉成錯誤回應。"""
    assert isinstance(exc, ApiError)
    annotate_request_log(request, result=exc.code)
    return error_response(exc.status_code, exc.code, exc.message)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """請求格式不符時回 400 `INVALID_REQUEST`，訊息指出是哪些欄位。"""
    assert isinstance(exc, RequestValidationError)
    fields: list[str] = []
    for err in exc.errors():
        name = _field_name(tuple(err.get("loc", ())))
        if name not in fields:
            fields.append(name)
    annotate_request_log(request, result=INVALID_REQUEST)
    message = f"請求格式不正確，請檢查欄位：{'、'.join(fields)}。"
    return error_response(400, INVALID_REQUEST, message)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    """把框架層的 HTTP 例外（例如 404、405）轉成統一格式，不回傳原始 detail。"""
    assert isinstance(exc, StarletteHTTPException)
    code, message = _STATUS_MESSAGES.get(exc.status_code, (HTTP_ERROR, "請求失敗。"))
    annotate_request_log(request, result=code)
    response = error_response(exc.status_code, code, message)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """未預期的錯誤回 500 與通用訊息；細節只寫入伺服端日誌。"""
    _error_logger.error(
        "未預期的錯誤 method=%s type=%s",
        request.method,
        type(exc).__name__,
        exc_info=exc,
    )
    return error_response(500, INTERNAL_ERROR, _INTERNAL_ERROR_MESSAGE)


def install_error_handlers(app: FastAPI) -> None:
    """在 app 上註冊所有共用例外處理器。

    Args:
        app: 要註冊的 FastAPI app。
    """
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)


def annotate_request_log(
    request: Request,
    *,
    activity_code: str | None = None,
    result: str | None = None,
    version: int | None = None,
) -> None:
    """為這次請求的日誌補上白名單欄位。

    只接受活動代碼、結果代碼與版本號，避免把 token 或憑證寫入日誌。

    Args:
        request: 目前的請求。
        activity_code: 活動代碼；預設取路徑參數 `code`。
        result: 結果代碼，例如 `OK` 或 `NOT_TEACHER`；預設依狀態碼推得。
        version: 操作後的活動版本號。
    """
    fields: dict[str, object] = request.scope.setdefault("state", {}).setdefault(
        _LOG_STATE_KEY, {}
    )
    if activity_code is not None:
        fields["activity_code"] = activity_code
    if result is not None:
        fields["result"] = result
    if version is not None:
        fields["version"] = version


def _path_template(scope: Scope) -> str:
    """取得路由樣板（例如 `/api/activities/{code}`），不記錄路徑參數的實際值。

    巢狀 router 的 route 物件只有相對路徑，因此改以實際路徑為底，
    把每個等於路徑參數值的片段換成 `{參數名}`。沒有匹配任何路由時回傳
    `<unmatched>`（不記錄使用者輸入的網址），靜態檔回傳 `<static>`。
    """
    if scope.get("endpoint") is None:
        return "<unmatched>"
    if "route" not in scope:
        return "<static>"
    by_value = {str(v): k for k, v in (scope.get("path_params") or {}).items()}
    segments = str(scope.get("path", "")).split("/")
    return "/".join(
        f"{{{by_value[unquote(s)]}}}" if unquote(s) in by_value else s for s in segments
    )


class RequestLogMiddleware:
    """每個 HTTP 請求記錄一行 INFO 日誌（contracts/http-api.md「日誌」）。

    記錄：方法、路徑樣板、活動代碼、結果代碼、狀態碼、版本號、耗時。
    不記錄：查詢字串、所有標頭（包含 `Authorization`）、請求與回應本文。
    """

    def __init__(self, app: ASGIApp) -> None:
        """包裝下一層 ASGI app。

        Args:
            app: 下一層 ASGI app。
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """處理一個 ASGI 呼叫；非 HTTP（例如 WebSocket）直接放行。

        Args:
            scope: ASGI scope。
            receive: ASGI receive。
            send: ASGI send。
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            self._log(scope, status, (time.perf_counter() - start) * 1000)

    @staticmethod
    def _log(scope: Scope, status: int, elapsed_ms: float) -> None:
        """依白名單輸出一行請求日誌。"""
        fields = scope.get("state", {}).get(_LOG_STATE_KEY, {})
        path_params = scope.get("path_params") or {}
        activity_code = fields.get("activity_code", path_params.get("code", "-"))
        result = fields.get("result", "OK" if status < 400 else f"HTTP_{status}")
        logger.info(
            "method=%s path=%s activity=%s result=%s status=%d version=%s "
            "elapsed_ms=%.1f",
            scope.get("method", "-"),
            _path_template(scope),
            activity_code,
            result,
            status,
            fields.get("version", "-"),
            elapsed_ms,
        )


def bearer_token(
    authorization: Annotated[str | None, Header()] = None,
) -> str | None:
    """FastAPI dependency：從 `Authorization: Bearer <token>` 取出 token。

    格式不符或沒有帶時回傳 `None`，由各子功能視為匿名身分。

    Args:
        authorization: `Authorization` 標頭值。

    Returns:
        token 字串；沒有或格式不符時為 `None`。
    """
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def idempotency_key(
    key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ] = None,
) -> str | None:
    """FastAPI dependency：取出 `Idempotency-Key` 標頭。

    超過 128 字元時，由共用驗證錯誤處理器回 400 `INVALID_REQUEST`。

    Args:
        key: `Idempotency-Key` 標頭值。

    Returns:
        去重用的 key；沒有帶時為 `None`。
    """
    return key
