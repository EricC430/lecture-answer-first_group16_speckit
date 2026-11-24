"""答案規則（Q-20：每格 ≤ 500 字、可換行、保存原文；研究 R8）。"""

import pytest

from lecture_quiz.core.round_submission import answer_rules
from lecture_quiz.core.round_submission.answer_rules import (
    MAX_ANSWER_CHARS,
    AnswerRules,
    InvalidAnswerError,
)
from lecture_quiz.core.round_submission.rules import SubmissionRejection


def _error(raw, expected):
    with pytest.raises(InvalidAnswerError) as info:
        AnswerRules.check(raw, expected)
    return info.value


def test_limit_is_a_module_constant():
    assert MAX_ANSWER_CHARS == 500
    assert answer_rules.MAX_ANSWER_CHARS == 500


def test_wrong_blank_count():
    """Scenario: US1-AS4（OpenSpec「題組少一格」：缺格、多格整筆拒絕）。"""
    for raw in (["甲"], ["甲", "乙", "丙"], []):
        error = _error(raw, 2)
        assert error.rejection is SubmissionRejection.WRONG_BLANK_COUNT
        assert error.expected_blanks == 2


def test_blank_cell_lists_every_empty_blank():
    """Scenario: US1-AS3（題組只有一格有內容，整筆拒絕並指出缺漏）。"""
    error = _error(["甲", "  "], 2)
    assert error.rejection is SubmissionRejection.BLANK_EMPTY
    assert error.blank_numbers == (2,)
    error = _error(["", "乙", "\t"], 3)
    assert error.blank_numbers == (1, 3)


@pytest.mark.parametrize("blank", [" ", "\u3000", "\t", "\n", " \u3000\t\r\n "])
def test_whitespace_only_is_blank(blank):
    """Scenario: US1-AS6（只含空白，含全形空白、Tab、換行，視為未填寫）。"""
    error = _error([blank], 1)
    assert error.rejection is SubmissionRejection.BLANK_EMPTY
    assert error.blank_numbers == (1,)


@pytest.mark.parametrize(
    "raw", ["甲", None, 3, {"0": "甲"}, ["甲", 2], [None], [["甲"]], [True]]
)
def test_non_string_answers_are_invalid(raw):
    assert _error(raw, 1).rejection is SubmissionRejection.INVALID_ANSWER


def test_length_limit():
    assert AnswerRules.check(["字" * 500], 1) == ("字" * 500,)
    error = _error(["字" * 501, "乙", "x" * 600], 3)
    assert error.rejection is SubmissionRejection.ANSWER_TOO_LONG
    assert error.blank_numbers == (1, 3)


def test_blank_reported_before_too_long():
    error = _error(["", "字" * 501], 2)
    assert error.rejection is SubmissionRejection.BLANK_EMPTY
    assert error.blank_numbers == (1,)


def test_original_text_is_kept():
    """保存原文：首尾空白與換行都保留，只在判空時忽略（Q-20）。"""
    raw = ["  第一行\n第二行  ", "\u3000答案\u3000"]
    assert AnswerRules.check(raw, 2) == ("  第一行\n第二行  ", "\u3000答案\u3000")
