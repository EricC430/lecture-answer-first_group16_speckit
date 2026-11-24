"""SubmissionService：多題搶答的送出、檢視與提供給 004／005 的讀取（003）。

判定、標記組別與保存都經 001 的 `ActivityService.record_submission` 在同一把活動
鎖內完成，推送在鎖外（003 研究 R2）；提交資料透過 001 的快照擴充推送（研究 R4）。
日誌只記活動代碼、輪次、題號、組號與結果，不記 token 與答案內容（研究 R13）。
"""

import logging
from collections.abc import Mapping
from datetime import datetime

from lecture_quiz.app.activity.ports import (
    HandlerStep,
    Outcome,
    SubmissionWindow,
    TeacherViewer,
    Viewer,
)
from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.round_submission.ports import QuestionShapeSource
from lecture_quiz.app.round_submission.store import SubmissionStore
from lecture_quiz.core.activity.models import Activity, Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.round_submission.models import (
    DecisionKind,
    RoundContext,
    Submission,
    SubmissionAttempt,
    SubmissionDecision,
    SubmissionLedger,
    SubmissionRejection,
)
from lecture_quiz.core.round_submission.rules import SubmissionRules
from lecture_quiz.core.round_submission.view import SubmissionView

logger = logging.getLogger(__name__)


def _from_activity_rejection(reason: RejectionReason | None) -> SubmissionRejection:
    """001 層面的拒絕轉成 003 的拒絕原因。"""
    if reason is RejectionReason.ACTIVITY_GONE:
        return SubmissionRejection.ACTIVITY_GONE
    if reason is RejectionReason.NOT_IN_GROUP:
        return SubmissionRejection.NOT_IN_GROUP
    # RecordSubmission 被拒（已截止、已關輪、組別不存在）：與「本輪已結束」相同處理
    return SubmissionRejection.ROUND_CLOSED


class _SubmitHandler:
    """一次 `submit` 的處理器；`decide` 與 `commit` 都在 001 的活動鎖內被呼叫。"""

    def __init__(
        self,
        store: SubmissionStore,
        shapes: QuestionShapeSource,
        code: str,
        attempt: SubmissionAttempt,
    ) -> None:
        self._store = store
        self._shapes = shapes
        self._code = code
        self._attempt = attempt
        self._ledger: SubmissionLedger | None = None
        self._decision: SubmissionDecision | None = None
        self.window: SubmissionWindow | None = None  # 給日誌：001 判定的組號與輪次

    def decide(
        self, window: SubmissionWindow, now: datetime
    ) -> HandlerStep[SubmissionDecision]:
        self.window = window
        ledger = self._store.get(self._code)
        context = RoundContext(
            group_number=window.group_number,
            round_number=window.round_number,
            open_questions=window.open_questions,
            accepting=window.accepting,
            blanks_per_question=self._shapes.blanks_per_question(self._code) or {},
        )
        decision = SubmissionRules.decide(
            ledger, context, self._code, self._attempt, now
        )
        self._ledger, self._decision = ledger, decision
        if decision.kind is DecisionKind.ACCEPTED:
            return HandlerStep.accept(decision)
        return HandlerStep.no_change(decision)

    def commit(self) -> None:
        assert self._ledger is not None and self._decision is not None
        assert self._decision.submission is not None
        self._store.put(self._code, self._ledger.with_added(self._decision.submission))


