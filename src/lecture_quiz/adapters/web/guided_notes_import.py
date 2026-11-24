"""002 的 HTTP 端點：Google 授權、選檔、選工作表與匯入（contracts/http-api.md）。

所有端點只限該活動的老師（回呼端點除外，它以 `state` 驗證）；學生沒有任何匯入端點。
錯誤格式、Bearer／Idempotency-Key 解析與請求日誌沿用 `common.py`。
日誌只記活動代碼、端點結果代碼與 001 版本，不記 token、授權碼、`state`、試算表標題。
"""

from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from lecture_quiz.adapters.google.auth import GoogleAuthGateway
from lecture_quiz.adapters.google.sheets_reader import GoogleSheetsReader
from lecture_quiz.adapters.web.common import (
    ApiError,
    annotate_request_log,
    bearer_token,
    idempotency_key,
)
from lecture_quiz.app.activity.ports import Requester
from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.guided_notes_import.messages import message_for
from lecture_quiz.app.guided_notes_import.models import (
    ImportOutcome,
    ImportRejection,
    SourceRef,
)
from lecture_quiz.app.guided_notes_import.ports import AuthGateway
from lecture_quiz.app.guided_notes_import.service import ImportService
from lecture_quiz.app.guided_notes_import.store import ImportStore
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.guided_notes_import.hints import column_letters
from lecture_quiz.core.guided_notes_import.models import ValidationIssue

_STATUS: dict[ImportRejection, int] = {
    ImportRejection.INVALID_REQUEST: 400,
    ImportRejection.NOT_TEACHER: 403,
    ImportRejection.ACTIVITY_NOT_FOUND: 404,
    ImportRejection.NOT_AUTHORIZED: 401,
    ImportRejection.AUTH_EXPIRED: 401,
    ImportRejection.AUTH_DENIED: 403,
    ImportRejection.PERMISSION_DENIED: 403,
    ImportRejection.NOT_A_SPREADSHEET: 422,
    ImportRejection.SHEET_NOT_FOUND: 422,
    ImportRejection.SOURCE_NOT_SELECTED: 422,
    ImportRejection.VALIDATION_FAILED: 422,
    ImportRejection.ROUND_STARTED: 409,
    ImportRejection.ACTIVITY_CANCELLED: 409,
    ImportRejection.STAGE_NOT_PREPARING: 409,
    ImportRejection.GATEWAY_REJECTED: 409,
    ImportRejection.READ_FAILED: 502,
    ImportRejection.GOOGLE_NOT_CONFIGURED: 503,
}
ID_MAX_LENGTH = 200

Token = Annotated[str | None, Depends(bearer_token)]
IdempotencyKey = Annotated[str | None, Depends(idempotency_key)]

JsonDict = dict[str, Any]


class EmptyBody(BaseModel):
    """`{}` 本文；不接受任何欄位。"""

    model_config = ConfigDict(extra="forbid")


