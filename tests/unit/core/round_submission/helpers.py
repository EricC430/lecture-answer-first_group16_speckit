"""003 核心單元測試共用的資料與工廠函式。

兩份版面的格數配置（憲章原則 III）：
- `LAYOUT_A`：課程範本，4 題，前兩題各兩格、後兩題各一格。
- `LAYOUT_B`：另一份版面，5 題，含三格題組。
"""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from types import MappingProxyType

from lecture_quiz.core.round_submission.models import (
    RoundContext,
    Submission,
    SubmissionAttempt,
)

from tests.conftest import FAKE_CLOCK_START

LAYOUT_A: Mapping[int, int] = MappingProxyType({1: 2, 2: 2, 3: 1, 4: 1})
LAYOUT_B: Mapping[int, int] = MappingProxyType({1: 1, 2: 3, 3: 1, 4: 2, 5: 1})
CODE = "K7QH2M"
NOW = FAKE_CLOCK_START


def make_context(
    *,
    group_number: int = 1,
    round_number: int | None = 1,
    open_questions: Sequence[int] = (1, 2, 3, 4),
    accepting: bool = True,
    blanks: Mapping[int, int] = LAYOUT_A,
) -> RoundContext:
    """本輪資訊；預設為第 1 輪、版面 A、題 1～4 開放、仍在接受提交。"""
    return RoundContext(
        group_number=group_number,
        round_number=round_number,
        open_questions=tuple(open_questions),
        accepting=accepting,
        blanks_per_question=blanks,
    )


def make_attempt(
    question_number: object = 1,
    answers: object = ("答案一", "答案二"),
    round_number: object = 1,
) -> SubmissionAttempt:
    """學生送出的原始內容。"""
    answers_raw = list(answers) if isinstance(answers, tuple) else answers
    return SubmissionAttempt(
        round_number_raw=round_number,
        question_number_raw=question_number,
        answers_raw=answers_raw,
    )


def make_submission(
    *,
    round_number: int = 1,
    question_number: int = 1,
    group_number: int = 1,
    answers: tuple[str, ...] = ("答案一", "答案二"),
    offset_ms: int = 0,
    sequence: int = 1,
    received_at: datetime | None = None,
) -> Submission:
    """一筆已接受的提交；`offset_ms` 為相對 `NOW` 的毫秒數。"""
    return Submission(
        activity_code=CODE,
        round_number=round_number,
        question_number=question_number,
        group_number=group_number,
        answers=answers,
        received_at=received_at or NOW + timedelta(milliseconds=offset_ms),
        sequence=sequence,
    )
