"""004 的 HTTP 端點（contracts/http-api.md）：判錯／撤銷與確認定案。

路由由 US4（PUT judgement）與 US6（POST finalize）加入；讀取結果一律透過 001 的快照。
"""

from typing import Annotated, TypeVar

from fastapi import APIRouter, FastAPI, Path, Request
from pydantic import BaseModel, ConfigDict, StrictBool

from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.ranking_review.ports import ReviewOutcome
from lecture_quiz.app.ranking_review.service import RankingService
from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.ranking_review.review import ReviewRejection

from .common import ApiError, annotate_request_log
from .http_api import ACTIVITY_NOT_FOUND, ACTIVITY_NOT_FOUND_MESSAGE, Token

T = TypeVar("T")

Positive = Annotated[int, Path(ge=1)]


class JudgementBody(BaseModel):
    """`PUT .../judgement` 的本文；多送的欄位（例如原因）一律忽略。"""

    model_config = ConfigDict(extra="ignore")

    wrong: StrictBool


def unwrap(
    request: Request, code: str, token: str | None, outcome: ReviewOutcome[T]
) -> T:
    """成功時取出值；失敗時轉成 `ApiError`。

    活動不存在時：帶 token 回 410 `ACTIVITY_GONE`（活動曾存在，例如後端重啟），
    不帶 token 回 404 `ACTIVITY_NOT_FOUND`（與 001 一致）。

    Args:
        request: 目前的請求。
        code: 正規化後的活動代碼。
        token: 請求帶的 token。
        outcome: 服務層結果。

    Returns:
        成功時的值。

    Raises:
        ApiError: 失敗時。
    """
    if outcome.ok and outcome.value is not None:
        return outcome.value
    reason = outcome.rejection
    assert reason is not None
    annotate_request_log(request, activity_code=code, result=reason.value)
    if reason is ReviewRejection.ACTIVITY_NOT_FOUND:
        if token:
            raise ApiError(410, "ACTIVITY_GONE", outcome.message)
        raise ApiError(404, ACTIVITY_NOT_FOUND, ACTIVITY_NOT_FOUND_MESSAGE)
    raise ApiError(reason.http_status, reason.value, outcome.message)


def create_router(app: FastAPI) -> APIRouter:
    """建立 004 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.ranking_service`。

    Returns:
        004 的 router。
    """
    router = APIRouter(tags=["ranking-review"])

    def service() -> RankingService:
        svc = app.state.ranking_service
        assert isinstance(svc, RankingService)
        return svc

    @router.put(
        "/activities/{code}/rounds/{round_number}/questions/{question_number}"
        "/groups/{group_number}/judgement"
    )
    async def judge(
        request: Request,
        code: str,
        round_number: Positive,
        question_number: Positive,
        group_number: Positive,
        body: JudgementBody,
        token: Token,
    ) -> JsonDict:
        """老師判錯或撤銷判錯（E1、E2）；免填原因。"""
        code = normalize_code_input(code)
        requester = app.state.activity_service.resolve_requester(code, token)
        action = service().mark_wrong if body.wrong else service().unmark_wrong
        outcome = await action(
            code, requester, round_number, question_number, group_number
        )
        result = unwrap(request, code, token, outcome)
        annotate_request_log(
            request,
            activity_code=code,
            result="OK",
            version=result.result_version,
        )
        return {
            "changed": result.changed,
            "resultVersion": result.result_version,
            "affectedQuestions": list(result.affected_questions),
        }

    return router
