"""US1：依任意順序完整提交（`SubmissionRules.decide`）。"""

from lecture_quiz.core.round_submission.models import SubmissionLedger
from lecture_quiz.core.round_submission.rules import (
    DecisionKind,
    SubmissionRejection,
    SubmissionRules,
)
from tests.unit.core.round_submission.helpers import (
    CODE,
    LAYOUT_B,
    NOW,
    make_attempt,
    make_context,
)


def _decide(ledger, attempt, **context):
    return SubmissionRules.decide(ledger, make_context(**context), CODE, attempt, NOW)


def test_any_order_is_accepted():
    """Scenario: US1-AS1（OpenSpec「不同順序作答」：先題 2 再題 1 都接受）。"""
    ledger = SubmissionLedger()
    second = _decide(ledger, make_attempt(2, ("乙一", "乙二")), open_questions=(1, 2))
    assert second.kind is DecisionKind.ACCEPTED
    assert second.submission.question_number == 2
    assert second.submission.sequence == 1
    ledger = ledger.with_added(second.submission)
    first = _decide(ledger, make_attempt(1, ("甲一", "甲二")), open_questions=(1, 2))
    assert first.kind is DecisionKind.ACCEPTED
    assert first.submission.sequence == 2
    assert first.submission.received_at == NOW
    assert first.submission.activity_code == CODE
    assert first.submission.group_number == 1
    assert first.submission.round_number == 1


def test_partial_set_leaves_others_open():
    """Scenario: US1-AS2（只交兩題，其餘仍可提交）。"""
    ledger = SubmissionLedger()
    for question, answers in ((3, ("丙",)), (1, ("甲", "乙"))):
        decision = _decide(ledger, make_attempt(question, answers))
        assert decision.kind is DecisionKind.ACCEPTED
        ledger = ledger.with_added(decision.submission)
    later = _decide(ledger, make_attempt(4, ("丁",)))
    assert later.kind is DecisionKind.ACCEPTED


def test_question_not_open_or_unknown():
    """Scenario: US1-AS5（非本輪題或不存在的題號整筆拒絕，不消耗機會）。"""
    ledger = SubmissionLedger()
    for question in (3, 99, "1", None, True, 1.0):
        decision = _decide(
            ledger, make_attempt(question, ("丙",)), open_questions=(1, 2)
        )
        assert decision.kind is DecisionKind.REJECTED, question
        assert decision.rejection is SubmissionRejection.QUESTION_NOT_OPEN
        assert decision.submission is None


def test_open_question_without_shape_is_not_open():
    decision = _decide(
        SubmissionLedger(),
        make_attempt(5, ("戊",)),
        open_questions=(1, 5),
    )
    assert decision.rejection is SubmissionRejection.QUESTION_NOT_OPEN


def test_rejected_attempt_does_not_consume_chance():
    """Scenario: US1-AS3（少一格被拒後，同題仍可再交一次；FR-005）。"""
    ledger = SubmissionLedger()
    rejected = _decide(ledger, make_attempt(1, ("甲", "")))
    assert rejected.kind is DecisionKind.REJECTED
    assert rejected.rejection is SubmissionRejection.BLANK_EMPTY
    assert rejected.blank_numbers == (2,)
    accepted = _decide(ledger, make_attempt(1, ("甲", "乙")))
    assert accepted.kind is DecisionKind.ACCEPTED
    assert accepted.submission.sequence == 1


def test_wrong_count_reports_expected():
    """Scenario: US1-AS4。"""
    decision = _decide(SubmissionLedger(), make_attempt(1, ("甲",)))
    assert decision.rejection is SubmissionRejection.WRONG_BLANK_COUNT
    assert decision.expected_blanks == 2


def test_nonsense_answer_is_accepted_as_text():
    """Scenario: US1-AS7（系統不判斷正誤，非空白即接受並保存原文）。"""
    answers = ("香蕉 <b>?</b>", "  42  ")
    decision = _decide(SubmissionLedger(), make_attempt(1, answers))
    assert decision.kind is DecisionKind.ACCEPTED
    assert decision.submission.answers == answers


def test_layout_b_three_blank_group():
    """兩份版面（原則 III、SC-009）：版面 B 題 2 需要 3 格。"""
    ledger = SubmissionLedger()
    context = {"blanks": LAYOUT_B, "open_questions": (1, 2, 3, 4, 5)}
    two = _decide(ledger, make_attempt(2, ("一", "二")), **context)
    assert two.rejection is SubmissionRejection.WRONG_BLANK_COUNT
    assert two.expected_blanks == 3
    three = _decide(ledger, make_attempt(2, ("一", "二", "三")), **context)
    assert three.kind is DecisionKind.ACCEPTED
