"""SubmissionService：多題搶答的送出、檢視與提供給 004／005 的讀取（003）。

判定、標記組別與保存都經 001 的 `ActivityService.record_submission` 在同一把活動
鎖內完成，推送在鎖外（003 研究 R2）；提交資料透過 001 的快照擴充推送（研究 R4）。
"""

import logging
from collections.abc import Mapping

from lecture_quiz.app.activity.ports import Viewer
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.round_submission.ports import QuestionShapeSource
from lecture_quiz.app.round_submission.store import SubmissionStore
from lecture_quiz.core.activity.models import Activity

logger = logging.getLogger(__name__)


class SubmissionService:
    """003 的應用服務；建立時向 001 註冊快照擴充。"""

    def __init__(
        self,
        activity_service: ActivityService,
        store: SubmissionStore,
        shapes: QuestionShapeSource,
    ) -> None:
        """建立服務並註冊快照擴充。

        Args:
            activity_service: 001 的活動服務。
            store: 提交的記憶體存放區。
            shapes: 每題子空格數的來源（002 或開發用）。
        """
        self._activities = activity_service
        self._store = store
        self._shapes = shapes
        activity_service.add_snapshot_extension(self.snapshot_extension)

    def snapshot_extension(
        self, activity: Activity, viewer: Viewer
    ) -> Mapping[str, object]:
        """併入快照的提交資料（US4、US5 完成）。

        Args:
            activity: 活動。
            viewer: 檢視者。

        Returns:
            要併入快照的欄位。
        """
        return {}
