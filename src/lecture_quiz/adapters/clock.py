"""系統時鐘轉接器。

核心層不得讀取系統時鐘（技術限制 4），時間由外層透過這裡取得後傳入。
測試改用 `tests/conftest.py` 的 `FakeClock`。
"""

from datetime import UTC, datetime
from typing import Protocol


class SupportsNow(Protocol):
    """任何能提供「現在時間」的物件，例如 `SystemClock` 或測試用的 `FakeClock`。"""

    def now(self) -> datetime:
        """回傳有時區資訊的現在時間。

        Returns:
            有時區資訊的 `datetime`。
        """
        ...


class SystemClock:
    """以作業系統時鐘提供現在時間。"""

    def now(self) -> datetime:
        """回傳有時區資訊的現在時間（本機時區）。

        Returns:
            轉成本機時區、有時區資訊的 `datetime`。
        """
        return datetime.now(UTC).astimezone()
