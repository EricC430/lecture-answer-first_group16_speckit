"""T030：組號與憑證的輸入規則（US2、FR-006、研究 R9）。"""

import pytest

from lecture_quiz.core.activity.input_rules import InputRules, InvalidInputError
from lecture_quiz.core.activity.results import RejectionReason


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (3, 3),
        ("3", 3),
        (" 3 ", 3),
        ("03", 3),
        ("３", 3),
        ("０３", 3),
        ("　０３　", 3),
        (6, 6),
        (1, 1),
    ],
)
def test_accepts_half_and_full_width_digits(raw, expected):
    assert InputRules.normalize_group_number(raw, 6) == expected


@pytest.mark.parametrize(
    "raw",
    [0, 7, -1, 2.5, "2.5", "三", "3組", "", "　", "-1", "+3", None, True, [3]],
)
def test_rejects_invalid_group_numbers(raw):
    with pytest.raises(InvalidInputError) as exc:
        InputRules.normalize_group_number(raw, 6)
    assert exc.value.reason is RejectionReason.INVALID_GROUP_NUMBER


def test_normalize_credential():
    assert InputRules.normalize_credential(" q8mz3r ") == "Q8MZ3R"
    assert InputRules.normalize_credential(None) == ""
    assert InputRules.normalize_credential(123) == ""


@pytest.mark.parametrize("length", [4, 4300, 4301, 5000, 100_000])
def test_overlong_digit_string_is_invalid_not_crash(length):
    """超長的數字字串一律回 INVALID_GROUP_NUMBER，不得因 int() 位數上限丟出 ValueError
    （PR #15 第三次審查問題 1；FR-031、SC-008）。"""
    with pytest.raises(InvalidInputError) as exc:
        InputRules.normalize_group_number("9" * length, 99)
    assert exc.value.reason is RejectionReason.INVALID_GROUP_NUMBER


def test_overlong_fullwidth_digits_is_invalid():
    with pytest.raises(InvalidInputError):
        InputRules.normalize_group_number("９" * 5000, 99)


def test_leading_zeros_still_accepted_within_length():
    assert InputRules.normalize_group_number("007", 99) == 7
