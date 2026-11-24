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
from lecture_quiz.adapters.countdown import AsyncioCountdownScheduler
from lecture_quiz.adapters.web import (
    guided_notes_import,
    http_api,
    ranking_review,
    submission_api,
    system,
    ws_sync,
)
from lecture_quiz.adapters.web.common import (
    RequestLogMiddleware,
    install_api_fallback,
    install_error_handlers,
)
from lecture_quiz.app.activity.ports import CountdownScheduler
from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.guided_notes_import.ports import AuthGateway, SheetsReader
from lecture_quiz.app.ranking_review.service import RankingService
from lecture_quiz.app.ranking_review.store import ReviewStore
from lecture_quiz.app.round_submission.ports import QuestionShapeSource
from lecture_quiz.app.round_submission.service import SubmissionService
from lecture_quiz.app.round_submission.store import SubmissionStore

STATIC_DIR = Path(__file__).parent / "adapters" / "static"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """設定全域 logging：INFO 層級、只輸出到 stdout（技術限制 3）。"""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=LOG_FORMAT)


def _wire_activity(
    app: FastAPI,
    scheduler: CountdownScheduler | None,
    ws_auth_timeout: float,
    ws_ping_interval: float,
) -> None:
    """組裝 001 的活動服務：記憶體存放、倒數排程、WebSocket 推送。

    只建立物件，不啟動任何背景工作；倒數任務在開輪時才建立。
    """
    hub = ws_sync.WebSocketHub(ws_auth_timeout, ws_ping_interval)
    if scheduler is None:
        scheduler = AsyncioCountdownScheduler(app.state.clock)
    service = ActivityService(ActivityRegistry(), app.state.clock, scheduler, hub)
    scheduler.set_callback(service.on_deadline)
    hub.bind(service)
    app.state.activity_service = service
    app.state.sync_hub = hub


def _wire_submission(app: FastAPI, shapes: QuestionShapeSource | None) -> None:
    """組裝 003 的提交服務；每題子空格數來源：指定者 → 002 的匯入服務。

    `app.state.import_service` 由 002 的 `create_router(app)` 建立，所以本函式
    必須在它之後呼叫；`ImportService.blanks_per_question` 結構上符合
    `QuestionShapeSource`（003 研究 R6、002 契約「給 003」）。
    """
    if shapes is None:
        shapes = app.state.import_service
    app.state.question_shape_source = shapes
    app.state.submission_service = SubmissionService(
        app.state.activity_service, SubmissionStore(), shapes
    )


def _wire_ranking(app: FastAPI) -> None:
    """組裝 004 的順位服務；需要 001 的活動服務、003 的提交服務與 WebSocket 推送。"""
    app.state.ranking_service = RankingService(
        app.state.activity_service,
        app.state.submission_service,
        ReviewStore(),
        app.state.sync_hub,
    )


def create_app(
    clock: SupportsNow | None = None,
    scheduler: CountdownScheduler | None = None,
    import_auth_gateway: AuthGateway | None = None,
    import_sheets_reader: SheetsReader | None = None,
    ws_auth_timeout: float = 5.0,
    ws_ping_interval: float = 10.0,
    question_shape_source: QuestionShapeSource | None = None,
) -> FastAPI:
    """建立 FastAPI app。

    Args:
        clock: 時鐘；測試傳入 `FakeClock`，省略時使用 `SystemClock`。
            子功能從 `app.state.clock` 取得，不得自行讀取系統時鐘。
        scheduler: 倒數排程；測試傳入 `ManualScheduler`，省略時使用 asyncio 版本。
        import_auth_gateway: 002 的授權連接埠；測試傳入 Fake，
            省略時使用真實 Google 轉接器。
        import_sheets_reader: 002 的 Sheets 讀取連接埠；測試傳入 Fake，
            省略時使用真實轉接器。
        ws_auth_timeout: WebSocket 等待 auth 的秒數。
        ws_ping_interval: WebSocket ping 間隔秒數。
        question_shape_source: 每題子空格數來源（003）；測試傳入假來源，省略時
            使用 002 的 `ImportService`（最後一次成功匯入的結果）。

    Returns:
        已掛上共用錯誤處理、請求日誌、所有 API router、WebSocket 與靜態檔的 app。
    """
    app = FastAPI(title="Vibe Coding 課堂搶答系統", docs_url=None, redoc_url=None)
    app.state.clock = clock if clock is not None else SystemClock()
    install_error_handlers(app)
    app.add_middleware(RequestLogMiddleware)
    _wire_activity(app, scheduler, ws_auth_timeout, ws_ping_interval)
    app.state.import_auth_gateway = import_auth_gateway  # 002 的注入點（None = 真實）
    app.state.import_sheets_reader = import_sheets_reader

    api = APIRouter(prefix="/api")
    # ── 子功能 router：每個子功能只加一行（順序不限）──
    api.include_router(system.create_router(app))
    api.include_router(http_api.create_router(app))  # 001
    # 002 先建立 import_service，003 的格數來源才能指向它
    api.include_router(guided_notes_import.create_router(app))  # 002
    _wire_submission(app, question_shape_source)  # 003 的格數來源依賴 002，須在其後
    api.include_router(submission_api.create_router(app))  # 003
    _wire_ranking(app)  # 004 需要 001、003 的服務，須在 003 之後
    api.include_router(ranking_review.create_router(app))  # 004
    # ── 子功能 router 結束 ──
    app.include_router(api)
    install_api_fallback(app)  # 未定義的 /api 路徑一律 404

    # WebSocket 路由也要在掛載靜態檔之前加入。
    app.include_router(ws_sync.create_router(app.state.sync_hub))  # 001

    # 靜態檔必須最後掛載：它掛在 "/"，會攔下所有尚未匹配的路徑。
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


configure_logging()
app = create_app()
