"""核對判定（US4）。"""

import pytest

from lecture_quiz.core.result_export.models import OutcomeStatus
from lecture_quiz.core.result_export.reconcile import reconcile
from tests.unit.core.result_export.helpers import (
    cell,
    cur_empty,
    cur_other,
    cur_text,
)

EXPECTED = [
    (1, 1, cell(4, 7), "甲一"),
    (1, 2, cell(5, 7), "甲二"),
    (3, None, cell(8, 6), "=1+1"),
]


def test_all_match_is_success():
    """Scenario: US4-AS2：目標格全數符合預期 → SUCCESS。"""
    current = {c: cur_text(a) for _, _, c, a in EXPECTED}
    result = reconcile(EXPECTED, current)
    assert result.status is OutcomeStatus.SUCCESS
    assert all(c.matches for c in result.checks)


def test_none_match_is_failed():
    """Scenario: US4-AS2：全數不符（空、其他型別、不同文字）→ FAILED。"""
    current = {
        cell(4, 7): cur_empty(),
        cell(5, 7): cur_other("123"),
        cell(8, 6): cur_text("別的"),
    }
    assert reconcile(EXPECTED, current).status is OutcomeStatus.FAILED


def test_partial_is_pending_and_lists_mismatches():
    """Scenario: US4-AS2：部分符合 → PENDING，checks 標出不符的格。"""
    current = {
        cell(4, 7): cur_text("甲一"),
        cell(5, 7): cur_empty(),
        cell(8, 6): cur_text("=1+1"),
    }
    result = reconcile(EXPECTED, current)
    assert result.status is OutcomeStatus.PENDING
    assert [c.matches for c in result.checks] == [True, False, True]
    bad = result.checks[1]
    assert (bad.question_number, bad.sub_index) == (1, 2)
    assert bad.expected == "甲二" and bad.current_display == ""


def test_number_is_not_text_match_and_cells_missing_are_empty():
    """數字 123 與預期 "123" 視為不符；沒有回傳的格視為空。"""
    result = reconcile([(1, None, cell(0, 0), "123")], {cell(0, 0): cur_other("123")})
    assert result.status is OutcomeStatus.FAILED
    assert result.checks[0].current_display == "123"
    result = reconcile([(1, None, cell(0, 0), "x")], {})
    assert (
        result.status is OutcomeStatus.FAILED and result.checks[0].current_display == ""
    )


def test_checks_carry_expected_and_display_and_are_deterministic():
    """逐格含預期與目前內容；相同輸入輸出相同。"""
    current = {cell(4, 7): cur_text("甲一")}
    a = reconcile(EXPECTED, current)
    assert a == reconcile(EXPECTED, current)
    assert [c.expected for c in a.checks] == ["甲一", "甲二", "=1+1"]


def test_empty_expected_is_rejected():
    """沒有目標格時不應被呼叫（FR-006）。"""
    with pytest.raises(ValueError):
        reconcile([], {})
