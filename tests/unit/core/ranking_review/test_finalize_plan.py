"""US6：`RoundReviewRules.finalize_plan`（FR-019、FR-020）。"""

from lecture_quiz.core.ranking_review.models import DisplayStatus
from lecture_quiz.core.ranking_review.review import RoundReview, RoundReviewRules
from tests.unit.core.ranking_review.helpers import cand, inp


def _plan(data, baseline=None):
    review = RoundReview.initial(1, data)
    return RoundReviewRules.finalize_plan(review, dict(baseline or data.baseline))


def test_plan_lists_solved_questions_increments_and_counts():
    """Scenario: US6-AS1（題組成功只算 1 次）。"""
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(1, 2, 3, 3)],
        questions=(1, 2, 3),
        baseline={1: 2, 2: 0},
    )
    plan = _plan(data)
    assert plan.solved_questions == {1, 2}
    assert dict(plan.success_increments) == {1: 2}
    assert dict(plan.final_counts) == {1: 4, 2: 0}
    assert plan.version == 1


def test_plan_rankings_are_final_status():
    """定案後名次 1 為 CORRECT（FR-033）。"""
    data = inp([cand(1, 1, 1, 1), cand(2, 1, 2, 2)], questions=(1,))
    statuses = [e.display_status for e in _plan(data).rankings[0].entries]
    assert statuses == [DisplayStatus.CORRECT, DisplayStatus.FAILED]


def test_no_submissions_means_empty_plan():
    """Scenario: US6-AS7（沒有提交）。"""
    plan = _plan(inp([], questions=(1, 2), baseline={1: 3}))
    assert plan.solved_questions == frozenset()
    assert dict(plan.success_increments) == {}
    assert dict(plan.final_counts) == {1: 3}


def test_all_wrong_means_empty_plan():
    """全被判錯 → 沒有成功題、沒有增量。"""
    data = inp([cand(1, 1, 1, 1)], questions=(1,), wrong=[(1, 1)])
    plan = RoundReviewRules.finalize_plan(RoundReview.initial(1, data), {1: 0})
    assert plan.solved_questions == frozenset()
    assert dict(plan.success_increments) == {}
