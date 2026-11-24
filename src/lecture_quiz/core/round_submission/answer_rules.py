"""答案規則（003 研究 R8；Q-20 已獲 OpenSpec 組同意，alignment 2026-11-23）。

- 每格答案上限 `MAX_ANSWER_CHARS` 字（以字元計，中文一字算一字）。
- 判斷是否為空時去除首尾空白（`str.strip()`：含全形空白、Tab、換行）。
- 保存與顯示都用原文，允許多行。

規則集中在本檔，日後調整只需改這裡與對應測試。
"""

from lecture_quiz.core.round_submission.models import SubmissionRejection

MAX_ANSWER_CHARS = 500


class InvalidAnswerError(Exception):
    """答案不合法。

    Attributes:
        rejection: 拒絕原因。
        blank_numbers: 有問題的格號（1 起算）。
        expected_blanks: 格數不符時，該題需要的格數。
    """

    def __init__(
        self,
        rejection: SubmissionRejection,
        blank_numbers: tuple[int, ...] = (),
        expected_blanks: int | None = None,
    ) -> None:
        """建立例外。

        Args:
            rejection: 拒絕原因。
            blank_numbers: 有問題的格號。
            expected_blanks: 該題需要的格數。
        """
        super().__init__(rejection.value)
        self.rejection = rejection
        self.blank_numbers = blank_numbers
        self.expected_blanks = expected_blanks


class AnswerRules:
    """一筆提交的答案檢查。"""

    @staticmethod
    def check(raw: object, expected: int) -> tuple[str, ...]:
        """檢查各格答案，通過時回傳原文。

        檢查順序：型別 → 格數 → 空格（列出全部）→ 字數（列出全部）。

        Args:
            raw: 原始輸入（應為字串陣列）。
            expected: 該題的子空格數。

        Returns:
            各格答案原文。

        Raises:
            InvalidAnswerError: 型別、格數、空格或字數不合法。
        """
        if not isinstance(raw, list | tuple) or not all(
            isinstance(cell, str) for cell in raw
        ):
            raise InvalidAnswerError(SubmissionRejection.INVALID_ANSWER)
        if len(raw) != expected:
            raise InvalidAnswerError(
                SubmissionRejection.WRONG_BLANK_COUNT, expected_blanks=expected
            )
        empty = tuple(i for i, cell in enumerate(raw, 1) if not cell.strip())
        if empty:
            raise InvalidAnswerError(SubmissionRejection.BLANK_EMPTY, empty)
        too_long = tuple(
            i for i, cell in enumerate(raw, 1) if len(cell) > MAX_ANSWER_CHARS
        )
        if too_long:
            raise InvalidAnswerError(SubmissionRejection.ANSWER_TOO_LONG, too_long)
        return tuple(raw)
