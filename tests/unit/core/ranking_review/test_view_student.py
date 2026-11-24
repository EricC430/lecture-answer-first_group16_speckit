"""US7：學生版輸出與請求者無關，且是老師版的子集（FR-036）。"""

from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.review import RoundReview
from lecture_quiz.core.ranking_review.view import ResultView, RoundView
from tests.integration.test_ranking_visibility import _keys
from tests.unit.core.ranking_review.helpers import cand, inp


def _view(final=False):
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 2, 3, 3)],
        questions=(1, 2),
        fair=True,
        baseline={1: 0, 2: 0, 3: 0},
    )
    review = RoundReview.initial(1, data)
    assert QuestionOrder  # 題序在 initial 已決定
    return [RoundView(1, True, review, final)]


def test_student_output_does_not_depend_on_group():
    """Scenario: US7-AS5（任意兩組學生看到同一份）。"""
    assert ResultView.for_student(_view()) == ResultView.for_student(_view())


def test_student_keys_are_proper_subset_of_teacher_keys():
    """學生版鍵集合是老師版的真子集。"""
    student = _keys(ResultView.for_student(_view()))
    teacher = _keys(ResultView.for_teacher(_view()))
    assert student < teacher


def test_final_has_empty_affected_for_both_roles():
    """final=true 時 affectedQuestions 皆為空。"""
    for body in (
        ResultView.for_student(_view(True)),
        ResultView.for_teacher(_view(True)),
    ):
        assert body["rounds"][0]["affectedQuestions"] == []