class InspectBody(BaseModel):
    """`POST /import/source/inspect` 的本文。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    spreadsheet_id: StrictStr = Field(
        alias="spreadsheetId", min_length=1, max_length=ID_MAX_LENGTH
    )


class SourceBody(InspectBody):
    """`PUT /import/source` 的本文。"""

    sheet_id: StrictInt = Field(alias="sheetId")


def issue_json(issue: ValidationIssue) -> JsonDict:
    """把驗證問題轉成 API 形狀：列從 1 起算、欄以字母表示，無位置時為 `null`。"""
    return {
        "kind": issue.kind.value,
        "row": issue.at.row + 1 if issue.at is not None else None,
        "col": column_letters(issue.at.col) if issue.at is not None else None,
        "quoted": issue.quoted,
        "hint": issue.hint,
    }


def result_json(outcome: ImportOutcome) -> JsonDict:
    """成功的匯入結果（`ImportResult`）。"""
    preview = outcome.preview
    assert preview is not None
    return {
        "imported": True,
        "sheetTitle": outcome.sheet_title,
        "questionNumbers": list(preview.question_numbers),
        "blanksPerQuestion": {
            str(k): v for k, v in preview.blanks_per_question.items()
        },
        "totalQuestions": preview.total_questions,
        "totalBlanks": preview.total_blanks,
        "version": outcome.version,
    }


def _build_service(app: FastAPI) -> tuple[ImportService, AuthGateway]:
    """組裝服務：測試可經 `app.state` 注入 Fake，省略時使用真實 Google 轉接器。"""
    store = ImportStore()
    gateway = getattr(app.state, "import_auth_gateway", None)
    if gateway is None:
        gateway = GoogleAuthGateway(store, app.state.clock)
    reader = getattr(app.state, "import_sheets_reader", None)
    if reader is None:
        # 只注入授權、沒注入讀取器時，讀取器需要真實的授權閘道提供憑證
        assert isinstance(gateway, GoogleAuthGateway)
        reader = GoogleSheetsReader(gateway)
    activity = app.state.activity_service
    assert isinstance(activity, ActivityService)
    return ImportService(gateway, reader, activity, store, app.state.clock), gateway


def create_router(app: FastAPI) -> APIRouter:
    """建立 002 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務存入 `app.state.import_service`。

    Returns:
        含 8 個端點與 `/oauth/callback` 的 router。
    """
    router = APIRouter(tags=["guided-notes-import"])
    service, auth_gateway = _build_service(app)
    app.state.import_service = service

    def requester_for(code: str, token: str | None) -> Requester:
        activity = app.state.activity_service
        assert isinstance(activity, ActivityService)
        return activity.resolve_requester(code, token)

    def fail(
        request: Request, code: str, token: str | None, rejection: ImportRejection
    ) -> ApiError:
        """把拒絕轉成 `ApiError`；活動不存在時依 001 慣例（帶 token 回 410）。"""
        annotate_request_log(request, activity_code=code, result=rejection.value)
        if rejection is ImportRejection.ACTIVITY_NOT_FOUND and token:
            gone = RejectionReason.ACTIVITY_GONE
            return ApiError(gone.http_status, gone.value, gone.default_message)
        return ApiError(_STATUS[rejection], rejection.value, message_for(rejection))

    def ok(
        request: Request, code: str, body: JsonDict, version: int | None = None
    ) -> JsonDict:
        annotate_request_log(request, activity_code=code, result="OK", version=version)
        return body

    @router.post("/activities/{code}/import/auth/start")
    async def auth_start(
        request: Request, code: str, token: Token, body: EmptyBody | None = None
    ) -> JsonDict:
        """開始授權（#1）：回傳 Google 授權網址。"""
        code = normalize_code_input(code)
        result = await service.start_auth(code, requester_for(code, token))
        if not result.ok or result.value is None:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        return ok(request, code, {"authUrl": result.value})

    @router.get("/oauth/callback")
    async def oauth_callback(request: Request) -> RedirectResponse:
        """Google 導回（#2）：以 `state` 找回活動。

        `state` 無效、過期或重複使用時不交換 token。
        """
        query = request.query_params
        outcome = await auth_gateway.complete_authorization(
            query.get("state"), query.get("code"), query.get("error")
        )
        params = {"auth": outcome.status}
        if outcome.code:
            params = {"code": outcome.code, **params}
        annotate_request_log(
            request,
            activity_code=outcome.code,
            result=f"AUTH_{outcome.status.upper()}",
        )
        response = RedirectResponse(
            f"/teacher.html?{urlencode(params)}", status_code=302
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @router.get("/activities/{code}/import/auth/status")
    async def auth_status(request: Request, code: str, token: Token) -> JsonDict:
        """授權狀態（#3）。"""
        code = normalize_code_input(code)
        result = service.auth_status(code, requester_for(code, token))
        if not result.ok or result.value is None:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        return ok(request, code, {"authorized": result.value})

    @router.get("/activities/{code}/import/picker-config")
    async def picker_config(request: Request, code: str, token: Token) -> Response:
        """Picker 設定（#4）：短效 `drive.file` token，`no-store`，不寫入日誌。"""
        code = normalize_code_input(code)
        result = await service.picker_config(code, requester_for(code, token))
        if not result.ok or result.value is None:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        annotate_request_log(request, activity_code=code, result="OK")
        return JSONResponse(
            {
                "accessToken": result.value.access_token,
                "apiKey": result.value.api_key,
                "appId": result.value.app_id,
            },
            headers={"Cache-Control": "no-store"},
        )

    @router.post("/activities/{code}/import/source/inspect")
    async def inspect(
        request: Request, code: str, token: Token, body: InspectBody
    ) -> JsonDict:
        """檢視試算表（#5）：列出可見工作表與後端決定的 `autoSelectSheetId`。"""
        code = normalize_code_input(code)
        result = await service.inspect_spreadsheet(
            code, requester_for(code, token), body.spreadsheet_id
        )
        if not result.ok or result.value is None:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        info = result.value
        return ok(
            request,
            code,
            {
                "spreadsheetId": info.spreadsheet_id,
                "title": info.title,
                "sheets": [
                    {"sheetId": s.sheet_id, "title": s.title} for s in info.sheets
                ],
                "autoSelectSheetId": info.auto_select_sheet_id,
            },
        )

    @router.put("/activities/{code}/import/source")
    async def select_source(
        request: Request, code: str, token: Token, body: SourceBody
    ) -> JsonDict:
        """選定來源（#6）：驗證工作表屬於該試算表且可見後才保存。"""
        code = normalize_code_input(code)
        source = SourceRef(body.spreadsheet_id, body.sheet_id)
        result = await service.select_source(code, requester_for(code, token), source)
        if not result.ok or result.value is None:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        selected = result.value
        return ok(
            request,
            code,
            {
                "spreadsheetId": selected.source.spreadsheet_id,
                "sheetId": selected.source.sheet_id,
                "sheetTitle": selected.sheet_title,
            },
        )

    @router.post("/activities/{code}/import")
    async def import_sheet(
        request: Request,
        code: str,
        token: Token,
        key: IdempotencyKey,
        body: EmptyBody | None = None,
    ) -> Response:
        """匯入（#7）：使用已記住的來源；同一個 `Idempotency-Key` 回傳第一次的結果。"""
        code = normalize_code_input(code)
        outcome = await service.import_sheet(code, requester_for(code, token), key)
        if outcome.ok:
            return JSONResponse(
                ok(request, code, result_json(outcome), outcome.version)
            )
        rejection = outcome.rejection or ImportRejection.READ_FAILED
        if rejection is ImportRejection.VALIDATION_FAILED:
            annotate_request_log(request, activity_code=code, result=rejection.value)
            return JSONResponse(
                {
                    "error": {
                        "code": rejection.value,
                        "message": message_for(rejection),
                        "issues": [issue_json(i) for i in outcome.issues],
                    }
                },
                status_code=_STATUS[rejection],
            )
        raise fail(request, code, token, rejection)

    @router.get("/activities/{code}/import")
    async def get_import(request: Request, code: str, token: Token) -> JsonDict:
        """頁面重新整理後恢復預覽（#8）；沒有匯入過回 `{"imported": false}`。"""
        code = normalize_code_input(code)
        result = await service.get_import_result(code, requester_for(code, token))
        if not result.ok:
            raise fail(
                request, code, token, result.rejection or ImportRejection.READ_FAILED
            )
        if result.value is None:
            return ok(request, code, {"imported": False})
        return ok(request, code, result_json(result.value), result.value.version)

    return router


__all__ = ["create_router"]
