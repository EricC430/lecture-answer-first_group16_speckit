"""US1：歷史成功次數基準（核心部分，FR-001）。"""

from lecture_quiz.core.ranking_review.ranking import RankingCalculator


def test_initial_counts_copies_baseline_and_does_not_mutate_input():
    """Scenario: US1-AS3（基準是開輪時保存的數字，重算不改動它）。"""
    baseline = {1: 1, 2: 0}
    counts = RankingCalculator.initial_counts(baseline, [1, 2])
    counts[1] += 5
    assert baseline == {1: 1, 2: 0}
    assert counts == {1: 6, 2: 0}


def test_group_missing_from_baseline_starts_at_zero():
    """Scenario: US1-AS4（中途加入、基準沒有紀錄的組別以 0 為起點）。"""
    counts = RankingCalculator.initial_counts({1: 2}, [1, 2, 3])
    assert counts == {1: 2, 2: 0, 3: 0}


def test_group_in_baseline_without_candidates_keeps_its_value():
    counts = RankingCalculator.initial_counts({1: 2, 9: 4}, [1])
    assert counts[9] == 4
