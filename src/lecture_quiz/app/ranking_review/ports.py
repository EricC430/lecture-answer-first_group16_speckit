"""004 的連接埠與服務回傳型別（contracts/service-interfaces.md）。

服務不拋業務錯誤：失敗時 `ReviewOutcome.ok=False`、`rejection` 為 004 自己的
`ReviewRejection`（與 001 的 `RejectionReason` 分開，HTTP 狀態與訊息見 research R12）。
"""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from lecture_quiz.core.ranking_review.outcome import FinalizedResult
from lecture_quiz.core.ranking_review.review import ReviewRejection

T = TypeVar("T")


@dataclass(frozen=True)
class ReviewOutcome(Generic[T]):
    """004 服務方法的回傳值；業務錯誤不拋例外。

    Attributes:
        ok: 是否成功。
        value: 成功時的值。
        rejection: 失敗原因。
        message: 失敗時給使用者的中文訊息（不含堆疊、路徑、token）。
    """

    ok: bool
    value: T | None = None
    rejection: ReviewRejection | None = None
    message: str = ""


@dataclass(frozen=True)
class MarkResult:
    """判錯／撤銷的結果。

    Attributes:
        changed: 是否真的改變（重複判錯、重複撤銷為 `False`）。
        result_version: 該輪目前的結果版本。
        affected_questions: 這次變更影響的題號（`changed=False` 時為空）。
    """

    changed: bool
    result_version: int
    affected_questions: tuple[int, ...]


@dataclass(frozen=True)
class FinalizeResult:
    """確認定案的結果。

    Attributes:
        version: 001 定案後的活動狀態版本。
        result_version: 被確認的結果版本。
        already_finalized: 是否為對已定案同一版本的重複確認（冪等）。
    """

    version: int
    result_version: int
    already_finalized: bool


@dataclass(frozen=True)
class FinalizedRound:
    """已定案輪次的唯讀視圖（給 005）。

    Attributes:
        round_number: 輪次編號。
        result: 定案時保存的結果。
    """

    round_number: int
    result: FinalizedResult


class RankingReader(Protocol):
    """提供給 005 的唯讀介面：只含已定案的輪次，005 不得重新計算順位或勝負。"""

    def finalized_rounds(self, code: str) -> tuple[FinalizedRound, ...]:
        """已定案輪次，依輪次遞增。

        Args:
            code: 活動代碼。

        Returns:
            已定案輪次；沒有時為空 tuple。
        """
        ...
