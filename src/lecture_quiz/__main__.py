"""以 `python -m lecture_quiz` 啟動後端，只監聽 127.0.0.1。

連接埠可用環境變數 `LECTURE_QUIZ_PORT` 指定，預設 8000。
會載入專案根目錄的 `.env`（002 的 Google 設定；`.env` 已被 `.gitignore` 排除）。
uvicorn 的日誌交給根 logger，統一輸出到 stdout；逐請求日誌由
`RequestLogMiddleware` 負責，所以關閉 uvicorn 的 access log（它會記錄查詢字串）。

按 Ctrl+C 後，uvicorn 會等所有連線結束才退出；頁面的 WebSocket 會自動重連，
可能讓後端一直等下去。`timeout_graceful_shutdown` 讓它最多等 3 秒，
就取消剩下的連線並退出。
"""

import os

import uvicorn

from lecture_quiz.main import configure_logging

GRACEFUL_SHUTDOWN_SECONDS = 3
ENV_FILE = ".env"  # 002：載入 Google 設定；不存在時 uvicorn 照常啟動


def main() -> None:
    """啟動 uvicorn（單一 worker，只監聽本機）。"""
    configure_logging()
    port = int(os.environ.get("LECTURE_QUIZ_PORT", "8000"))
    uvicorn.run(
        "lecture_quiz.main:app",
        host="127.0.0.1",
        port=port,
        log_config=None,
        access_log=False,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SECONDS,
        env_file=ENV_FILE,
    )


if __name__ == "__main__":
    main()
