"""004 核心單元測試共用的資料與工廠函式。

兩組不同題數配置（憲章原則 III 在 004 的對應：核心不依賴固定題數）：
- `LAYOUT_A`：4 題。
- `LAYOUT_B`：5 題，題 3 沒有任何提交、題 5 為題組提交。
"""

from collections.abc import Iterable, Mapping

from lecture_quiz.core.ranking_review.models import Candidate, RankingInput
from tests.conftest import FAKE_CLOCK_START

LAYOUT_A: tuple[int, ...] = (1, 2, 3, 4)
LAYOUT_B: tuple[int, ...] = (1, 2, 3, 4, 5)
NOW = FAKE_CLOCK_START


def cand(group: int, question: int, second: float, seq: int) -> Candidate:
    """一筆候選：接收時間為固定起點加 `second` 秒，`seq` 為接收序號。"""
    from datetime import timedelta

    return Candidate(group, question, NOW + timedelta(seconds=second), seq)


def inp(
    candidates: Iterable[Candidate],
    *,
    questions: Iterable[int] = LAYOUT_A,
    fair: bool = False,
    baseline: Mapping[int, int] | None = None,
    wrong: Iterable[tuple[int, int]] = (),
) -> RankingInput:
    """建構 `RankingInput`；`wrong` 的元素是（組號, 題號）。"""
    return RankingInput(
        question_numbers=tuple(questions),
        fair_mode=fair,
        baseline=dict(baseline or {}),
        candidates=tuple(candidates),
        wrong_marks=frozenset(wrong),
    )


def fair_two_questions() -> RankingInput:
    """OpenSpec 公平分配兩題：甲乙基準皆 0，順序甲題一、甲題二、乙題一、乙題二。"""
    return inp(
        [cand(1, 1, 1, 1), cand(1, 2, 2, 2), cand(2, 1, 3, 3), cand(2, 2, 4, 4)],
        questions=(1, 2),
        fair=True,
        baseline={1: 0, 2: 0},
    )


def cross_question(wrong: Iterable[tuple[int, int]] = ()) -> RankingInput:
    """OpenSpec 跨題範例：甲乙基準皆 0，甲在兩題都先送出（公平模式）。"""
    return inp(
        [cand(1, 1, 1, 1), cand(1, 2, 2, 2), cand(2, 1, 3, 3), cand(2, 2, 4, 4)],
        questions=(1, 2),
        fair=True,
        baseline={1: 0, 2: 0},
        wrong=wrong,
    )
