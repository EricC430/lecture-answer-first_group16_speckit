"""007 瀏覽器工作階段：發出瀏覽器金鑰 cookie（contracts/http-and-sync-changes.md §1）。

學生頁載入時先呼叫 `POST /api/browser-session`，確保這個瀏覽器有一把金鑰，加入組別時
才不會因為同一瀏覽器的兩個分頁同時第一次加入而各拿一把（research R3）。

金鑰只出現在 `Set-Cookie`（HttpOnly、SameSite=Strict），不在回應本文，也不寫入日誌。
"""

from fastapi import APIRouter, Request, Response

from lecture_quiz.app.activity.secrets_gen import new_browser_key

from .common import (
    BROWSER_COOKIE_MAX_AGE,
    BROWSER_COOKIE_NAME,
    annotate_request_log,
    browser_key_from,
)


def create_router() -> APIRouter:
    """建立 007 的 router（掛在 `/api` 之下）。

    Returns:
        只有 `POST /browser-session` 的 router。
    """
    router = APIRouter(tags=["browser-session"])

    @router.post("/browser-session", status_code=204)
    async def ensure_browser_session(request: Request) -> Response:
        """已有合法金鑰時不動 cookie；否則發一把新的（本文一律為空）。"""
        response = Response(status_code=204)
        if browser_key_from(request.cookies) is not None:
            annotate_request_log(request, result="OK")
            return response
        response.set_cookie(
            BROWSER_COOKIE_NAME,
            new_browser_key(),
            max_age=BROWSER_COOKIE_MAX_AGE,
            path="/",
            httponly=True,
            samesite="strict",
        )
        annotate_request_log(request, result="ISSUED")
        return response

    return router
