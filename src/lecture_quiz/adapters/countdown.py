"""以 asyncio 任務實作倒數排程（`CountdownScheduler`）。

到期時以「截止時間」呼叫回呼；服務層再用 `max(clock.now(), deadline)` 當作 `now`
送進狀態機，避免計時器比牆上時鐘早幾毫秒觸發而關不了輪（PR #15 審查第 3 項）。
只在 `schedule` 時建立任務，匯入或建立 app 時不啟動任何背景工作。
"""

import asyncio
import logging
from datetime import datetime

from lecture_quiz.adapters.clock import SupportsNow
from lecture_quiz.app.activity.ports import DeadlineCallback

logger = logging.getLogger(__name__)


class AsyncioCountdownScheduler:
    """每個活動最多一個倒數任務；重新排程時取代舊任務。"""

    def __init__(self, clock: SupportsNow) -> None:
        """建立排程器。

        Args:
            clock: 用來計算距離截止還有多久的時鐘。
        """
        self._clock = clock
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._callback: DeadlineCallback | None = None

    def set_callback(self, callback: DeadlineCallback) -> None:
        """綁定到期回呼。

        Args:
            callback: `(活動代碼, 截止時間)` 的非同步函式。
        """
        self._callback = callback

    def schedule(self, code: str, deadline: datetime) -> None:
        """排程；同一活動已有排程時先取消舊的。

        Args:
            code: 活動代碼。
            deadline: 截止時間。
        """
        self.cancel(code)
        self._tasks[code] = asyncio.get_running_loop().create_task(
            self._wait_and_fire(code, deadline)
        )

    def cancel(self, code: str) -> None:
        """取消該活動的排程；沒有排程時不做事。

        Args:
            code: 活動代碼。
        """
        task = self._tasks.pop(code, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def _wait_and_fire(self, code: str, deadline: datetime) -> None:
        delay = (deadline - self._clock.now()).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        if self._tasks.get(code) is asyncio.current_task():
            del self._tasks[code]
        if self._callback is None:
            return
        try:
            await self._callback(code, deadline)
        except Exception:
            logger.exception("倒數回呼失敗 activity=%s", code)
