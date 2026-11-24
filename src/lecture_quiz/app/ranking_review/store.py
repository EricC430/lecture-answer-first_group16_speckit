"""004 的記憶體存放區：審閱狀態、每活動一把鎖、快照快取（research R1、R14）。

後端重啟即清空（憲章原則 VII）。快取鍵含「是否定案」：定案不增加結果版本卻會改變
輸出（搶答成功 → 搶答正確、按鈕與前一組消失），所以旗標必須在鍵裡。
"""

import asyncio

from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.ranking_review.review import RoundReview

CacheKey = tuple[str, int, int, bool, str]


class ReviewStore:
    """活動代碼 → 各輪的 `RoundReview`，以及每活動一把 `asyncio.Lock`。"""

    def __init__(self) -> None:
        """建立空的存放區。"""
        self._reviews: dict[tuple[str, int], RoundReview] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._cache: dict[CacheKey, JsonDict] = {}

    def get(self, code: str, round_number: int) -> RoundReview | None:
        """取得某輪已保存的審閱狀態。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。

        Returns:
            審閱狀態；尚未保存時為 `None`。
        """
        return self._reviews.get((code, round_number))

    def put(self, code: str, review: RoundReview) -> None:
        """保存（或取代）某輪的審閱狀態。

        Args:
            code: 活動代碼。
            review: 審閱狀態。
        """
        self._reviews[(code, review.round_number)] = review

    def lock(self, code: str) -> asyncio.Lock:
        """該活動專屬的鎖；同一活動永遠回傳同一把。

        Args:
            code: 活動代碼。

        Returns:
            鎖。
        """
        found = self._locks.get(code)
        if found is None:
            found = asyncio.Lock()
            self._locks[code] = found
        return found

    def cache_get(
        self, code: str, round_number: int, version: int, final: bool, kind: str
    ) -> JsonDict | None:
        """取得快取的序列化結果。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。
            version: 結果版本。
            final: 是否定案。
            kind: 角色種類（`teacher` 或 `student`）。

        Returns:
            快取的 JSON；沒有時為 `None`。
        """
        return self._cache.get((code, round_number, version, final, kind))

    def cache_put(
        self,
        code: str,
        round_number: int,
        version: int,
        final: bool,
        kind: str,
        value: JsonDict,
    ) -> None:
        """寫入快取。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。
            version: 結果版本。
            final: 是否定案。
            kind: 角色種類。
            value: 序列化後的 JSON。
        """
        self._cache[(code, round_number, version, final, kind)] = value

    def drop(self, code: str) -> None:
        """清掉該活動的審閱狀態、鎖與快取。

        Args:
            code: 活動代碼。
        """
        self._reviews = {k: v for k, v in self._reviews.items() if k[0] != code}
        self._cache = {k: v for k, v in self._cache.items() if k[0] != code}
        self._locks.pop(code, None)
