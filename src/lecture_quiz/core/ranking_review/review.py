"""一輪的審閱狀態與判錯／定案的判定規則（data-model.md「判定與狀態」）。

核心只做「給定已查好的資料，回傳決定」：階段、身分等需要 001 活動資料的檢查在
服務層。時間資料只來自候選的 `received_at`。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum

from lecture_quiz.core.ranking_review.models import (
    RankingInput,
    RoundResult,
    freeze_mapping,
)
from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.outcome import FinalizedResult
from lecture_quiz.core.ranking_review.ranking import RankingCalculator


class ReviewRejection(StrEnum):
    """判錯、撤銷與定案的拒絕原因（research R12）；`http_status` 與預設訊息見下表。"""

    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_TEACHER = "NOT_TEACHER"
    ACTIVITY_NOT_FOUND = "ACTIVITY_NOT_FOUND"
    ROUND_NOT_FOUND = "ROUND_NOT_FOUND"
    SUBMISSION_NOT_FOUND = "SUBMISSION_NOT_FOUND"
    ROUND_STILL_OPEN = "ROUND_STILL_OPEN"
    NO_ROUND = "NO_ROUND"
    STALE_ROUND = "STALE_ROUND"
    RESULT_ALREADY_FINAL = "RESULT_ALREADY_FINAL"
    ACTIVITY_CANCELLED = "ACTIVITY_CANCELLED"
    STALE_RESULT_VERSION = "STALE_RESULT_VERSION"
    FINALIZE_REJECTED = "FINALIZE_REJECTED"

    @property
    def http_status(self) -> int:
        """對應的 HTTP 狀態碼（`FINALIZE_REJECTED` 實際沿用 001 的狀態碼）。"""
        return _HTTP_STATUS[self]

    @property
    def default_message(self) -> str:
        """給使用者看、可修正的中文訊息；不含堆疊、路徑、token。"""
        return _MESSAGES[self]


_HTTP_STATUS = {
    ReviewRejection.INVALID_REQUEST: 400,
    ReviewRejection.NOT_TEACHER: 403,
    ReviewRejection.ACTIVITY_NOT_FOUND: 404,
    ReviewRejection.ROUND_NOT_FOUND: 404,
    ReviewRejection.SUBMISSION_NOT_FOUND: 404,
    ReviewRejection.ROUND_STILL_OPEN: 409,
    ReviewRejection.NO_ROUND: 409,
    ReviewRejection.STALE_ROUND: 409,
    ReviewRejection.RESULT_ALREADY_FINAL: 409,
    ReviewRejection.ACTIVITY_CANCELLED: 409,
    ReviewRejection.STALE_RESULT_VERSION: 409,
    ReviewRejection.FINALIZE_REJECTED: 409,
}

_MESSAGES = {
    ReviewRejection.INVALID_REQUEST: "請求格式不正確，請檢查後再試。",
    ReviewRejection.NOT_TEACHER: "需要這個活動的老師身分才能操作。",
    ReviewRejection.ACTIVITY_NOT_FOUND: "找不到這個活動代碼，請確認後再輸入。",
    ReviewRejection.ROUND_NOT_FOUND: "找不到這一輪，請重新整理後再操作。",
    ReviewRejection.SUBMISSION_NOT_FOUND: "找不到這筆提交，請重新整理後再操作。",
    ReviewRejection.ROUND_STILL_OPEN: "本輪尚未關閉，無法判錯。",
    ReviewRejection.NO_ROUND: "目前沒有可判錯的輪次。",
    ReviewRejection.STALE_ROUND: "輪次已更新，請重新整理後再操作。",
    ReviewRejection.RESULT_ALREADY_FINAL: "本輪已定案，不能再修改。",
    ReviewRejection.ACTIVITY_CANCELLED: "活動已取消。",
    ReviewRejection.STALE_RESULT_VERSION: "結果已更新，請重新檢視後再確認。",
    ReviewRejection.FINALIZE_REJECTED: "定案未生效，請重新整理後再試。",
}


@dataclass(frozen=True)
class RoundReview:
    """一輪的審閱狀態。

    Attributes:
        round_number: 輪次編號。
        version: 結果版本，從 1 開始，只在實際變更時加 1（與 001 的狀態版本獨立）。
        wrong_marks: 被判錯的（組號, 題號）集合。
        result: 目前的整輪結果。
        affected: 最近一次實際變更影響的題號（初始為空）。
        replaced: 題號 → 依判錯順序保存的「被替換的搶答成功者」歷程（最後一位是最近
            一位；撤銷判錯時移出歷程以退回上一步；定案時清空；初始為空）。
        finalized: 定案時保存的結果；未定案為 `None`。
    """

    round_number: int
    version: int
    wrong_marks: frozenset[tuple[int, int]]
    result: RoundResult
    affected: frozenset[int] = frozenset()
    replaced: Mapping[int, tuple[int, ...]] = field(default_factory=dict)
    finalized: FinalizedResult | None = None

    def __post_init__(self) -> None:
        """把歷程轉成唯讀。"""
        object.__setattr__(self, "replaced", freeze_mapping(self.replaced))

    @staticmethod
    def initial(round_number: int, data: RankingInput) -> "RoundReview":
        """關輪後尚無判錯時的初始審閱狀態（版本 1）。

        在這裡決定一次題序並保存在 `result.order`，之後的重算都傳入這份題序。

        Args:
            round_number: 輪次編號。
            data: 整輪重算的輸入（`wrong_marks` 應為空）。

        Returns:
            版本 1 的審閱狀態。
        """
        order = QuestionOrder.compute(data.question_numbers, data.candidates)
        return RoundReview(
            round_number=round_number,
            version=1,
            wrong_marks=data.wrong_marks,
            result=RankingCalculator.recompute(data, order),
        )

    def with_finalized(self, finalized: FinalizedResult) -> "RoundReview":
        """附上定案結果（歷程清空）；其餘欄位不變。

        Args:
            finalized: 定案結果。

        Returns:
            新的審閱狀態。
        """
        return replace(self, finalized=finalized, replaced={})


@dataclass(frozen=True)
class MarkDecision:
    """判錯／撤銷的判定結果。

    Attributes:
        ok: 是否成功（含「沒有變化」）。
        changed: 是否真的改變；`False` 時 `review` 是原物件。
        review: 成功時的新（或原）審閱狀態。
        rejection: 失敗原因。
    """

    ok: bool
    changed: bool = False
    review: RoundReview | None = None
    rejection: ReviewRejection | None = None


class RoundReviewRules:
    """判錯、撤銷的判定規則（純函式）。"""

    @staticmethod
    def mark(
        review: RoundReview,
        data: RankingInput,
        group_number: int,
        question_number: int,
        wrong: bool,
    ) -> MarkDecision:
        """判錯或撤銷判錯一筆已被接受的提交，並整輪重算。

        判錯集合以 `review.wrong_marks` 為準（`data.wrong_marks` 會被忽略）；重算一律從
        開輪基準與**保存的**題序出發（FR-015），所以結果不依賴操作順序。

        Args:
            review: 目前的審閱狀態。
            data: 本輪的重算輸入（候選、基準、模式、題號）。
            group_number: 組號。
            question_number: 題號。
            wrong: `True` 為判錯、`False` 為撤銷。

        Returns:
            判定結果：沒有該筆提交 → `SUBMISSION_NOT_FOUND`；狀態已相同 → 成功但
            `changed=False`（原物件）；否則為版本加一的新狀態。
        """
        key = (group_number, question_number)
        known = any(
            c.group_number == group_number and c.question_number == question_number
            for c in data.candidates
        )
        if not known:
            return MarkDecision(False, rejection=ReviewRejection.SUBMISSION_NOT_FOUND)
        if (key in review.wrong_marks) == wrong:
            return MarkDecision(True, False, review)
        marks = review.wrong_marks | {key} if wrong else review.wrong_marks - {key}
        old_ranking = review.result.ranking_of(question_number)
        new_result = RankingCalculator.recompute(
            replace(data, wrong_marks=marks), review.result.order
        )
        history = list(review.replaced.get(question_number, ()))
        if wrong:
            if old_ranking is not None and old_ranking.success_group == group_number:
                history.append(group_number)
        elif group_number in history:
            history.remove(group_number)
        replaced = dict(review.replaced)
        if history:
            replaced[question_number] = tuple(history)
        else:
            replaced.pop(question_number, None)
        new = replace(
            review,
            version=review.version + 1,
            wrong_marks=marks,
            result=new_result,
            affected=RankingCalculator.diff(review.result, new_result),
            replaced=replaced,
        )
        return MarkDecision(True, True, new)
