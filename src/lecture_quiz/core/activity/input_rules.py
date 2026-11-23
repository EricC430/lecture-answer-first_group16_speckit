"""輸入規則（純函式）：組數上限、倒數秒數、選題、題號。

驗證失敗時拋出 `InvalidInputError`，由狀態機轉成拒絕原因；不產生任何部分結果（FR-031）。
組名正規化（`normalize_group_name`）待 US2 依組號決議實作。
"""

from collections.abc import Sequence

from lecture_quiz.core.activity.results import RejectionReason

MIN_MAX_GROUPS = 1
MAX_MAX_GROUPS = 99
MIN_COUNTDOWN = 1
MAX_COUNTDOWN = 3600


class InvalidInputError(Exception):
    """輸入不合法。

    Attributes:
        reason: 對應的拒絕原因。
    """

    def __init__(self, reason: RejectionReason) -> None:
        """建立例外。

        Args:
            reason: 拒絕原因。
        """
        super().__init__(reason.value)
        self.reason = reason


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class InputRules:
    """建立活動、開輪與匯入的輸入驗證。"""

    @staticmethod
    def validate_max_groups(raw: object) -> int:
        """驗證組數上限：1～99 的整數（FR-036、研究 R9）。

        Args:
            raw: 原始輸入（可能是任何 JSON 值）。

        Returns:
            組數上限。

        Raises:
            InvalidInputError: 不是 1～99 的整數（含布林、小數、字串、`None`）。
        """
        if _is_int(raw) and MIN_MAX_GROUPS <= raw <= MAX_MAX_GROUPS:  # type: ignore[operator]
            return int(raw)  # type: ignore[call-overload]
        raise InvalidInputError(RejectionReason.INVALID_MAX_GROUPS)

    @staticmethod
    def validate_countdown(raw: object) -> int | None:
        """驗證倒數秒數：`None`（不倒數）或 1～3600 的整數（FR-017）。

        Args:
            raw: 原始輸入（可能是任何 JSON 值）。

        Returns:
            秒數或 `None`。

        Raises:
            InvalidInputError: 秒數為小數、字串、布林、超出範圍等。
        """
        if raw is None:
            return None
        if _is_int(raw) and MIN_COUNTDOWN <= raw <= MAX_COUNTDOWN:  # type: ignore[operator]
            return int(raw)  # type: ignore[call-overload]
        raise InvalidInputError(RejectionReason.INVALID_COUNTDOWN)

    @staticmethod
    def validate_selection(
        selected: Sequence[int] | None,
        imported: tuple[int, ...],
        solved: frozenset[int],
    ) -> tuple[int, ...]:
        """驗證本輪所選題目（FR-014）。

        Args:
            selected: 老師所選題號；`None` 表示全部未成功題。
            imported: 活動的題號（匯入順序）。
            solved: 已成功題號。

        Returns:
            依匯入順序排列的所選題號。

        Raises:
            InvalidInputError: 零題、重複、不存在、已成功，或沒有任何未成功題可選。
        """
        unsolved = tuple(q for q in imported if q not in solved)
        if selected is None:
            if not unsolved:
                raise InvalidInputError(RejectionReason.INVALID_SELECTION)
            return unsolved
        chosen = list(selected)
        if (
            not chosen
            or not all(_is_int(q) for q in chosen)
            or len(set(chosen)) != len(chosen)
            or not set(chosen) <= set(unsolved)
        ):
            raise InvalidInputError(RejectionReason.INVALID_SELECTION)
        return tuple(q for q in imported if q in set(chosen))

    @staticmethod
    def validate_question_numbers(numbers: Sequence[int]) -> tuple[int, ...]:
        """驗證 002 匯入的題號：至少一題、正整數、不重複。

        Args:
            numbers: 題號。

        Returns:
            原順序的題號。

        Raises:
            InvalidInputError: 不合法時。
        """
        values = list(numbers)
        if (
            not values
            or not all(_is_int(q) and q >= 1 for q in values)
            or len(set(values)) != len(values)
        ):
            raise InvalidInputError(RejectionReason.INVALID_SELECTION)
        return tuple(values)
