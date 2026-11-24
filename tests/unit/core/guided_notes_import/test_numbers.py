"""題號正規化（research R5）：明確的 ASCII 規則，不用 `isdigit`／寬鬆 `int()`。"""

import pytest

from lecture_quiz.core.guided_notes_import.models import CellValue
from lecture_quiz.core.guided_notes_import.numbers import normalize_number


def number(value: float) -> CellValue:
    return CellValue(number=value, text=None, display=str(value))


def text(value: str) -> CellValue:
    return CellValue(number=None, text=value, display=value)


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        (number(1), 1),
        (number(1.0), 1),
        (number(12.0), 12),
        (text(" 1 "), 1),
        (text("01"), 1),
        (text("1"), 1),
        (text("　2　"), 2),
    ],
)
def test_accepts_positive_integers(cell, expected):
    """Scenario: US2-AS4"""
    assert normalize_number(cell) == expected


@pytest.mark.parametrize(
    "cell",
    [
        number(0),
        number(-1),
        number(1.5),
        number(float("nan")),
        number(float("inf")),
        text("1."),
        text("第1題"),
        text("Q1"),
        text("１"),  # 全形數字：Python 的 isdigit 會誤收，這裡必須拒絕
        text("²"),  # 上標數字
        text("0"),
        text("-1"),
        text("1.5"),
        text(""),
        text("   "),
        CellValue(number=None, text=None, display="TRUE"),  # 布林
        CellValue(number=None, text=None, display="#DIV/0!"),  # 錯誤值
    ],
)
def test_rejects_non_numbers(cell):
    """Edge: 題號格式"""
    assert normalize_number(cell) is None


class _IntWithoutIsInteger(int):
    """模擬 Python 3.11：`int` 沒有 `is_integer()`（3.12 才加入）。"""

    is_integer = None  # type: ignore[assignment]


@pytest.mark.parametrize(
    ("value", "expected"), [(1, 1), (12, 12), (0, None), (-3, None)]
)
def test_python_int_cells_work_without_int_is_integer(value, expected):
    """`CellValue.number` 型別允許 int；3.11 的 int 沒有 `is_integer()`，不得拋例外。"""
    cell = CellValue(number=_IntWithoutIsInteger(value), text=None, display=str(value))
    assert normalize_number(cell) == expected
