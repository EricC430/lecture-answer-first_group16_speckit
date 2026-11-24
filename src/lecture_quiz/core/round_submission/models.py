"""003 的核心資料結構（data-model.md）；全部不可變。"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType


def _freeze(mapping: Mapping[int, int]) -> Mapping[int, int]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class Submission:
    """一組在某一輪對某一題的第一筆有效提交；建立後不可修改，不含裝置 token。

    Attributes:
        activity_code: 活動代碼。
        round_number: 輪次編號。
        question_number: 題號。
        group_number: 組號（送出當下由後端判定，FR-012）。
        answers: 各子空格答案的原文，`answers[i]` 是第 i+1 格（Q-20）。
        received_at: 後端接收時間（FR-015）。
        sequence: 活動內嚴格遞增的接收序號（FR-016）；不回覆給學生。
    """

    activity_code: str
    round_number: int
    question_number: int
    group_number: int
    answers: tuple[str, ...]
    received_at: datetime
    sequence: int


@dataclass(frozen=True)
class SubmissionAttempt:
    """學生送出的原始內容；由 `SubmissionRules.decide` 驗證，被拒時不保存。

    Attributes:
        round_number_raw: 輪次識別的原始輸入。
        question_number_raw: 題號的原始輸入。
        answers_raw: 各格答案的原始輸入。
    """

    round_number_raw: object
    question_number_raw: object
    answers_raw: object


@dataclass(frozen=True)
class RoundContext:
    """`decide` 需要的本輪資訊；由服務層從 001 的本輪資訊與 002 的格數組成。

    Attributes:
        group_number: 提交者的組號。
        round_number: 目前輪次編號；還沒有輪次時為 `None`。
        open_questions: 本輪開放題。
        accepting: 是否仍接受提交（搶答中且未截止）。
        blanks_per_question: 題號 → 子空格數（來自 002 的成功匯入結果）。
    """

    group_number: int
    round_number: int | None
    open_questions: tuple[int, ...]
    accepting: bool
    blanks_per_question: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """把格數表轉成唯讀，避免呼叫端事後修改。"""
        object.__setattr__(
            self, "blanks_per_question", _freeze(self.blanks_per_question)
        )


@dataclass(frozen=True)
class SubmissionLedger:
    """一個活動的全部有效提交與下一個接收序號。

    Attributes:
        submissions: 依接受順序排列的提交。
        next_sequence: 下一筆被接受的提交要使用的序號（從 1 開始）。
    """

    submissions: tuple[Submission, ...] = ()
    next_sequence: int = 1

    def find(
        self, round_number: int, question_number: int, group_number: int
    ) -> Submission | None:
        """找某一輪某一題某一組的提交。

        Args:
            round_number: 輪次編號。
            question_number: 題號。
            group_number: 組號。

        Returns:
            提交；沒有時為 `None`。
        """
        for submission in self.submissions:
            if (
                submission.round_number == round_number
                and submission.question_number == question_number
                and submission.group_number == group_number
            ):
                return submission
        return None

    def for_round(self, round_number: int) -> tuple[Submission, ...]:
        """某一輪的全部提交（依接受順序）。

        Args:
            round_number: 輪次編號。

        Returns:
            該輪的提交。
        """
        return tuple(s for s in self.submissions if s.round_number == round_number)

    def with_added(self, submission: Submission) -> "SubmissionLedger":
        """加入一筆提交，回傳新的 ledger（原物件不變）。

        Args:
            submission: 新提交；`sequence` 應等於目前的 `next_sequence`。

        Returns:
            新的 ledger，`next_sequence` 加 1。
        """
        return SubmissionLedger(
            submissions=(*self.submissions, submission),
            next_sequence=self.next_sequence + 1,
        )


class DecisionKind(StrEnum):
    """判定結果的種類。"""

    ACCEPTED = "ACCEPTED"
    ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
    REJECTED = "REJECTED"


class SubmissionRejection(StrEnum):
    """提交被拒的原因；每個值對應一個 HTTP 狀態碼。"""

    ACTIVITY_GONE = "ACTIVITY_GONE"
    NOT_IN_GROUP = "NOT_IN_GROUP"
    STALE_ROUND = "STALE_ROUND"
    ROUND_CLOSED = "ROUND_CLOSED"
    QUESTION_NOT_OPEN = "QUESTION_NOT_OPEN"
    SHAPES_UNAVAILABLE = "SHAPES_UNAVAILABLE"
    INVALID_ANSWER = "INVALID_ANSWER"
    WRONG_BLANK_COUNT = "WRONG_BLANK_COUNT"
    BLANK_EMPTY = "BLANK_EMPTY"
    ANSWER_TOO_LONG = "ANSWER_TOO_LONG"

    @property
    def http_status(self) -> int:
        """對應的 HTTP 狀態碼。"""
        return _HTTP_STATUS[self]


_HTTP_STATUS = {
    SubmissionRejection.ACTIVITY_GONE: 410,
    SubmissionRejection.NOT_IN_GROUP: 403,
    SubmissionRejection.STALE_ROUND: 409,
    SubmissionRejection.ROUND_CLOSED: 409,
    SubmissionRejection.QUESTION_NOT_OPEN: 400,
    SubmissionRejection.SHAPES_UNAVAILABLE: 503,
    SubmissionRejection.INVALID_ANSWER: 400,
    SubmissionRejection.WRONG_BLANK_COUNT: 400,
    SubmissionRejection.BLANK_EMPTY: 400,
    SubmissionRejection.ANSWER_TOO_LONG: 400,
}


@dataclass(frozen=True)
class SubmissionDecision:
    """一次判定的結果。

    Attributes:
        kind: 接受、本組已送出或拒絕。
        submission: 接受時為新提交；本組已送出時為既有提交。
        rejection: 拒絕原因。
        blank_numbers: 有問題的格號（1 起算）：空格或超過字數。
        expected_blanks: 格數不符時，該題需要的格數。
    """

    kind: DecisionKind
    submission: Submission | None = None
    rejection: SubmissionRejection | None = None
    blank_numbers: tuple[int, ...] = ()
    expected_blanks: int | None = None
