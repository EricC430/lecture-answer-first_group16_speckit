"""以 `python -m lecture_quiz` 啟動後端，只監聽 127.0.0.1。

連接埠可用環境變數 `LECTURE_QUIZ_PORT` 指定，預設 8000。
uvicorn 的日誌交給根 logger，統一輸出到 stdout；逐請求日誌由
`RequestLogMiddleware` 負責，所以關閉 uvicorn 的 access log（它會記錄查詢字串）。
"""

import os

import uvicorn

from lecture_quiz.main import configure_logging


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
    )


if __name__ == "__main__":
    main()
