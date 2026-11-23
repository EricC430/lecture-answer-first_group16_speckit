"""題號正規化（research R5）。

一律用明確的 ASCII 規則運算式，**不使用** `str.isdigit()` 或寬鬆的 `int()`：
Python 會把全形數字與上標數字當成數字，但題號只接受半形 0～9。
"""

import math
import re

from lecture_quiz.core.guided_notes_import.models import CellValue

_ASCII_DIGITS = re.compile(r"[0-9]{1,9}")
"""題號文字：只含半形數字；最多 9 位，避免超長字串轉整數的問題。"""


def is_blank(value: CellValue | None) -> bool:
    """儲存格是否為空（沒有值、或只有空白文字）。

    Args:
        value: 儲存格值；`None` 代表工作表上沒有這個儲存格。

    Returns:
        空儲存格為 True。布林與錯誤值有顯示內容，視為非空。
    """
    if value is None:
        return True
    if value.number is not None:
        return False
    if value.text is not None:
        return value.text.strip() == ""
    return value.display.strip() == ""


def normalize_number(value: CellValue) -> int | None:
    """把題號儲存格轉成正整數；不合法時回傳 `None`。

    接受：值為正整數的數值（1、1.0）、去除首尾空白後僅由半形數字組成且大於 0 的文字
    （「1」「01」「 1 」）。其餘一律拒絕：0、負數、小數、「1.」「第1題」「Q1」、
    全形數字、布林與錯誤值。

    Args:
        value: 題號欄的儲存格值。

    Returns:
        題號；不合法時為 `None`。
    """
    if value.number is not None:
        number = value.number
        if math.isfinite(number) and number.is_integer() and number > 0:
            return int(number)
        return None
    if value.text is not None:
        text = value.text.strip()
        if _ASCII_DIGITS.fullmatch(text):
            parsed = int(text)
            return parsed if parsed > 0 else None
    return None