class SubmissionService:
    """003 的應用服務（實作 `SubmissionReader`）；建立時向 001 註冊快照擴充。"""

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

    async def submit(
        self, code: str, device_token: str, attempt: SubmissionAttempt
    ) -> Outcome[SubmissionDecision]:
        """送出一筆答案。

        一律回傳 `ok=True`；接受、本組已送出或拒絕都放在 `value`。

        Args:
            code: 活動代碼（會正規化）。
            device_token: 原始裝置 token。
            attempt: 學生送出的原始內容。

        Returns:
            判定結果。
        """
        code = normalize_code_input(code)
        handler = _SubmitHandler(self._store, self._shapes, code, attempt)
        outcome = await self._activities.record_submission(code, device_token, handler)
        if outcome.ok and outcome.value is not None:
            decision = outcome.value
        else:
            decision = SubmissionDecision(
                DecisionKind.REJECTED,
                rejection=_from_activity_rejection(outcome.rejection),
            )
        self._log(code, attempt, decision, handler.window)
        return Outcome(ok=True, value=decision)

    def round_submissions(self, code: str, round_number: int) -> tuple[Submission, ...]:
        """某一輪的全部有效提交，依（接收時間, 接收序號）排序（給 004、005）。

        Args:
            code: 活動代碼。
            round_number: 輪次編號。

        Returns:
            排序後的提交；活動不存在或沒有提交時為空 tuple。
        """
        ledger = self._store.get(normalize_code_input(code))
        return SubmissionRules.order(ledger.for_round(round_number))

    def all_submissions(self, code: str) -> tuple[Submission, ...]:
        """全部輪次的有效提交，依（接收時間, 接收序號）排序（給 004、005）。

        Args:
            code: 活動代碼。

        Returns:
            排序後的提交。
        """
        ledger = self._store.get(normalize_code_input(code))
        return SubmissionRules.order(ledger.submissions)

    @staticmethod
    def _log(
        code: str,
        attempt: SubmissionAttempt,
        decision: SubmissionDecision,
        window: SubmissionWindow | None,
    ) -> None:
        """記錄一筆提交的結果；不記 token 與答案（研究 R13）。

        組號與輪次取自 001 在鎖內判定的 `window`（不採信學生送來的值）；活動不存在
        或裝置不屬於任何組時 001 不會呼叫判定，記為 `-`。
        """
        sub = decision.submission
        result = (
            "accepted"
            if decision.kind is DecisionKind.ACCEPTED
            else "alreadySubmitted"
            if decision.kind is DecisionKind.ALREADY_SUBMITTED
            else str(decision.rejection)
        )
        raw = attempt.question_number_raw
        # 只記合理範圍的整數題號：避免把不可信的輸入（或超長整數）寫進日誌
        question = (
            sub.question_number
            if sub
            else raw
            if isinstance(raw, int) and not isinstance(raw, bool) and 0 < raw < 10000
            else "-"
        )
        logger.info(
            "提交 activity=%s round=%s question=%s group=%s result=%s",
            code,
            window.round_number if window and window.round_number else "-",
            question,
            window.group_number if window else "-",
            result,
        )

    def snapshot_extension(
        self, activity: Activity, viewer: Viewer
    ) -> Mapping[str, object]:
        """併入快照的 003 欄位（contracts/sync-websocket.md）。

        活動還沒有格數資料（尚未匯入題目）時不帶任何 003 欄位。
        `questionShapes`：老師為全部題的格數；學生只有本輪開放題的格數。
        `submissions`：依角色裁切（`SubmissionView`）；`current` 學生只有本組
        （FR-021），`published` 是已關輪的輪次，所有角色都看得到全部組（研究 R11）。

        Args:
            activity: 活動。
            viewer: 檢視者。

        Returns:
            要併入快照的欄位。
        """
        shapes = self._shapes.blanks_per_question(activity.code)
        if shapes is None:
            return {}
        ledger = self._store.get(activity.code)
        if isinstance(viewer, TeacherViewer):
            visible = sorted(shapes)
            fields = SubmissionView.for_teacher(ledger, activity)
        else:
            current = activity.current_round
            is_open = activity.stage is Stage.ROUND_OPEN and current is not None
            open_questions = current.rules.question_numbers if current else ()
            visible = [q for q in open_questions if q in shapes] if is_open else []
            fields = SubmissionView.for_group(ledger, activity, viewer.group_number)
        return {"questionShapes": {str(q): shapes[q] for q in visible}, **fields}
