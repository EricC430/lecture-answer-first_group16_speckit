"""US3：輪次、截止與排序由後端決定（`SubmissionRules.decide` 步驟 1～2、`order`）。"""

import random

import pytest

from lecture_quiz.core.round_submission.models import SubmissionLedger
from lecture_quiz.core.round_submission.rules import (
    DecisionKind,
    SubmissionRejection,
    SubmissionRules,
)
from tests.unit.core.round_submission.helpers import (
    CODE,
    NOW,
    make_attempt,
    make_context,
    make_submission,
)


def _decide(ledger, attempt, **context):
    return SubmissionRules.decide(ledger, make_context(**context), CODE, attempt, NOW)


@pytest.mark.parametrize("round_raw", [1, 3, "2", None, True, 2.0])
def test_stale_round(round_raw):
    """Scenario: US3-AS4（OpenSpec「舊輪次頁面提交」：輪次識別不是目前輪次）。"""
    decision = _decide(
        SubmissionLedger(), make_attempt(1, ("甲", "乙"), round_raw), round_number=2
    )
    assert decision.kind is DecisionKind.REJECTED
    assert decision.rejection is SubmissionRejection.STALE_ROUND
    attempt = make_attempt(1, ("甲", "乙"), round_raw)
    assert "輪次已更新，請重新整理" in SubmissionRules.describe(decision, attempt)


def test_no_round_yet_is_round_closed():
    """spec Edge Cases「非搶答中提交」：還沒有任何輪次 → 本輪尚未開始或已結束。"""
    attempt = make_attempt(1, ("甲", "乙"), 1)
    decision = _decide(
        SubmissionLedger(), attempt, round_number=None, open_questions=()
    )
    assert decision.rejection is SubmissionRejection.ROUND_CLOSED
    message = SubmissionRules.describe(decision, attempt)
    assert "本輪已結束" in message and "尚未開始" in message


def test_not_accepting_is_round_closed():
    """Scenario: US3-AS2、US3-AS3（已截止或老師已關輪）。"""
    attempt = make_attempt(1, ("甲", "乙"))
    decision = _decide(SubmissionLedger(), attempt, accepting=False)
    assert decision.rejection is SubmissionRejection.ROUND_CLOSED
    assert "本輪已結束" in SubmissionRules.describe(decision, attempt)


def test_check_priority():
    """研究 R10：舊輪次 > 本輪已結束 > 題號 > 本組已送出 > 內容。"""
    ledger = SubmissionLedger((make_submission(round_number=2),), next_sequence=2)
    bad = make_attempt(99, "不是陣列", 1)
    stale = _decide(ledger, bad, round_number=2, accepting=False)
    assert stale.rejection is SubmissionRejection.STALE_ROUND
    closed = _decide(ledger, make_attempt(99, "x", 2), round_number=2, accepting=False)
    assert closed.rejection is SubmissionRejection.ROUND_CLOSED
    # 已截止時即使本組已送出，也回本輪已結束
    already = _decide(
        ledger, make_attempt(1, ("a", "b"), 2), round_number=2, accepting=False
    )
    assert already.rejection is SubmissionRejection.ROUND_CLOSED


def test_order_by_received_at_then_sequence():
    """Scenario: US3-AS5（OpenSpec「同時間戳」：同一時間依接收序號）。"""
    subs = [
        make_submission(group_number=3, offset_ms=0, sequence=2),
        make_submission(group_number=1, offset_ms=0, sequence=1),
        make_submission(group_number=2, offset_ms=-5, sequence=3),
        make_submission(group_number=4, offset_ms=10, sequence=4),
    ]
    expected = (subs[2], subs[1], subs[0], subs[3])
    rng = random.Random(3)
    for _ in range(20):
        shuffled = subs[:]
        rng.shuffle(shuffled)
        ordered = SubmissionRules.order(shuffled)
        assert isinstance(ordered, tuple)
        assert ordered == expected
