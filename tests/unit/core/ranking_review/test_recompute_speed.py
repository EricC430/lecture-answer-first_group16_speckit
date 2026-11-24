"""US2：判錯後以已保存的題序重算，題序不動（FR-005，OpenSpec「最早提交被判錯」）。"""

from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import cand, inp


def test_earliest_submission_judged_wrong_keeps_question_order():
    """Scenario: US2-AS3 ↔ OpenSpec「最早提交被判錯」。"""
    candidates = [cand(1, 3, 1, 1), cand(2, 1, 5, 2), cand(2, 3, 6, 3)]
    data = inp(candidates, questions=(1, 2, 3))
    order = QuestionOrder.compute(data.question_numbers, data.candidates)
    assert order == (3, 1, 2)
    before = RankingCalculator.recompute(data, order)
    judged = inp(candidates, questions=(1, 2, 3), wrong=[(1, 3)])
    after = RankingCalculator.recompute(judged, order)
    assert after.order == order == (3, 1, 2)
    third = after.ranking_of(3)
    assert third is not None and third.success_group == 2
    first_entry = [e for e in third.entries if e.group_number == 1][0]
    assert first_entry.rank is None and first_entry.wrong
    assert before.ranking_of(3).success_group == 1


def test_recompute_does_not_recompute_order_from_marks():
    """題序由呼叫端傳入的已保存題序決定，不因判錯重新計算。"""
    candidates = [cand(1, 2, 1, 1), cand(1, 1, 2, 2)]
    data = inp(candidates, questions=(1, 2), wrong=[(1, 2)])
    result = RankingCalculator.recompute(data, (2, 1))
    assert result.order == (2, 1)
