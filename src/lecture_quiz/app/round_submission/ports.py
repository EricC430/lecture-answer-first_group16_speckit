"""003 的連接埠（contracts/service-interfaces.md）。"""

from collections.abc import Mapping
from typing import Protocol

from lecture_quiz.core.round_submission.models import Submission


class QuestionShapeSource(Protocol):
    """每題子空格數的來源；由 002 實作（003 研究 R6）。"""

    def blanks_per_question(self, code: str) -> Mapping[int, int] | None:
        """題號 → 子空格數（單題為 1）。

        Args:
            code: 活動代碼。

        Returns:
            最後一次成功匯入的格數；尚未匯入時為 `None`。
        """
        ...


class SubmissionReader(Protocol):
    """提供給 004、005 的唯讀介面。"""

    def round_submissions(self, code: str, round_number: int) -> tuple[Submission, ...]:
        """某一輪的全部有效提交，依（接收時間, 接收序號）排序。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。

        Returns:
            排序後的提交。
        """
        ...

    def all_submissions(self, code: str) -> tuple[Submission, ...]:
        """全部輪次的有效提交，依（接收時間, 接收序號）排序。

        Args:
            code: 活動代碼。

        Returns:
            排序後的提交。
        """
        ...


class NullQuestionShapeSource:
    """尚未有任何格數來源時使用（002 合併前、未啟用 dev seed）：一律回傳 `None`。"""

    def blanks_per_question(self, code: str) -> Mapping[int, int] | None:
        """一律沒有格數。

        Args:
            code: 活動代碼。

        Returns:
            `None`。
        """
        return None
