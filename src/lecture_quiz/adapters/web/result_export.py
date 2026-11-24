"""005 的 HTTP 端點（contracts/http-api.md）：預覽、寫回、核對、重試、重新授權、CSV。

所有端點只限該活動的老師；身分由 001 的 `resolve_requester` 判定，不採信請求本文。
業務失敗由服務回傳 `ExportRejection`，在這裡轉成 `{"error": {"code", "message"}}`。
"""

from typing import TypeVar

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from lecture_quiz.app.activity.ports import Requester
from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.result_export.messages import http_status, message_of
from lecture_quiz.app.result_export.models import ExportRejection, Result
from lecture_quiz.app.result_export.service import ExportService
from lecture_quiz.app.result_export.views import attempt_json, preview_json
from lecture_quiz.core.activity.snapshot_view import JsonDict

from .common import ApiError, annotate_request_log
from .http_api import ACTIVITY_NOT_FOUND, ACTIVITY_NOT_FOUND_MESSAGE, Token

T = TypeVar("T")


class WriteBody(BaseModel):
    """`POST .../export/writes` 的本文：預覽時拿到的成果快照識別。"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    snapshot_id: StrictStr = Field(alias="snapshotId")


def unwrap(request: Request, code: str, token: str | None, result: Result[T]) -> T:
    """成功時取出值；失敗時轉成 `ApiError`。

    活動不存在時：帶 token 回 410 `ACTIVITY_GONE`，不帶 token 回 404（與 001 一致）。

    Args:
        request: 目前的請求。
        code: 正規化後的活動代碼。
        token: 請求帶的 token。
        result: 服務層結果。

    Returns:
        成功時的值。

    Raises:
        ApiError: 失敗時。
    """
    if result.ok and result.value is not None:
        return result.value
    reason = result.rejection
    assert reason is not None
    annotate_request_log(request, activity_code=code, result=reason.value)
    if reason is ExportRejection.ACTIVITY_NOT_FOUND:
        if token:
            raise ApiError(410, "ACTIVITY_GONE", message_of(reason))
        raise ApiError(404, ACTIVITY_NOT_FOUND, ACTIVITY_NOT_FOUND_MESSAGE)
    raise ApiError(http_status(reason), reason.value, message_of(reason))


def create_router(app: FastAPI) -> APIRouter:
    """建立 005 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.export_service`。

    Returns:
        005 的 router。
    """
    router = APIRouter(tags=["result-export"])

    def service() -> ExportService:
        svc = app.state.export_service
        assert isinstance(svc, ExportService)
        return svc

    def requester_for(code: str, token: str | None) -> Requester:
        return app.state.activity_service.resolve_requester(code, token)

    @router.post("/activities/{code}/export/preview")
    async def preview(request: Request, code: str, token: Token) -> JsonDict:
        """寫回預覽（X1）：只讀取，不改任何狀態。"""
        code = normalize_code_input(code)
        result = await service().preview(code, requester_for(code, token))
        view = unwrap(request, code, token, result)
        annotate_request_log(request, activity_code=code, result="OK")
        return preview_json(view)

    @router.post("/activities/{code}/export/writes")
    async def write(
        request: Request, code: str, body: WriteBody, token: Token
    ) -> JsonDict:
        """確認寫回（X2）：綁定預覽時的成果快照。"""
        code = normalize_code_input(code)
        result = await service().confirm_write(
            code, requester_for(code, token), body.snapshot_id
        )
        attempt = unwrap(request, code, token, result)
        annotate_request_log(request, activity_code=code, result=attempt.status.value)
        return attempt_json(attempt)

    @router.post("/activities/{code}/export/authorization")
    async def authorization(request: Request, code: str, token: Token) -> JsonDict:
        """重新授權入口（X6）：除已取消外任何階段都可使用。"""
        code = normalize_code_input(code)
        result = await service().start_authorization(code, requester_for(code, token))
        url = unwrap(request, code, token, result)
        annotate_request_log(request, activity_code=code, result="OK")
        return {"authUrl": url}

    return router
