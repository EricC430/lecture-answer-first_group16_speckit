"""003 的 HTTP API（contracts/http-api.md）：`POST /activities/{code}/submissions`。"""

from fastapi import APIRouter, FastAPI


def create_router(app: FastAPI) -> APIRouter:
    """建立 003 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.submission_service`。

    Returns:
        003 的 router。
    """
    return APIRouter(tags=["round-submission"])
