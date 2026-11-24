"""US2：每組每題每輪只算第一筆（`SubmissionRules.decide` 步驟 4）。"""

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


@pytest.mark.parametrize(
    "answers",
    [
        ("新一", "新二"),
        ("答案一", "答案二"),
        ("只有一格",),
        ("甲", ""),
        ("字" * 501, "乙"),
        "不是陣列",
    ],
)
def test_existing_submission_wins_regardless_of_content(answers):
    """Scenario: US2-AS4（已有提交時不論內容是否有效都回本組已送出、不覆蓋）。"""
    original = make_submission(answers=("答案一", "答案二"), sequence=1)
    ledger = SubmissionLedger((original,), next_sequence=2)
    decision = _decide(ledger, make_attempt(1, answers))
    assert decision.kind is DecisionKind.ALREADY_SUBMITTED
    assert decision.submission is original
    assert decision.rejection is None
    assert ledger.submissions == (original,) and ledger.next_sequence == 2


def test_question_check_comes_before_already_submitted():
    """研究 R10：題號不在本輪開放時，先回題號錯誤。"""
    ledger = SubmissionLedger((make_submission(question_number=1),), next_sequence=2)
    decision = _decide(ledger, make_attempt(1, ("甲", "乙")), open_questions=(2,))
    assert decision.rejection is SubmissionRejection.QUESTION_NOT_OPEN


def test_invalid_then_valid_is_accepted():
    """Scenario: US2-AS5（先無效被拒不消耗機會，再有效即接受）。"""
    ledger = SubmissionLedger()
    first = _decide(ledger, make_attempt(1, ("甲", "  ")))
    assert first.kind is DecisionKind.REJECTED
    second = _decide(ledger, make_attempt(1, ("甲", "乙")))
    assert second.kind is DecisionKind.ACCEPTED
    assert second.submission.sequence == 1


def test_next_round_gives_a_new_chance():
    """Scenario: US2-AS3（OpenSpec「下一輪重新作答」：第 2 輪題 1 再開可再送）。"""
    round_one = make_submission(round_number=1, question_number=1, sequence=1)
    ledger = SubmissionLedger((round_one,), next_sequence=2)
    decision = _decide(
        ledger,
        make_attempt(1, ("再一", "再二"), round_number=2),
        round_number=2,
        open_questions=(1,),
    )
    assert decision.kind is DecisionKind.ACCEPTED
    assert decision.submission.round_number == 2
    assert decision.submission.sequence == 2
    assert ledger.submissions == (round_one,)


def test_other_group_is_not_affected():
    """他組已送同題不影響本組。"""
    ledger = SubmissionLedger((make_submission(group_number=2),), next_sequence=2)
    decision = _decide(ledger, make_attempt(1, ("甲", "乙")), group_number=1)
    assert decision.kind is DecisionKind.ACCEPTED
    assert decision.submission.group_number == 1


def test_describe_already_submitted():
    ledger = SubmissionLedger((make_submission(),), next_sequence=2)
    attempt = make_attempt(1, ("x", "y"))
    decision = _decide(ledger, attempt)
    assert "本組已送出" in SubmissionRules.describe(decision, attempt)
