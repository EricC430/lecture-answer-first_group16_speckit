"""004 的 HTTP 端點（contracts/http-api.md）：判錯／撤銷與確認定案。

路由由 US4（PUT judgement）與 US6（POST finalize）加入；讀取結果一律透過 001 的快照。
"""

from fastapi import APIRouter, FastAPI


def create_router(app: FastAPI) -> APIRouter:
    """建立 004 的 router（掛在 `/api` 之下）。

    Args:
        app: 目前的 app；服務在 `app.state.ranking_service`。

    Returns:
        004 的 router。
    """
    router = APIRouter(tags=["ranking-review"])
    return router
