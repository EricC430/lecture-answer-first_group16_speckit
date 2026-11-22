"""核心層：只能是純函式。

不得匯入 `lecture_quiz.app`、`lecture_quiz.adapters`、fastapi、starlette、asyncio、
socket、time，也不得讀取系統時鐘；時間一律由呼叫端傳入。
由 `tests/architecture/test_core_is_pure.py` 自動檢查。
"""
