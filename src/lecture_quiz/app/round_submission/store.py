"""提交的記憶體存放區（003 研究 R1）；後端重啟即清空。"""

from lecture_quiz.core.round_submission.models import SubmissionLedger


class SubmissionStore:
    """活動代碼 → `SubmissionLedger`。讀寫只發生在 001 的活動鎖內。"""

    def __init__(self) -> None:
        """建立空的存放區。"""
        self._ledgers: dict[str, SubmissionLedger] = {}

    def get(self, code: str) -> SubmissionLedger:
        """取得活動的 ledger；沒有時回傳空 ledger。

        Args:
            code: 活動代碼。

        Returns:
            ledger。
        """
        return self._ledgers.get(code, SubmissionLedger())

    def put(self, code: str, ledger: SubmissionLedger) -> None:
        """以新的 ledger 取代舊的。

        Args:
            code: 活動代碼。
            ledger: 新的 ledger。
        """
        self._ledgers[code] = ledger
