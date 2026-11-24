"""寫回後的核對判定（純函式；FR-016，research R7）。

只比對「記錄位置」上的內容與預期答案，不做結構檢查。
"""

from collections.abc import Mapping, Sequence

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import (
    CellCheck,
    CellKind,
    CurrentCell,
    OutcomeStatus,
    Reconciliation,
)

Expected = tuple[int, int | None, CellRef, str]
"""（題號, 子編號, 目標位置, 預期答案）。"""


def reconcile(
    expected: Sequence[Expected], current: Mapping[CellRef, CurrentCell]
) -> Reconciliation:
    """比對目標格目前的內容與預期答案。

    Args:
        expected: 每個目標格的預期。
        current: 目標格目前的內容；沒有的格視為空。

    Returns:
        全部逐字相同為 `SUCCESS`；全部不同為 `FAILED`；其餘為 `PENDING`。

    Raises:
        ValueError: `expected` 為空（沒有目標格不應被核對）。
    """
    if not expected:
        raise ValueError("沒有目標格可以核對")
    checks: list[CellCheck] = []
    for question, sub_index, target, answer in expected:
        cell = current.get(target, CurrentCell(CellKind.EMPTY))
        shown = cell.text if cell.kind is CellKind.TEXT else cell.display
        matches = cell.kind is CellKind.TEXT and cell.text == answer
        checks.append(CellCheck(question, sub_index, answer, shown or "", matches))
    matched = sum(1 for c in checks if c.matches)
    if matched == len(checks):
        status = OutcomeStatus.SUCCESS
    elif matched == 0:
        status = OutcomeStatus.FAILED
    else:
        status = OutcomeStatus.PENDING
    return Reconciliation(status, tuple(checks))
