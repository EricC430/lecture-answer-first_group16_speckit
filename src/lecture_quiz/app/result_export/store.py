"""記憶體存放：依活動代碼為 key（憲章原則 VII：不持久化，重啟即清空）。"""

import asyncio
from dataclasses import dataclass, field

from lecture_quiz.app.result_export.models import WriteAttempt


@dataclass
class ExportStore:
    """005 保存的寫回嘗試與每活動一把鎖。

    Attributes:
        attempts: 活動代碼 → 依嘗試編號遞增的嘗試清單。
        locks: 活動代碼 → 鎖（只序列化「檢查進行中並建立嘗試」，Google I/O 在鎖外）。
    """

    attempts: dict[str, list[WriteAttempt]] = field(default_factory=dict)
    locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    def lock(self, code: str) -> asyncio.Lock:
        """取得（必要時建立）該活動的鎖。

        Args:
            code: 活動代碼。

        Returns:
            該活動專屬的鎖。
        """
        lock = self.locks.get(code)
        if lock is None:
            lock = asyncio.Lock()
            self.locks[code] = lock
        return lock

    def next_id(self, code: str) -> int:
        """該活動下一個嘗試編號（從 1 起）。"""
        return len(self.attempts.get(code, ())) + 1

    def add_attempt(self, code: str, attempt: WriteAttempt) -> None:
        """新增一次嘗試。"""
        self.attempts.setdefault(code, []).append(attempt)

    def latest(self, code: str) -> WriteAttempt | None:
        """最近一次嘗試；沒有時為 `None`。"""
        items = self.attempts.get(code)
        return items[-1] if items else None

    def get(self, code: str, attempt_id: int) -> WriteAttempt | None:
        """依編號取得嘗試。"""
        for item in self.attempts.get(code, ()):
            if item.attempt_id == attempt_id:
                return item
        return None

    def replace(self, code: str, attempt: WriteAttempt) -> None:
        """以相同編號的新內容取代既有嘗試。"""
        items = self.attempts.get(code, [])
        for index, item in enumerate(items):
            if item.attempt_id == attempt.attempt_id:
                items[index] = attempt
                return
        raise KeyError(attempt.attempt_id)
