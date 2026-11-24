"""001 活動的 HTTP 端點（contracts/http-api.md）。

共用的錯誤格式、例外處理與請求日誌在 `adapters/web/common.py`；這裡只負責
把服務層的 `Outcome` 轉成 HTTP 回應，以及 `RejectionReason` → 狀態碼。
"""

from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictBool, StrictInt

from lecture_quiz.app.activity.ports import Outcome, Requester
from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.activity.snapshot_view import JsonDict

from .common import ApiError, annotate_request_log, bearer_token, idempotency_key

T = TypeVar("T")

ACTIVITY_NOT_FOUND = "ACTIVITY_NOT_FOUND"
ACTIVITY_NOT_FOUND_MESSAGE = "找不到這個活動代碼，請確認後再輸入。"

Token = Annotated[str | None, Depends(bearer_token)]
IdempotencyKey = Annotated[str | None, Depends(idempotency_key)]


class CreateActivityBody(BaseModel):
    """`POST /activities` 的本文。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # 原始值交給核心的 InputRules 驗證，錯誤時回 INVALID_MAX_GROUPS
    max_groups: JsonValue = Field(default=None, alias="maxGroups")


class JoinGroupBody(BaseModel):
    """`POST /activities/{code}/groups/join` 的本文。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    # 原始值交給核心的 InputRules 正規化，錯誤時回 INVALID_GROUP_NUMBER
    group_number: JsonValue = Field(default=None, alias="groupNumber")
    credential: JsonValue = None


