"""US3：公平模式依固定題序處理，不依賴題數（憲章原則 III 的對應驗證）。"""

import pytest

from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.unit.core.ranking_review.helpers import LAYOUT_A, LAYOUT_B, cand, inp


def test_processing_follows_fixed_order_not_question_number():
    """T039（題序 3,1,2 時先處理題 3；FR-004、憲章原則 III）。"""
    data = inp(
        [cand(1, 3, 1, 1), cand(2, 3, 2, 2), cand(1, 1, 3, 3), cand(2, 1, 4, 4)],
        questions=(1, 2, 3),
        fair=True,
        baseline={1: 0, 2: 0},
    )
    result = RankingCalculator.recompute(data, (3, 1, 2))
    assert [r.question_number for r in result.rankings] == [3, 1, 2]
    assert result.ranking_of(3).success_group == 1
    assert result.ranking_of(1).success_group == 2  # 甲已有 1 次，乙優先


@pytest.mark.parametrize("layout", [LAYOUT_A, LAYOUT_B])
def test_fair_mode_works_for_both_layouts(layout):
    """T039（4 題與 5 題、含無提交題；憲章原則 III）。"""
    candidates = [cand(1, q, q, q) for q in layout if q != 3]
    candidates += [cand(2, q, q + 10, q + 20) for q in layout if q != 3]
    data = inp(candidates, questions=layout, fair=True, baseline={1: 0, 2: 0})
    result = RankingCalculator.recompute(data, layout)
    assert len(result.rankings) == len(layout)
    assert result.ranking_of(3).success_group is None
    assert result.ranking_of(3).entries == ()
    total = sum(result.wins.values())
    assert total == len(layout) - 1
    assert abs(result.wins.get(1, 0) - result.wins.get(2, 0)) <= 1
