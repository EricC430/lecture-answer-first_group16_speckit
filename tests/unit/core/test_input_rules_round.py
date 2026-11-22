"""T041：開輪輸入規則（倒數秒數、選題）。"""

import pytest

from lecture_quiz.core.activity.input_rules import InputRules, InvalidInputError
from lecture_quiz.core.activity.results import RejectionReason


@pytest.mark.parametrize("raw", [None, 1, 60, 3600])
def test_valid_countdown(raw):
    assert InputRules.validate_countdown(raw) == raw


@pytest.mark.parametrize(
    "raw", [0, -1, 3601, 2.5, 10.0, "10", "", True, False, [5], {"s": 5}]
)
def test_invalid_countdown(raw):
    """Scenario: US3-AS6

    倒數秒數為 0、負數、小數、非數字、空白或大於 3600 時拒絕；1 與 3600 可以。
    """
    with pytest.raises(InvalidInputError) as exc:
        InputRules.validate_countdown(raw)
    assert exc.value.reason is RejectionReason.INVALID_COUNTDOWN
    assert exc.value.reason.default_message == "倒數秒數須為 1～3600 的整數。"


def test_selection_none_means_all_unsolved_in_import_order():
    assert InputRules.validate_selection(None, (4, 1, 2, 3), frozenset({2})) == (
        4,
        1,
        3,
    )


def test_selection_keeps_import_order():
    assert InputRules.validate_selection((3, 1), (1, 2, 3, 4), frozenset()) == (1, 3)


@pytest.mark.parametrize(
    ("selected", "solved"),
    [
        ((), frozenset()),  # 零題
        ((1, 1), frozenset()),  # 重複
        ((9,), frozenset()),  # 不存在
        ((1, 2), frozenset({2})),  # 含已成功題
        (None, frozenset({1, 2, 3, 4})),  # 預設全選，但全部都已成功
        ((True,), frozenset()),  # bool 不是題號
    ],
)
def test_invalid_selection(selected, solved):
    with pytest.raises(InvalidInputError) as exc:
        InputRules.validate_selection(selected, (1, 2, 3, 4), solved)
    assert exc.value.reason is RejectionReason.INVALID_SELECTION
