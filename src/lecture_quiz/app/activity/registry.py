"""活動的記憶體存放區（研究 R5、R6；原則 VII 不使用資料庫）。

- 代碼 → `Activity`。
- 每個活動一把 `asyncio.Lock`。
- 每個活動的去重表：(身分雜湊, Idempotency-Key) → 原回應，最多 1000 筆，超過淘汰最舊的。
- 全域的「建立活動 key → 結果」表，同樣最多 1000 筆。
"""

import asyncio
from collections import OrderedDict
from typing import NamedTuple, TypeVar

from lecture_quiz.core.activity.models import Activity

MAX_PROCESSED = 1000
K = TypeVar("K")


class ProcessedKey(NamedTuple):
    """去重表的 key。

    Attributes:
        identity: 請求者身分（token 雜湊，或 `anonymous`）。
        idempotency_key: 前端送來的 `Idempotency-Key`。
    """

    identity: str
    idempotency_key: str


def _remember(table: "OrderedDict[K, object]", key: K, value: object) -> None:
    table[key] = value
    table.move_to_end(key)
    while len(table) > MAX_PROCESSED:
        table.popitem(last=False)


class ActivityRegistry:
    """只存在記憶體的活動表；後端重啟即清空。"""

    def __init__(self) -> None:
        """建立空的存放區。"""
        self._activities: dict[str, Activity] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._processed: dict[str, OrderedDict[ProcessedKey, object]] = {}
        self._created: OrderedDict[str, object] = OrderedDict()
        self.create_lock = asyncio.Lock()

    def get(self, code: str) -> Activity | None:
        """取得活動；不存在時回傳 `None`。

        Args:
            code: 活動代碼。

        Returns:
            活動或 `None`。
        """
        return self._activities.get(code)

    def put(self, activity: Activity) -> None:
        """新增或取代活動。

        Args:
            activity: 新狀態。
        """
        self._activities[activity.code] = activity

    def codes(self) -> set[str]:
        """存續中活動的代碼。

        Returns:
            代碼集合（複本）。
        """
        return set(self._activities)

    def lock(self, code: str) -> asyncio.Lock:
        """取得該活動的鎖（第一次使用時建立）。

        Args:
            code: 活動代碼。

        Returns:
            這個活動專用的 `asyncio.Lock`。
        """
        lock = self._locks.get(code)
        if lock is None:
            lock = self._locks[code] = asyncio.Lock()
        return lock

    def recall(self, code: str, key: ProcessedKey) -> object | None:
        """查詢去重表。

        Args:
            code: 活動代碼。
            key: 身分與 Idempotency-Key。

        Returns:
            第一次的回應；沒有時為 `None`。
        """
        return self._processed.get(code, OrderedDict()).get(key)

    def remember(self, code: str, key: ProcessedKey, response: object) -> None:
        """記錄一筆去重結果。

        Args:
            code: 活動代碼。
            key: 身分與 Idempotency-Key。
            response: 要在重送時原樣回傳的結果。
        """
        _remember(self._processed.setdefault(code, OrderedDict()), key, response)

    def processed_count(self, code: str) -> int:
        """該活動去重表目前的筆數。

        Args:
            code: 活動代碼。

        Returns:
            筆數。
        """
        return len(self._processed.get(code, ()))

    def recall_create(self, idempotency_key: str) -> object | None:
        """查詢建立活動的去重表。

        Args:
            idempotency_key: 前端送來的 key。

        Returns:
            第一次建立的結果；沒有時為 `None`。
        """
        return self._created.get(idempotency_key)

    def remember_create(self, idempotency_key: str, result: object) -> None:
        """記錄建立活動的結果。

        Args:
            idempotency_key: 前端送來的 key。
            result: 第一次建立的結果。
        """
        _remember(self._created, idempotency_key, result)
