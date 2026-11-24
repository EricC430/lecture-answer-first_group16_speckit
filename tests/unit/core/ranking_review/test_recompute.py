"""US5：整輪重算（FR-015～FR-017、SC-002、SC-003）。"""

from dataclasses import replace

from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import cand, cross_question, inp


def _run(data, order=None):
    order = order or QuestionOrder.compute(data.question_numbers, data.candidates)
    return RankingCalculator.recompute(data, order), order


def accumulating_recompute(data, order, previous):
    """錯誤實作（負對照）：以上一版的暫算次數當起點，而不是開輪基準。"""
    return RankingCalculator.recompute(
        replace(data, baseline=dict(previous.group_counts)), order
    )


def test_marking_first_winner_flips_both_questions():
    """Scenario: US5-AS1 ↔ OpenSpec「判錯造成跨題勝者改變」。"""
    data = cross_question()
    before, order = _run(data)
    assert [r.success_group for r in before.rankings] == [1, 2]
    after, _ = _run(cross_question(wrong=[(1, 1)]), order)
    assert [r.success_group for r in after.rankings] == [2, 1]
    assert RankingCalculator.diff(before, after) == {1, 2}
    assert after.group_counts[1] == 1 and after.group_counts[2] == 1


def test_undo_returns_to_identical_result():
    """Scenario: US5-AS2。"""
    before, order = _run(cross_question())
    _run(cross_question(wrong=[(1, 1)]), order)
    again, _ = _run(cross_question(), order)
    assert again == before


def test_all_candidates_wrong_means_no_success_and_no_count():
    """Scenario: US5-AS3 ↔ OpenSpec「全部被判錯」。"""
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2)],
        questions=(1,),
        fair=True,
        baseline={1: 0, 2: 0},
        wrong=[(1, 1), (2, 1)],
    )
    result, _ = _run(data)
    assert result.rankings[0].success_group is None
    assert result.group_counts[1] == 0 and result.group_counts[2] == 0
    assert result.wins == {}


def test_mark_and_undo_sequence_returns_to_start():
    """Scenario: US5-AS4（SC-003）：判錯、撤銷數次後與最初逐題相同。"""
    start, order = _run(cross_question())
    steps = [
        [(1, 1)],
        [(1, 1), (2, 2)],
        [(2, 2)],
        [(1, 2), (2, 2)],
        [],
    ]
    result = start
    for marks in steps:
        result, _ = _run(cross_question(wrong=marks), order)
    assert result == start


def test_same_input_recomputed_100_times_is_identical():
    """SC-002。"""
    data = cross_question(wrong=[(1, 1)])
    first, order = _run(data)
    assert all(_run(data, order)[0] == first for _ in range(100))


def test_negative_control_accumulating_recompute_is_detected():
    """負對照：累加式錯誤實作在同一操作序列後與初始結果不同，正確實作相同。"""
    data = cross_question()
    start, order = _run(data)
    wrong_data = cross_question(wrong=[(1, 1)])
    current = start
    for d in (wrong_data, data):
        current = accumulating_recompute(d, order, current)
    assert current != start
    good = start
    for d in (wrong_data, data):
        good, _ = _run(d, order)
    assert good == start
