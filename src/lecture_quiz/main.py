"""組裝 FastAPI app：logging 設定、共用錯誤處理、子功能 router 與靜態檔。

啟動方式（只監聽本機，技術限制 1）::

    python -m lecture_quiz
    # 或
    uvicorn lecture_quiz.main:app --host 127.0.0.1 --port 8000

建議用 `python -m lecture_quiz`：它會讓 uvicorn 的日誌也輸出到 stdout（技術限制 3）。

擴充方式：每個子功能在 `create_app` 的「子功能 router」區塊加一行
`api.include_router(<能力>.create_router(app))`，詳見 `docs/DEVELOPMENT.md`。
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from lecture_quiz.adapters.clock import SupportsNow, SystemClock
from lecture_quiz.adapters.web import system
from lecture_quiz.adapters.web.common import (
    RequestLogMiddleware,
    install_error_handlers,
)

STATIC_DIR = Path(__file__).parent / "adapters" / "static"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """設定全域 logging：INFO 層級、只輸出到 stdout（技術限制 3）。"""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=LOG_FORMAT)


def create_app(clock: SupportsNow | None = None) -> FastAPI:
    """建立 FastAPI app。

    Args:
        clock: 時鐘；測試傳入 `FakeClock`，省略時使用 `SystemClock`。
            子功能從 `app.state.clock` 取得，不得自行讀取系統時鐘。

    Returns:
        已掛上共用錯誤處理、請求日誌、所有 API router 與靜態檔的 app。
    """
    app = FastAPI(title="Vibe Coding 課堂搶答系統", docs_url=None, redoc_url=None)
    app.state.clock = clock if clock is not None else SystemClock()
    install_error_handlers(app)
    app.add_middleware(RequestLogMiddleware)

    api = APIRouter(prefix="/api")
    # ── 子功能 router：每個子功能只加一行（順序不限）──
    api.include_router(system.create_router(app))
    # ── 子功能 router 結束 ──
    app.include_router(api)

    # WebSocket 路由（例如 001 的 /ws/activities/{code}）也要在掛載靜態檔之前加入。

    # 靜態檔必須最後掛載：它掛在 "/"，會攔下所有尚未匹配的路徑。
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


configure_logging()
app = create_app()
