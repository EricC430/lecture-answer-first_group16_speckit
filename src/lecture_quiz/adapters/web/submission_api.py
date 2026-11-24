"""003 的 HTTP API（contracts/http-api.md）：`POST /activities/{code}/submissions`。

- 所屬組別一律由後端依裝置 token 判定；本文多送的欄位（前端時間、自稱的組號）一律
  忽略（US3-AS7）。
- `roundNumber`、`questionNumber`、`answers` 原樣交給核心判定，型別錯誤也由核心
  回覆可修正的訊息；只有本文不是 JSON 物件或缺欄位時回 400 `INVALID_REQUEST`。
- 回應不含接收序號（序號跨組遞增，回覆給學生會洩漏他組進度；spec FR-010）。
"""

from fastapi import APIRouter, FastAPI, Request, Response
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.round_submission.service import SubmissionService
from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.round_submission.models import (
    DecisionKind,
    Submission,
    SubmissionAttempt,
)
from lecture_quiz.core.round_submission.rules import SubmissionRules

from .common import ApiError, annotate_request_log
from .http_api import Token


class SubmitBody(BaseModel):
    """`POST /activities/{code}/submissions` 的本文。"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    round_number: JsonValue = Field(alias="roundNumber")
    question_number: JsonValue = Field(alias="questionNumber")
    answers: JsonValue


def submission_json(submission: Submission) -> JsonDict:
    """學生與老師都可看的提交內容（不含接收序號）。

    Args:
        submission: 提交。

    Returns:
        JSON 格式的提交。
    """
    return {
        "roundNumber": submission.round_number,
        "questionNumber": submission.question_number,
        "groupNumber": submission.group_number,
        "answers": list(submission.answers),
        "receivedAt": submission.received_at.isoformat(timespec="milliseconds"),
    }


def create_router(app: FastAPI) -> APIRouter:
    """建立 003 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.submission_service`。

    Returns:
        003 的 router。
    """
    router = APIRouter(tags=["round-submission"])

    def service() -> SubmissionService:
        svc = app.state.submission_service
        assert isinstance(svc, SubmissionService)
        return svc

    @router.post("/activities/{code}/submissions", status_code=201)
    async def submit(
        request: Request,
        response: Response,
        code: str,
        body: SubmitBody,
        token: Token,
    ) -> JsonDict:
        """送出一題的答案（S1）；本組已送出時回 200 與既有提交。"""
        code = normalize_code_input(code)
        attempt = SubmissionAttempt(
            body.round_number, body.question_number, body.answers
        )
        outcome = await service().submit(code, token or "", attempt)
        decision = outcome.value
        assert decision is not None
        if decision.kind is DecisionKind.REJECTED:
            assert decision.rejection is not None
            annotate_request_log(request, activity_code=code)
            raise ApiError(
                decision.rejection.http_status,
                decision.rejection.value,
                SubmissionRules.describe(decision, attempt),
            )
        assert decision.submission is not None
        if decision.kind is DecisionKind.ALREADY_SUBMITTED:
            response.status_code = 200
            annotate_request_log(
                request, activity_code=code, result="ALREADY_SUBMITTED"
            )
            return {
                "result": "alreadySubmitted",
                "message": SubmissionRules.describe(decision, attempt),
                "submission": submission_json(decision.submission),
            }
        annotate_request_log(request, activity_code=code, result="OK")
        return {
            "result": "accepted",
            "submission": submission_json(decision.submission),
        }

    return router
