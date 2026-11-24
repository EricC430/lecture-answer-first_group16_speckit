"""核心型別：不可變、顯示狀態推導、定案後的狀態轉換（共用基礎）。"""

import dataclasses
from datetime import timedelta

import pytest

from lecture_quiz.core.ranking_review.models import (
    DisplayStatus,
    QuestionRanking,
    RankEntry,
    RoundResult,
    WinReason,
    as_final,
    display_status,
)
from tests.unit.core.ranking_review.helpers import NOW, cand


def _entry(group, rank, wrong=False, reason=None):
    return RankEntry(group, rank, None, reason, wrong, display_status(rank, wrong))


def test_core_types_are_frozen():
    candidate = cand(1, 1, 0, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.group_number = 2  # type: ignore[misc]
    entry = _entry(1, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.rank = 2  # type: ignore[misc]
    result = RoundResult((1,), (), {1: 1}, {1: 1})
    with pytest.raises(TypeError):
        result.group_counts[1] = 9  # type: ignore[index]


def test_candidate_keeps_backend_received_time_only():
    candidate = cand(3, 2, 5, 9)
    assert candidate.received_at == NOW + timedelta(seconds=5)
    assert (candidate.group_number, candidate.question_number) == (3, 2)
    assert candidate.sequence == 9


@pytest.mark.parametrize(
    ("rank", "wrong", "expected"),
    [
        (None, True, DisplayStatus.WRONG),
        (1, False, DisplayStatus.SUCCESS),
        (2, False, DisplayStatus.FAILED),
        (7, False, DisplayStatus.FAILED),
    ],
)
def test_display_status(rank, wrong, expected):
    assert display_status(rank, wrong) is expected


def test_as_final_turns_success_into_correct_only():
    ranking = QuestionRanking(
        1,
        (
            _entry(1, 1, reason=WinReason.EARLIER_SUBMISSION),
            _entry(2, 2),
            _entry(3, None, wrong=True),
        ),
        1,
    )
    final = as_final([ranking])[0]
    statuses = [e.display_status for e in final.entries]
    assert statuses == [
        DisplayStatus.CORRECT,
        DisplayStatus.FAILED,
        DisplayStatus.WRONG,
    ]
    # 輸入不被修改
    assert ranking.entries[0].display_status is DisplayStatus.SUCCESS
    # 其他欄位不變
    assert final.success_group == 1
    assert final.entries[0].reason is WinReason.EARLIER_SUBMISSION