class OpenRoundBody(BaseModel):
    """`POST /activities/{code}/rounds` 的本文。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    question_numbers: list[StrictInt] | None = Field(
        default=None, alias="questionNumbers"
    )
    fair_mode: StrictBool = Field(default=False, alias="fairMode")
    # 原始值交給核心的 InputRules 驗證，
    # 錯誤時回 INVALID_COUNTDOWN 而不是 INVALID_REQUEST
    countdown_seconds: JsonValue = Field(default=None, alias="countdownSeconds")


def unwrap(request: Request, code: str, token: str | None, outcome: Outcome[T]) -> T:
    """成功時取出值；失敗時轉成 `ApiError` 拋出。

    活動不存在時：帶 token 回 410 `ACTIVITY_GONE`（代表活動曾經存在，例如後端已重啟），
    不帶 token 回 404。

    Args:
        request: 目前的請求。
        code: 正規化後的活動代碼。
        token: 請求帶的 token。
        outcome: 服務層的結果。

    Returns:
        成功時的值。

    Raises:
        ApiError: 失敗時。
    """
    if outcome.ok and outcome.value is not None:
        return outcome.value
    reason = outcome.rejection
    assert reason is not None
    annotate_request_log(request, activity_code=code)
    if reason is RejectionReason.ACTIVITY_GONE and not token:
        raise ApiError(404, ACTIVITY_NOT_FOUND, ACTIVITY_NOT_FOUND_MESSAGE)
    raise ApiError(reason.http_status, reason.value, outcome.message)


def create_router(app: FastAPI) -> APIRouter:
    """建立 001 的 HTTP router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.activity_service`。

    Returns:
        001 的 router。
    """
    router = APIRouter(tags=["activity"])

    def service() -> ActivityService:
        svc = app.state.activity_service
        assert isinstance(svc, ActivityService)
        return svc

    def requester_for(code: str, token: str | None) -> Requester:
        return service().resolve_requester(code, token)

    def ok(request: Request, code: str, version: int, body: JsonDict) -> JsonDict:
        annotate_request_log(request, activity_code=code, result="OK", version=version)
        return body

    @router.post("/activities", status_code=201)
    async def create_activity(
        request: Request,
        token: Token,
        key: IdempotencyKey,
        body: CreateActivityBody | None = None,
    ) -> JsonDict:
        """建立活動（#1）；`token` 為這個瀏覽器上一個活動的老師 token（C7）。"""
        body = body or CreateActivityBody()
        outcome = await service().create(body.max_groups, token, key)
        if not outcome.ok or outcome.value is None:
            reason = outcome.rejection
            assert reason is not None
            raise ApiError(reason.http_status, reason.value, outcome.message)
        created = outcome.value
        return ok(
            request,
            created.code,
            created.version,
            {
                "code": created.code,
                "teacherToken": created.teacher_token,
                "maxGroups": created.max_groups,
                "version": created.version,
            },
        )

    @router.get("/activities/{code}/snapshot")
    async def get_snapshot(request: Request, code: str, token: Token) -> JsonDict:
        """取得依角色裁切的快照（#2）。"""
        code = normalize_code_input(code)
        outcome = service().snapshot(code, requester_for(code, token))
        snapshot = unwrap(request, code, token, outcome)
        return ok(request, code, snapshot.version, snapshot.to_json())

    @router.post("/activities/{code}/open-joining")
    async def open_joining(
        request: Request, code: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """開放加入（#12）：準備中 → 開放加入，須已匯入題目。"""
        code = normalize_code_input(code)
        outcome = await service().open_joining(code, requester_for(code, token), key)
        version = unwrap(request, code, token, outcome)
        return ok(request, code, version, {"version": version})

    @router.post("/activities/{code}/groups/join")
    async def join_group(
        request: Request,
        code: str,
        token: Token,
        key: IdempotencyKey,
        body: JoinGroupBody | None = None,
    ) -> JsonDict:
        """以組號加入組別（#3）；已是某組成員的裝置回 409 ALREADY_IN_GROUP。"""
        code = normalize_code_input(code)
        body = body or JoinGroupBody()
        outcome = await service().join(
            code,
            body.group_number,
            body.credential,
            requester_for(code, token),
            key,
        )
        joined = unwrap(request, code, token, outcome)
        return ok(
            request,
            code,
            joined.version,
            {
                "deviceToken": joined.device_token,
                "groupNumber": joined.group_number,
                "credential": joined.credential,
                "version": joined.version,
            },
        )

    @router.post("/activities/{code}/groups/leave")
    async def leave_group(
        request: Request, code: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """離開本組（#4）；搶答中回 409 NO_GROUP_SWITCH_DURING_ROUND。"""
        code = normalize_code_input(code)
        outcome = await service().leave_group(code, requester_for(code, token), key)
        version = unwrap(request, code, token, outcome)
        return ok(request, code, version, {"version": version})

    @router.delete("/activities/{code}/groups/{number}")
    async def delete_group(
        request: Request, code: str, number: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """刪除沒有提交紀錄的組別（#5）；組號原樣交給核心正規化。"""
        code = normalize_code_input(code)
        outcome = await service().delete_group(
            code, requester_for(code, token), number, key
        )
        version = unwrap(request, code, token, outcome)
        return ok(request, code, version, {"version": version})

    @router.post("/activities/{code}/rounds", status_code=201)
    async def open_round(
        request: Request,
        code: str,
        token: Token,
        key: IdempotencyKey,
        body: OpenRoundBody | None = None,
    ) -> JsonDict:
        """開輪（#6）。"""
        code = normalize_code_input(code)
        body = body or OpenRoundBody()
        outcome = await service().open_round(
            code,
            requester_for(code, token),
            tuple(body.question_numbers) if body.question_numbers is not None else None,
            body.fair_mode,
            body.countdown_seconds,
            key,
        )
        opened = unwrap(request, code, token, outcome)
        deadline = opened.deadline.isoformat() if opened.deadline else None
        return ok(
            request,
            code,
            opened.version,
            {
                "roundNumber": opened.round_number,
                "deadline": deadline,
                "version": opened.version,
            },
        )

    @router.post("/activities/{code}/rounds/current/close")
    async def close_round(
        request: Request, code: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """關輪（#7）；已關過時 `alreadyClosed` 為 true、版本不變。"""
        code = normalize_code_input(code)
        outcome = await service().close_round(code, requester_for(code, token), key)
        closed = unwrap(request, code, token, outcome)
        return ok(
            request,
            code,
            closed.version,
            {
                "roundNumber": closed.round_number,
                "version": closed.version,
                "alreadyClosed": closed.already_closed,
            },
        )

    @router.post("/activities/{code}/end")
    async def end(
        request: Request, code: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """結束活動（#9）。"""
        code = normalize_code_input(code)
        outcome = await service().end(code, requester_for(code, token), key)
        ended = unwrap(request, code, token, outcome)
        return ok(
            request,
            code,
            ended.version,
            {
                "version": ended.version,
                "unsolvedQuestions": list(ended.unsolved_questions),
            },
        )

    @router.post("/activities/{code}/cancel")
    async def cancel(
        request: Request, code: str, token: Token, key: IdempotencyKey
    ) -> JsonDict:
        """取消活動（#10）。"""
        code = normalize_code_input(code)
        outcome = await service().cancel(code, requester_for(code, token), key)
        version = unwrap(request, code, token, outcome)
        return ok(request, code, version, {"version": version})

    return router
