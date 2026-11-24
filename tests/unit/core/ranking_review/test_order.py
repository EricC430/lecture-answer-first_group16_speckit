"""US2：固定題目處理順序（FR-004、FR-005）。"""

from lecture_quiz.core.ranking_review.order import QuestionOrder
from tests.unit.core.ranking_review.helpers import LAYOUT_A, LAYOUT_B, cand


def test_order_follows_earliest_accepted_submission_per_question():
    """Scenario: US2-AS1（第 3 題最早，其次第 1 題，無提交的第 2 題置後）。"""
    candidates = [
        cand(1, 3, 1, 1),
        cand(2, 1, 5, 2),
        cand(1, 1, 9, 3),
    ]
    assert QuestionOrder.compute((1, 2, 3), candidates) == (3, 1, 2)


def test_questions_without_submissions_go_last_sorted_by_number():
    """Scenario: US2-AS2。"""
    candidates = [cand(1, 3, 1, 1)]
    assert QuestionOrder.compute(LAYOUT_A, candidates) == (3, 1, 2, 4)


def test_order_uses_receive_sequence_when_times_are_equal():
    candidates = [cand(1, 2, 5, 7), cand(1, 1, 5, 4)]
    assert QuestionOrder.compute((1, 2), candidates) == (1, 2)


def test_order_does_not_depend_on_a_fixed_question_count():
    """兩組不同題數配置（A：4 題；B：5 題含無提交題與題組提交）。"""
    a = QuestionOrder.compute(
        LAYOUT_A, [cand(1, 4, 1, 1), cand(2, 2, 2, 2), cand(3, 1, 3, 3)]
    )
    b = QuestionOrder.compute(
        LAYOUT_B, [cand(1, 5, 1, 1), cand(2, 2, 2, 2), cand(3, 1, 3, 3)]
    )
    assert a == (4, 2, 1, 3)
    assert b == (5, 2, 1, 3, 4)
    assert sorted(a) == list(LAYOUT_A) and sorted(b) == list(LAYOUT_B)


def test_earliest_candidate_defines_order_regardless_of_later_candidates():
    candidates = [cand(2, 1, 9, 5), cand(1, 1, 2, 1), cand(3, 2, 4, 3)]
    assert QuestionOrder.compute((1, 2), candidates) == (1, 2)
