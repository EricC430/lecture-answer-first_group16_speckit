"""RankingService：判錯、撤銷、定案與依角色的結果檢視（004）。

用自己的每活動鎖序列化判錯、撤銷與定案（研究 R1），推送在鎖外（研究 R4）。日誌只記
活動代碼、輪次、題號、組號、版本與結果，不記答案、token、憑證（FR-032）。
"""

import logging
from collections.abc import Mapping

from lecture_quiz.app.activity.ports import SyncPublisher, TeacherViewer, Viewer
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.ranking_review.ports import (
    FinalizedRound,
    FinalizeResult,
    MarkResult,
    ReviewOutcome,
)
from lecture_quiz.app.ranking_review.store import ReviewStore
from lecture_quiz.app.round_submission.ports import SubmissionReader
from lecture_quiz.core.activity.models import Activity, Round, Stage
from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.ranking_review.models import Candidate, RankingInput
from lecture_quiz.core.ranking_review.review import RoundReview
from lecture_quiz.core.ranking_review.view import ResultView, RoundView
from lecture_quiz.core.round_submission.models import Submission

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

    @staticmethod
    def _build_input(
        activity: Activity,
        round_number: int,
        submissions: tuple[Submission, ...],
        wrong_marks: frozenset[tuple[int, int]],
    ) -> RankingInput:
        """由 001 的輪次與 003 的提交組成整輪重算的輸入。

        基準取自 `Round.baseline`（開輪時保存、key 為組號，重算一律使用這份）；題號與
        模式取自 `Round.rules`；候選只取 003 提交的組號、題號、接收時間與接收序號。
        組別、時間與序號一律來自後端資料，不採信任何前端輸入（FR-026）。

        Args:
            activity: 活動。
            round_number: 輪次編號（必須存在於 `activity.rounds`）。
            submissions: 該輪全部有效提交。
            wrong_marks: 被判錯的（組號, 題號）集合。

        Returns:
            整輪重算的輸入。
        """
        round_ = next(r for r in activity.rounds if r.number == round_number)
        return RankingInput(
            question_numbers=round_.rules.question_numbers,
            fair_mode=round_.rules.fair_mode,
            baseline=round_.baseline,
            candidates=tuple(
                Candidate(s.group_number, s.question_number, s.received_at, s.sequence)
                for s in submissions
            ),
            wrong_marks=wrong_marks,
        )

    @staticmethod
    def _is_final(activity: Activity, round_: Round) -> bool:
        """該輪是否已定案：早於目前輪，或目前輪且階段為結果已定案／已結束。"""
        current = activity.current_round
        if current is None:
            return False
        if round_.number < current.number:
            return True
        return activity.stage in (Stage.RESULT_FINAL, Stage.ENDED)

    def _review_of(self, activity: Activity, round_: Round) -> RoundReview:
        """已保存的審閱狀態；沒有時以純計算導出初始結果（版本 1，不寫入存放區）。"""
        stored = self._store.get(activity.code, round_.number)
        if stored is not None:
            return stored
        submissions = self._submissions.round_submissions(activity.code, round_.number)
        data = self._build_input(activity, round_.number, submissions, frozenset())
        return RoundReview.initial(round_.number, data)

    def review_for(self, code: str, round_number: int) -> RoundReview | None:
        """某輪的審閱狀態；搶答中、輪次或活動不存在時為 `None`。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。

        Returns:
            已保存的審閱狀態，沒有判錯時為純計算導出的初始結果（版本 1）。
        """
        activity = self._activities.get(code)
        if activity is None:
            return None
        round_ = next((r for r in activity.rounds if r.number == round_number), None)
        if round_ is None or not round_.closed:
            return None
        return self._review_of(activity, round_)

    def snapshot_extension(
        self, activity: Activity, viewer: Viewer
    ) -> Mapping[str, object]:
        """併入快照的 004 欄位（contracts/sync-websocket.md）。

        同步、無副作用：只有純計算與不可變的快取（`docs/DEVELOPMENT.md` 3.5）。只輸出
        已關輪的輪次；搶答中的目前輪不輸出（FR-024）。

        Args:
            activity: 活動。
            viewer: 檢視者。

        Returns:
            要併入的欄位；沒有已關輪輪次時為空 mapping。
        """
        kind = "teacher" if isinstance(viewer, TeacherViewer) else "student"
        rounds: list[JsonDict] = []
        for round_ in activity.rounds:
            if not round_.closed:
                continue
            final = self._is_final(activity, round_)
            stored = self._store.get(activity.code, round_.number)
            version = stored.version if stored is not None else 1
            cached = self._store.cache_get(
                activity.code, round_.number, version, final, kind
            )
            if cached is None:
                review = self._review_of(activity, round_)
                view = [RoundView(round_.number, round_.rules.fair_mode, review, final)]
                body = (
                    ResultView.for_teacher(view)
                    if kind == "teacher"
                    else ResultView.for_student(view)
                )
                cached = body["rounds"][0]  # type: ignore[index]
                self._store.cache_put(
                    activity.code, round_.number, version, final, kind, cached
                )
            rounds.append(cached)
        if not rounds:
            return {}
        return {"ranking": {"rounds": rounds}}

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
