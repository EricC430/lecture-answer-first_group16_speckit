"""US2：速度模式排名（FR-006、FR-009）。"""

from lecture_quiz.core.ranking_review.models import DisplayStatus, WinReason
from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import cand, inp


def _run(candidates, **kwargs):
    data = inp(candidates, **kwargs)
    order = QuestionOrder.compute(data.question_numbers, data.candidates)
    return RankingCalculator.recompute(data, order)


def test_same_group_fastest_on_two_questions_wins_both():
    """Scenario: US2-AS4 ↔ OpenSpec「同組最快回答兩題」。"""
    result = _run(
        [cand(1, 1, 1, 1), cand(1, 2, 2, 2), cand(2, 1, 3, 3), cand(2, 2, 4, 4)],
        questions=(1, 2),
    )
    for ranking in result.rankings:
        assert ranking.success_group == 1
        first, second = ranking.entries
        assert first.reason is WinReason.EARLIER_SUBMISSION
        assert second.rank == 2


def test_three_candidates_get_ranks_one_two_three_and_only_first_wins():
    """Scenario: US2-AS5。"""
    result = _run(
        [cand(1, 1, 3, 3), cand(2, 1, 1, 1), cand(3, 1, 2, 2)], questions=(1,)
    )
    ranking = result.rankings[0]
    assert [(e.group_number, e.rank) for e in ranking.entries] == [
        (2, 1),
        (3, 2),
        (1, 3),
    ]
    assert ranking.success_group == 2
    assert [e.display_status for e in ranking.entries] == [
        DisplayStatus.SUCCESS,
        DisplayStatus.FAILED,
        DisplayStatus.FAILED,
    ]


def test_equal_receive_time_is_decided_by_sequence():
    """Scenario: US2-AS6。"""
    result = _run([cand(1, 1, 5, 9), cand(2, 1, 5, 4)], questions=(1,))
    ranking = result.rankings[0]
    assert ranking.success_group == 2
    assert ranking.entries[0].reason is WinReason.BACKEND_ORDER


def test_speed_mode_ignores_success_counts():
    """Scenario: US2-AS7（甲基準 3、乙 0，甲較早 → 甲仍是搶答成功者）。"""
    result = _run(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2)],
        questions=(1,),
        fair=False,
        baseline={1: 3, 2: 0},
    )
    ranking = result.rankings[0]
    assert ranking.success_group == 1
    assert ranking.entries[0].reason is WinReason.EARLIER_SUBMISSION
    assert ranking.entries[0].count_at_processing is None


def test_question_without_candidates_has_no_success_group():
    result = _run([cand(1, 1, 1, 1)], questions=(1, 2))
    by_question = {r.question_number: r for r in result.rankings}
    assert by_question[2].success_group is None
    assert by_question[2].entries == ()


def test_sole_candidate_reason():
    result = _run([cand(1, 1, 1, 1)], questions=(1,))
    assert result.rankings[0].entries[0].reason is WinReason.SOLE_CANDIDATE


def test_wrong_candidate_has_no_rank_and_is_listed_after_ranked_ones():
    result = _run(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3)],
        questions=(1,),
        wrong=[(1, 1)],
    )
    ranking = result.rankings[0]
    assert ranking.success_group == 2
    assert [(e.group_number, e.rank) for e in ranking.entries] == [
        (2, 1),
        (3, 2),
        (1, None),
    ]
    assert ranking.entries[-1].display_status is DisplayStatus.WRONG
    assert ranking.entries[-1].reason is None


def test_wins_and_group_counts_follow_baseline():
    result = _run(
        [cand(1, 1, 1, 1), cand(2, 2, 2, 2)], questions=(1, 2), baseline={1: 4}
    )
    assert dict(result.wins) == {1: 1, 2: 1}
    assert dict(result.group_counts) == {1: 5, 2: 1}


def test_recompute_rejects_inconsistent_input():
    """輸入不變式（data-model）：違反時是程式錯誤，以 AssertionError 拒絕。"""
    import pytest

    data = inp([cand(1, 1, 1, 1), cand(1, 1, 2, 2)], questions=(1,))
    with pytest.raises(AssertionError):
        RankingCalculator.recompute(data, (1,))
    dup_seq = inp([cand(1, 1, 1, 5), cand(2, 1, 2, 5)], questions=(1,))
    with pytest.raises(AssertionError):
        RankingCalculator.recompute(dup_seq, (1,))
    outside = inp([cand(1, 9, 1, 1)], questions=(1,))
    with pytest.raises(AssertionError):
        RankingCalculator.recompute(outside, (1,))
    orphan_mark = inp([cand(1, 1, 1, 1)], questions=(1,), wrong=[(2, 1)])
    with pytest.raises(AssertionError):
        RankingCalculator.recompute(orphan_mark, (1,))
