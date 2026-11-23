"""開發用 seed API：在 002 合併前放入假題目，供 001 人工驗證（研究 R8）。

只在 `LECTURE_QUIZ_DEV_SEED=1`（或 `create_app(dev_seed=True)`）時掛載，只限老師。
002 合併後的第一個 PR 移除本檔、環境變數與 `tests/integration/test_dev_seed.py`。
"""

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.core.activity.snapshot_view import JsonDict

from .common import annotate_request_log
from .http_api import Token, unwrap

MAX_SEED_QUESTIONS = 50


class SeedBody(BaseModel):
    """`POST /dev/activities/{code}/seed-questions` 的本文。"""

    model_config = ConfigDict(extra="forbid")

    count: StrictInt = Field(ge=1, le=MAX_SEED_QUESTIONS)


def create_router(app: FastAPI) -> APIRouter:
    """建立開發用 seed router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.activity_service`。

    Returns:
        seed router。
    """
    router = APIRouter(prefix="/dev", tags=["dev"])

    @router.get("/status")
    async def status() -> dict[str, bool]:
        """讓老師頁判斷是否顯示「放入假題目」按鈕。"""
        return {"enabled": True}

    @router.post("/activities/{code}/seed-questions")
    async def seed_questions(
        request: Request, code: str, body: SeedBody, token: Token
    ) -> JsonDict:
        """放入題號 1..count（只限老師、只在準備中）。"""
        service: ActivityService = app.state.activity_service
        code = normalize_code_input(code)
        requester = service.resolve_requester(code, token)
        numbers = tuple(range(1, body.count + 1))
        outcome = await service.replace_questions(code, requester, numbers)
        version = unwrap(request, code, token, outcome)
        annotate_request_log(request, activity_code=code, result="OK", version=version)
        return {"version": version}

    return router
