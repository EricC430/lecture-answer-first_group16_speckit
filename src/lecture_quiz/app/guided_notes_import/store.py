"""記憶體存放：依活動代碼為 key（原則 VII：不持久化，重啟即清空）。"""

import asyncio
from dataclasses import dataclass, field

from lecture_quiz.app.guided_notes_import.models import (
    ImportOutcome,
    ImportRecord,
    SourceSelection,
)

IDEMPOTENCY_LIMIT = 1000
"""去重表上限；超過時淘汰最舊的。"""


@dataclass
class ImportStore:
    """002 保存的四類資料，彼此獨立。

    Attributes:
        sessions: 授權 session（形態由轉接層決定，應用層只看得到「是否已授權」）。
        selections: 選定的來源。
        records: 最後一次成功匯入的結果。
        locks: 每個活動一把匯入鎖（與 001 的活動鎖分開）。
        idempotent: `(活動代碼, Idempotency-Key)` 對應的第一次匯入結果。
    """

    sessions: dict[str, object] = field(default_factory=dict)
    selections: dict[str, SourceSelection] = field(default_factory=dict)
    records: dict[str, ImportRecord] = field(default_factory=dict)
    locks: dict[str, asyncio.Lock] = field(default_factory=dict)
    idempotent: dict[tuple[str, str], ImportOutcome] = field(default_factory=dict)

    def lock_for(self, code: str) -> asyncio.Lock:
        """取得（必要時建立）該活動的匯入鎖。

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

    def remember_outcome(self, code: str, key: str, outcome: ImportOutcome) -> None:
        """記住某個 `Idempotency-Key` 的第一次結果（超過上限時淘汰最舊的）。

        Args:
            code: 活動代碼。
            key: 去重用的 key。
            outcome: 第一次的結果。
        """
        self.idempotent[(code, key)] = outcome
        while len(self.idempotent) > IDEMPOTENCY_LIMIT:
            self.idempotent.pop(next(iter(self.idempotent)))
