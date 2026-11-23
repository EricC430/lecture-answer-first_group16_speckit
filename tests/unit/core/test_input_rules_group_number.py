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
