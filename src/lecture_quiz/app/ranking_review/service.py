"""RankingService：判錯、撤銷、定案與依角色的結果檢視（004）。

用自己的每活動鎖序列化判錯、撤銷與定案（研究 R1），推送在鎖外（研究 R4）。日誌只記
活動代碼、輪次、題號、組號、版本與結果，不記答案、token、憑證（FR-032）。
"""

import logging
from collections.abc import Mapping

from lecture_quiz.app.activity.ports import SyncPublisher, Viewer
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.ranking_review.ports import (
    FinalizedRound,
    FinalizeResult,
    MarkResult,
    ReviewOutcome,
)
from lecture_quiz.app.ranking_review.store import ReviewStore
from lecture_quiz.app.round_submission.ports import SubmissionReader
from lecture_quiz.core.activity.models import Activity

logger = logging.getLogger(__name__)


class RankingService:
    """004 的應用服務（實作 `RankingReader`）；建立時向 001 註冊快照擴充。"""

    def __init__(
        self,
        activity_service: ActivityService,
        submissions: SubmissionReader,
        store: ReviewStore,
        publisher: SyncPublisher,
    ) -> None:
        """建立服務並註冊快照擴充。

        Args:
            activity_service: 001 的活動服務。
            submissions: 003 的提交唯讀介面。
            store: 004 的記憶體存放區。
            publisher: 001 的推送（`WebSocketHub`）。
        """
        self._activities = activity_service
        self._submissions = submissions
        self._store = store
        self._publisher = publisher
        activity_service.add_snapshot_extension(self.snapshot_extension)

    def snapshot_extension(
        self, activity: Activity, viewer: Viewer
    ) -> Mapping[str, object]:
        """併入快照的 004 欄位（contracts/sync-websocket.md）。

        Args:
            activity: 活動。
            viewer: 檢視者。

        Returns:
            要併入的欄位；沒有已關輪輪次時為空 mapping。
        """
        return {}

    async def mark_wrong(
        self,
        code: str,
        requester: object,
        round_number: int,
        question_number: int,
        group_number: int,
    ) -> ReviewOutcome[MarkResult]:
        """判錯。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            round_number: 輪次編號。
            question_number: 題號。
            group_number: 組號。

        Returns:
            判定結果。
        """
        raise NotImplementedError

    async def unmark_wrong(
        self,
        code: str,
        requester: object,
        round_number: int,
        question_number: int,
        group_number: int,
    ) -> ReviewOutcome[MarkResult]:
        """撤銷判錯。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            round_number: 輪次編號。
            question_number: 題號。
            group_number: 組號。

        Returns:
            判定結果。
        """
        raise NotImplementedError

    async def finalize(
        self, code: str, requester: object, result_version: int
    ) -> ReviewOutcome[FinalizeResult]:
        """確認定案。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            result_version: 老師所見的結果版本。

        Returns:
            判定結果。
        """
        raise NotImplementedError

    def finalized_rounds(self, code: str) -> tuple[FinalizedRound, ...]:
        """已定案輪次的唯讀視圖（給 005）。

        Args:
            code: 活動代碼。

        Returns:
            已定案輪次，依輪次遞增。
        """
        raise NotImplementedError
