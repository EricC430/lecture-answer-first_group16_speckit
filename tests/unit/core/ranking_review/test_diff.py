"""US4／US5：`diff` 只列出真正改變的題（FR-016）。"""

from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import cand, inp


def _result(wrong=()):
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(1, 2, 3, 3), cand(2, 2, 4, 4)],
        questions=(1, 2),
        wrong=wrong,
    )
    return RankingCalculator.recompute(
        data, QuestionOrder.compute(data.question_numbers, data.candidates)
    )


def test_only_changed_questions_are_listed():
    """Scenario: US5-AS5（只有題一變）。"""
    assert RankingCalculator.diff(_result(), _result(wrong=[(1, 1)])) == {1}


def test_non_winner_wrong_mark_is_still_affected():
    """對非搶答成功者判錯（有名次 → 無名次）仍列入。"""
    assert RankingCalculator.diff(_result(), _result(wrong=[(2, 2)])) == {2}


def test_identical_results_have_no_affected_questions():
    """沒有改變 → 空集合。"""
    assert RankingCalculator.diff(_result(), _result()) == frozenset()
