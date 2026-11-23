"""提交判定（純函式，003 研究 R10、data-model.md「判定順序」）。"""

from dataclasses import dataclass
from enum import StrEnum

from lecture_quiz.core.round_submission.models import Submission


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


class SubmissionRules:
    """提交判定；US1～US3 逐步完成。"""

    @staticmethod
    def decide(*args: object, **kwargs: object) -> SubmissionDecision:
        """判定一筆提交（尚未實作，US1 起完成）。

        Args:
            *args: 未使用。
            **kwargs: 未使用。

        Raises:
            NotImplementedError: 尚未實作。
        """
        raise NotImplementedError
