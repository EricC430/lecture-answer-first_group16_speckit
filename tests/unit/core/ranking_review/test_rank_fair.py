"""US3：公平模式排名（FR-007、FR-008、FR-009）。"""

from lecture_quiz.core.ranking_review.models import WinReason
from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import cand, fair_two_questions, inp


def _run(data):
    order = QuestionOrder.compute(data.question_numbers, data.candidates)
    return RankingCalculator.recompute(data, order)


def test_fair_two_questions_split_between_groups():
    """Scenario: US3-AS1 ↔ OpenSpec「公平分配兩題」。"""
    result = _run(fair_two_questions())
    q1, q2 = result.rankings
    assert q1.success_group == 1
    assert q1.entries[0].reason is WinReason.EARLIER_SUBMISSION
    assert q2.success_group == 2
    assert q2.entries[0].reason is WinReason.FEWER_SUCCESSES


def test_equal_count_and_time_is_decided_by_sequence():
    """Scenario: US3-AS2 ↔ OpenSpec「完全同次數與同時間」。"""
    data = inp(
        [cand(1, 1, 5, 9), cand(2, 1, 5, 4)],
        questions=(1,),
        fair=True,
        baseline={1: 0, 2: 0},
    )
    ranking = _run(data).rankings[0]
    assert ranking.success_group == 2
    assert ranking.entries[0].reason is WinReason.BACKEND_ORDER


def test_lower_baseline_beats_earlier_submission():
    """Scenario: US3-AS3（甲基準 1 且較早，乙基準 0 → 乙成功）。"""
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2)],
        questions=(1,),
        fair=True,
        baseline={1: 1, 2: 0},
    )
    ranking = _run(data).rankings[0]
    assert ranking.success_group == 2
    assert ranking.entries[0].reason is WinReason.FEWER_SUCCESSES


def test_count_at_processing_reflects_earlier_wins_in_the_round():
    """Scenario: US3-AS4（處理題二時甲已有本輪暫算 1 次）。"""
    result = _run(fair_two_questions())
    q2 = result.rankings[1]
    by_group = {e.group_number: e.count_at_processing for e in q2.entries}
    assert by_group == {1: 1, 2: 0}
    q1 = result.rankings[0]
    assert {e.group_number: e.count_at_processing for e in q1.entries} == {1: 0, 2: 0}


def test_question_group_counts_once_not_per_blank():
    """Scenario: US3-AS5（題組一筆提交成功只加 1 次）。"""
    data = inp([cand(1, 1, 1, 1)], questions=(1,), fair=True, baseline={1: 2})
    result = _run(data)
    assert result.wins == {1: 1}
    assert result.group_counts[1] == 3


def test_only_first_place_count_increases():
    """Scenario: US3-AS6（三個候選只有第一名成功）。"""
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3)],
        questions=(1,),
        fair=True,
        baseline={1: 0, 2: 0, 3: 0},
    )
    result = _run(data)
    assert result.group_counts[1] == 1
    assert result.group_counts[2] == 0
    assert result.group_counts[3] == 0


def test_sole_candidate_reason():
    """理由表：只有一個候選 → SOLE_CANDIDATE。"""
    data = inp([cand(1, 1, 1, 1)], questions=(1,), fair=True)
    assert _run(data).rankings[0].entries[0].reason is WinReason.SOLE_CANDIDATE


def test_later_entry_reason_compares_with_previous_rank():
    """理由表：第 2 名起與前一名比較（次數不同 → FEWER_SUCCESSES，同次數 → 時間）。"""
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3)],
        questions=(1,),
        fair=True,
        baseline={1: 0, 2: 0, 3: 1},
    )
    entries = _run(data).rankings[0].entries
    assert [e.group_number for e in entries] == [1, 2, 3]
    assert entries[1].reason is WinReason.EARLIER_SUBMISSION
    assert entries[2].reason is WinReason.FEWER_SUCCESSES
