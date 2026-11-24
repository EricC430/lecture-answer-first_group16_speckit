"""系統層級端點（健康檢查），也是子功能 router 寫法的最小範例。

子功能照同樣形式在 `adapters/web/<能力>.py` 提供 `create_router(app)`，
再到 `main.py` 的 `create_app` 加一行掛上。
"""

from fastapi import APIRouter, FastAPI


def create_router(app: FastAPI) -> APIRouter:
    """建立系統端點的 router。

    Args:
        app: 目前的 app；可由 `app.state.clock` 取得時鐘。

    Returns:
        含 `GET /health` 的 router（掛在 `/api` 之下）。
    """
    router = APIRouter(tags=["system"])

    @router.get("/health")
    async def health() -> dict[str, str]:
        """回傳服務狀態與伺服端時間，供冒煙測試確認後端已啟動。"""
        return {"status": "ok", "time": app.state.clock.now().isoformat()}

    return router
