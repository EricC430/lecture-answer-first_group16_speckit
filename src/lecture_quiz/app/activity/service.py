"""ActivityService：序列化同一活動的操作、重送去重、觸發推送（研究 R5、R6）。

會改變狀態的操作都走 `_execute`，順序是：
1. 取得該活動的鎖。
2. 查詢去重表（同一身分、同一個 Idempotency-Key 直接回傳第一次的結果）。
3. 呼叫 `ActivityStateMachine.apply(..., now=clock.now())`。
4. 成功且有變化時，以新的 `Activity` 取代舊的，並執行排程等副作用。
5. 記錄去重結果。
6. 釋放鎖。
7. 有變化時推送。

查表、套用、記錄都在同一把鎖內，同一個 key 的並行重送只會套用一次
（FR-033；PR #15 審查第 2 項）。

給 003 的擴充（003 研究 R2、R4）：
- `record_submission`：在同一把活動鎖內完成「判定 → 標記組別 → 保存」，鎖外推送。
- `add_snapshot_extension`：把 003 的提交資料併入依角色裁切的快照。
"""

import dataclasses
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from lecture_quiz.app.activity.ports import (
    Clock,
    CountdownScheduler,
    DisconnectReason,
    GroupViewer,
    Outcome,
    Requester,
    SnapshotExtension,
    SubmissionHandler,
    SubmissionWindow,
    SyncPublisher,
    TeacherViewer,
)
from lecture_quiz.app.activity.registry import ActivityRegistry, ProcessedKey
from lecture_quiz.app.activity.secrets_gen import (
    hash_token,
    new_code,
    new_credential,
    new_token,
    normalize_code_input,
    tokens_match,
)
from lecture_quiz.core.activity.commands import (
    Actor,
    Anonymous,
    CancelActivity,
    CloseRound,
    Command,
    CreateActivity,
    DeleteGroup,
    Device,
    EndActivity,
    Finalize,
    FinalizeOutcome,
    JoinGroup,
    LeaveGroup,
    MarkGroupSubmitted,
    OpenJoining,
    OpenRound,
    RecordSubmission,
    ReplaceQuestions,
    System,
    Teacher,
)
from lecture_quiz.core.activity.models import Activity, Group, Round, Stage
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    Transition,
    describe_rejection,
)
from lecture_quiz.core.activity.snapshot_view import ActivitySnapshot, SnapshotView
from lecture_quiz.core.activity.state_machine import ActivityStateMachine

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class CreatedActivity:
    """建立活動的結果；`teacher_token` 只在這裡出現一次。"""

    code: str
    teacher_token: str
    max_groups: int
    version: int


@dataclass(frozen=True)
class JoinedDevice:
    """加入組別的結果；瀏覽器金鑰不在其中（007 FR-008，只存在 cookie）。"""

    group_number: int
    credential: str
    version: int


@dataclass(frozen=True)
class DeviceContext:
    """給 003 的裝置資訊；所屬組別一律由後端判定（FR-012）。"""

    group_number: int
    stage: Stage
    round_number: int | None
    open_questions: tuple[int, ...]
    deadline: datetime | None


@dataclass(frozen=True)
class RoundOpened:
    """開輪結果。"""

    round_number: int
    deadline: datetime | None
    version: int


@dataclass(frozen=True)
class RoundClosed:
    """關輪結果；`already_closed` 表示這次請求沒有改變狀態。"""

    round_number: int
    version: int
    already_closed: bool


@dataclass(frozen=True)
class ActivityEnded:
    """結束活動的結果。"""

    version: int
    unsolved_questions: tuple[int, ...]


@dataclass(frozen=True)
class ExportView:
    """提供給 005 的匯出資料。"""

    code: str
    stage: Stage
    question_numbers: tuple[int, ...]
    solved_questions: frozenset[int]
    unsolved_questions: tuple[int, ...]
    groups: tuple[Group, ...]


def _gone() -> Outcome[T]:
    reason = RejectionReason.ACTIVITY_GONE
    return Outcome(ok=False, rejection=reason, message=reason.default_message)


def _identity(actor: Actor) -> str:
    if isinstance(actor, Teacher | Device):
        return actor.token_hash
    return "system" if isinstance(actor, System) else "anonymous"


def _idempotency_identity(command: Command) -> str:
    """Idempotency-Key 的身分範圍。

    加入組別以瀏覽器雜湊為範圍（007 verification P-01）：同一瀏覽器第一次加入時是匿名，
    重送時已是組員；若以請求者區分，重送會查不到快取而回 409。
    """
    if isinstance(command, JoinGroup) and command.device_token_hash:
        return command.device_token_hash
    return _identity(command.actor)


class ActivityService:
    """活動的應用服務；同時實作給 002 的 `ActivityGateway` 與給 003～005 的介面。"""

    def __init__(
        self,
        registry: ActivityRegistry,
        clock: Clock,
        scheduler: CountdownScheduler,
        publisher: SyncPublisher,
    ) -> None:
        """建立服務。

        Args:
            registry: 記憶體存放區。
            clock: 時鐘；核心需要的 `now` 都從這裡取得後傳入。
            scheduler: 倒數排程。
            publisher: 狀態推送。
        """
        self._registry = registry
        self._clock = clock
        self._scheduler = scheduler
        self._publisher = publisher
        self._extensions: list[SnapshotExtension] = []

    @property
    def registry(self) -> ActivityRegistry:
        """記憶體存放區（測試與轉接層查詢用）。"""
        return self._registry

    # ── 查詢 ─────────────────────────────────────────────

    def get(self, code: str) -> Activity | None:
        """取得活動；代碼會先正規化。

        Args:
            code: 活動代碼。

        Returns:
            活動或 `None`。
        """
        return self._registry.get(normalize_code_input(code))

    def resolve_requester(self, code: str, token: str | None) -> Requester:
        """把 token 轉成這個活動的身分。

        Args:
            code: 活動代碼。
            token: 原始 token；沒有時為 `None`。

        Returns:
            `Teacher`、`Device` 或 `Anonymous`。
        """
        activity = self.get(code)
        if activity is None or not token:
            return Anonymous()
        if tokens_match(token, activity.teacher.token_hash):
            return Teacher(activity.teacher.token_hash)
        token_hash = hash_token(token)
        if token_hash in activity.devices:
            return Device(token_hash)
        return Anonymous()

    def stage(self, code: str) -> Stage | None:
        """目前階段；活動不存在時為 `None`（`ActivityGateway`）。

        Args:
            code: 活動代碼。

        Returns:
            階段或 `None`。
        """
        activity = self.get(code)
        return activity.stage if activity else None

    def is_teacher(self, code: str, requester: Requester) -> bool:
        """`requester` 是否為該活動老師（`ActivityGateway`）。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            是老師時為 True。
        """
        activity = self.get(code)
        return activity is not None and ActivityStateMachine.is_teacher(
            activity, requester
        )

    def snapshot(self, code: str, requester: Requester) -> Outcome[ActivitySnapshot]:
        """依身分取得裁切後的快照。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            老師版或學生版快照；匿名身分回傳 `NOT_TEACHER`。
        """
        activity = self.get(code)
        if activity is None:
            return _gone()
        view = self.snapshot_for(activity, requester)
        if view is None:
            reason = RejectionReason.NOT_TEACHER
            return Outcome(ok=False, rejection=reason, message=reason.default_message)
        return Outcome(ok=True, value=view)

    def add_snapshot_extension(self, extension: SnapshotExtension) -> None:
        """註冊快照擴充（003 研究 R4）；之後所有快照都會併入它回傳的欄位。

        Args:
            extension: 擴充函式。
        """
        self._extensions.append(extension)

    def snapshot_for(
        self, activity: Activity, requester: Requester
    ) -> ActivitySnapshot | None:
        """依身分裁切快照，並併入已註冊的擴充欄位；身分無效時回傳 `None`。

        Args:
            activity: 活動。
            requester: 已解析的身分。

        Returns:
            快照或 `None`。
        """
        if ActivityStateMachine.is_teacher(activity, requester):
            return self._extend(
                SnapshotView.for_teacher(activity), activity, TeacherViewer()
            )
        if isinstance(requester, Device):
            device = activity.devices.get(requester.token_hash)
            if device is not None:
                return self._extend(
                    SnapshotView.for_group(activity, device.group_number),
                    activity,
                    GroupViewer(device.group_number),
                )
        return None

    def _extend(
        self,
        snapshot: ActivitySnapshot,
        activity: Activity,
        viewer: TeacherViewer | GroupViewer,
    ) -> ActivitySnapshot:
        if not self._extensions:
            return snapshot
        extra = dict(snapshot.extra)
        for extension in self._extensions:
            extra.update(extension(activity, viewer))
        return dataclasses.replace(snapshot, extra=extra)

    def current_round(self, code: str) -> Round | None:
        """目前輪次（給 004）。

        Args:
            code: 活動代碼。

        Returns:
            目前輪次；活動不存在或沒有輪次時為 `None`。
        """
        activity = self.get(code)
        return activity.current_round if activity else None

    def accepts_submission(self, code: str, now: datetime) -> bool:
        """此刻是否接受提交（給 003）：搶答中，且沒有截止時間或尚未截止。

        Args:
            code: 活動代碼。
            now: 提交到達的時間。

        Returns:
            接受時為 True。
        """
        activity = self.get(code)
        if activity is None or activity.stage is not Stage.ROUND_OPEN:
            return False
        current = activity.current_round
        return current is not None and not ActivityStateMachine.is_deadline_passed(
            current, now
        )

    def export_view(self, code: str, requester: Requester) -> Outcome[ExportView]:
        """匯出用資料（給 005）：只限老師，已取消的活動一律拒絕。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            匯出資料，或拒絕原因。
        """
        activity = self.get(code)
        if activity is None:
            return _gone()
        if not ActivityStateMachine.is_teacher(activity, requester):
            reason = RejectionReason.NOT_TEACHER
            return Outcome(ok=False, rejection=reason, message=reason.default_message)
        if activity.stage is Stage.CANCELLED:
            return Outcome(
                ok=False,
                rejection=RejectionReason.STAGE_NOT_ALLOWED,
                message="活動已取消，不提供寫回與 CSV 下載。",
            )
        view = ExportView(
            code=activity.code,
            stage=activity.stage,
            question_numbers=activity.question_numbers,
            solved_questions=activity.solved_questions,
            unsolved_questions=activity.unsolved_questions,
            groups=tuple(g for _, g in sorted(activity.groups.items())),
        )
        return Outcome(ok=True, value=view)

    # ── 會改變狀態的操作 ─────────────────────────────────

    async def create(
        self,
        max_groups_raw: object,
        teacher_token: str | None = None,
        idempotency_key: str | None = None,
    ) -> Outcome[CreatedActivity]:
        """建立活動；同一個 key 重送時回傳同一組代碼與 token。

        順序：重送查表 → 同一位老師只能有一個存續中活動（C7，研究 R10）→ 狀態機
        驗證組數上限。三者都在建立鎖內。

        Args:
            max_groups_raw: 組數上限的原始輸入。
            teacher_token: 這個瀏覽器上一個活動的老師 token（可無）。
            idempotency_key: 前端送來的 key。

        Returns:
            活動代碼、老師 token（只出現這一次）、組數上限與版本；或拒絕原因。
        """
        async with self._registry.create_lock:
            if idempotency_key is not None:
                cached = self._registry.recall_create(idempotency_key)
                if isinstance(cached, CreatedActivity):
                    return Outcome(ok=True, value=cached)
            if teacher_token:
                previous = self._registry.find_by_teacher(hash_token(teacher_token))
                if previous is not None and not previous.stage.is_terminal:
                    reason = RejectionReason.TEACHER_HAS_ACTIVE_ACTIVITY
                    return Outcome(
                        ok=False,
                        rejection=reason,
                        message=(
                            f"你已有一個進行中的活動（代碼 {previous.code}），"
                            "請先結束或取消它。"
                        ),
                    )
            token = new_token()
            issued = IssuedSecrets(
                activity_code=new_code(self._registry.codes()),
                teacher_token_hash=hash_token(token),
            )
            transition = ActivityStateMachine.apply(
                None,
                CreateActivity(Anonymous(), max_groups_raw),
                self._clock.now(),
                issued,
            )
            if not transition.ok or transition.activity is None:
                assert transition.rejection is not None
                return Outcome(
                    ok=False,
                    rejection=transition.rejection,
                    message=transition.rejection.default_message,
                )
            created = transition.activity
            self._registry.put(created)
            result = CreatedActivity(
                created.code, token, created.max_groups, created.version
            )
            if idempotency_key is not None:
                self._registry.remember_create(idempotency_key, result)
        logger.info("建立活動 activity=%s", result.code)
        return Outcome(ok=True, value=result)

    async def join(
        self,
        code: str,
        number_raw: object,
        credential_raw: object = None,
        requester: Requester | None = None,
        idempotency_key: str | None = None,
        *,
        browser_key: str,
    ) -> Outcome[JoinedDevice]:
        """以組號加入組別（US2）；新組號建立組別並發憑證，既有組號比對憑證。

        007 起裝置 token 就是瀏覽器金鑰（research R2）：由呼叫端從 cookie（或 Bearer）
        取得後傳入，`hash_token(browser_key)` 即這個瀏覽器在本活動的裝置雜湊。

        Args:
            code: 活動代碼。
            number_raw: 組號的原始輸入。
            credential_raw: 組別加入憑證的原始輸入。
            requester: 已解析的身分；已是某組成員的裝置會被拒絕。
            idempotency_key: 前端送來的 key。
            browser_key: 這個瀏覽器的金鑰。

        Returns:
            組號、該組憑證與版本（金鑰不回傳）。
        """
        device_hash = hash_token(browser_key)
        issued = IssuedSecrets(
            device_token_hash=device_hash, group_credential=new_credential()
        )

        def build(t: Transition, activity: Activity) -> JoinedDevice:
            device = activity.devices[device_hash]
            group = activity.groups[device.group_number]
            return JoinedDevice(group.number, group.join_credential, activity.version)

        return await self._execute(
            code,
            JoinGroup(
                requester or Anonymous(),
                number_raw,
                credential_raw,
                device_token_hash=device_hash,
            ),
            idempotency_key,
            build,
            issued=issued,
        )

    def resolve_device(self, code: str, device_token: str) -> Outcome[DeviceContext]:
        """依裝置 token 取得所屬組別與目前輪次（給 003）。

        Args:
            code: 活動代碼。
            device_token: 原始裝置 token。

        Returns:
            裝置資訊；活動不存在回傳 `ACTIVITY_GONE`，token 無效回傳 `NOT_IN_GROUP`。
        """
        activity = self.get(code)
        if activity is None:
            return _gone()
        device = activity.devices.get(hash_token(device_token))
        if device is None:
            reason = RejectionReason.NOT_IN_GROUP
            return Outcome(ok=False, rejection=reason, message=reason.default_message)
        current = activity.current_round
        is_open = activity.stage is Stage.ROUND_OPEN and current is not None
        context = DeviceContext(
            group_number=device.group_number,
            stage=activity.stage,
            round_number=current.number if current else None,
            open_questions=current.rules.question_numbers
            if is_open and current
            else (),
            deadline=current.rules.deadline if is_open and current else None,
        )
        return Outcome(ok=True, value=context)

    async def leave_group(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> Outcome[int]:
        """學生裝置離開本組（US7）；成功後通知該裝置的連線並關閉。

        Args:
            code: 活動代碼。
            requester: 已解析的身分（必須是本活動的裝置）。
            idempotency_key: 前端送來的 key。

        Returns:
            新版本號；搶答中回傳 `NO_GROUP_SWITCH_DURING_ROUND`。
        """
        departed: list[str] = []
        outcome = await self._execute(
            code,
            LeaveGroup(requester),
            idempotency_key,
            lambda t, a: a.version,
            on_removed_devices=departed.extend,
        )
        await self._disconnect(code, departed, "LEFT_GROUP")
        return outcome

    async def delete_group(
        self,
        code: str,
        requester: Requester,
        number_raw: object,
        idempotency_key: str | None = None,
    ) -> Outcome[int]:
        """老師刪除沒有提交紀錄的組別（US7）；原組裝置收到 GROUP_DELETED。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            number_raw: 組號的原始輸入。
            idempotency_key: 前端送來的 key。

        Returns:
            新版本號，或拒絕原因。
        """
        removed: list[str] = []
        outcome = await self._execute(
            code,
            DeleteGroup(requester, number_raw),
            idempotency_key,
            lambda t, a: a.version,
            on_removed_devices=removed.extend,
        )
        await self._disconnect(code, removed, "GROUP_DELETED")
        return outcome

    async def mark_group_submitted(self, code: str, group_number: int) -> Outcome[int]:
        """標記組別已有提交紀錄（給 003）；與刪除組別在同一把鎖內依序處理。

        Args:
            code: 活動代碼。
            group_number: 組號。

        Returns:
            版本號；不在搶答中或組別不存在時回傳拒絕原因。
        """
        return await self._execute(
            code,
            MarkGroupSubmitted(System(), group_number),
            None,
            lambda t, a: a.version,
        )

    async def record_submission(
        self, code: str, device_token: str, handler: SubmissionHandler[T]
    ) -> Outcome[T]:
        """在同一把活動鎖內判定並記錄一筆提交（給 003，003 研究 R2）。

        鎖內順序：找裝置與組號 → 取一次 `now` → 組 `SubmissionWindow` →
        `handler.decide` → 若為 `accept`：套用 `RecordSubmission`，成功才呼叫
        `handler.commit`。鎖外推送。關輪與倒數截止走同一把鎖，所以結果公開後
        不會再加入本輪提交（003 FR-019）。

        Args:
            code: 活動代碼。
            device_token: 原始裝置 token。
            handler: 003 的處理器。

        Returns:
            `handler` 給的值；活動不存在、token 無效或記錄被拒時回傳拒絕原因。
        """
        code = normalize_code_input(code)
        changed_activity: Activity | None = None
        async with self._registry.lock(code):
            activity = self._registry.get(code)
            if activity is None:
                return _gone()
            device = activity.devices.get(hash_token(device_token))
            if device is None:
                reason = RejectionReason.NOT_IN_GROUP
                return Outcome(
                    ok=False, rejection=reason, message=reason.default_message
                )
            now = self._clock.now()
            step = handler.decide(self._window(activity, device.group_number, now), now)
            if step.kind == "accept":
                transition = ActivityStateMachine.apply(
                    activity, RecordSubmission(System(), device.group_number), now
                )
                if not transition.ok:
                    assert transition.rejection is not None
                    return Outcome(
                        ok=False,
                        rejection=transition.rejection,
                        message=transition.rejection.default_message,
                    )
                assert transition.activity is not None
                self._registry.put(transition.activity)
                handler.commit()
                changed_activity = transition.activity
        if changed_activity is not None:
            await self._publish(changed_activity)
        return Outcome(ok=True, value=step.value)

    @staticmethod
    def _window(
        activity: Activity, group_number: int, now: datetime
    ) -> SubmissionWindow:
        current = activity.current_round
        is_open = activity.stage is Stage.ROUND_OPEN and current is not None
        return SubmissionWindow(
            group_number=group_number,
            stage=activity.stage,
            round_number=current.number if current else None,
            open_questions=current.rules.question_numbers
            if is_open and current
            else (),
            deadline=current.rules.deadline if is_open and current else None,
            accepting=is_open
            and current is not None
            and not ActivityStateMachine.is_deadline_passed(current, now),
        )

    async def open_joining(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> Outcome[int]:
        """老師開放加入：準備中 → 開放加入（須已匯入題目），學生才能開始加入組別。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            idempotency_key: 前端送來的 key。

        Returns:
            新版本號；沒有題目時回傳 `NO_QUESTIONS`。
        """
        return await self._execute(
            code,
            OpenJoining(requester),
            idempotency_key,
            lambda t, a: a.version,
        )

    async def replace_questions(
        self, code: str, requester: Requester, question_numbers: tuple[int, ...]
    ) -> Outcome[int]:
        """以整份新題號取代舊的（`ActivityGateway`，給 002）。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            question_numbers: 新題號。

        Returns:
            成功時為新版本號；被拒時既有題目完全不變。
        """
        return await self._execute(
            code,
            ReplaceQuestions(requester, tuple(question_numbers)),
            None,
            lambda t, a: a.version,
        )

    async def open_round(
        self,
        code: str,
        requester: Requester,
        question_numbers: tuple[int, ...] | None = None,
        fair_mode: bool = False,
        countdown_raw: object = None,
        idempotency_key: str | None = None,
    ) -> Outcome[RoundOpened]:
        """開輪；有截止時間時排程倒數。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            question_numbers: 所選題號；`None` 表示全部未成功題。
            fair_mode: 公平模式。
            countdown_raw: 倒數秒數的原始輸入。
            idempotency_key: 前端送來的 key。

        Returns:
            輪次編號、截止時間與版本。
        """

        def build(t: Transition, activity: Activity) -> RoundOpened:
            current = activity.current_round
            assert current is not None
            return RoundOpened(current.number, current.rules.deadline, activity.version)

        def schedule(activity: Activity) -> None:
            current = activity.current_round
            if current is not None and current.rules.deadline is not None:
                self._scheduler.schedule(activity.code, current.rules.deadline)

        command = OpenRound(requester, question_numbers, fair_mode, countdown_raw)
        return await self._execute(
            code, command, idempotency_key, build, on_change=schedule
        )

    async def close_round(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> Outcome[RoundClosed]:
        """老師手動關輪；已關過時回傳 `already_closed=True`、版本不變。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            idempotency_key: 前端送來的 key。

        Returns:
            輪次編號、版本與是否已關過。
        """
        return await self._close(code, CloseRound(requester), idempotency_key)

    async def on_deadline(self, code: str, deadline: datetime) -> None:
        """倒數到期回呼：以 `max(clock.now(), deadline)` 當作 `now` 關輪。

        計時器可能比牆上時鐘早幾毫秒觸發；用截止時間當下限，輪次才一定會關閉
        （PR #15 審查第 3 項）。

        Args:
            code: 活動代碼。
            deadline: 排程時的截止時間。
        """
        now = max(self._clock.now(), deadline)
        await self._close(code, CloseRound(System()), None, now=now)

    async def finalize(
        self,
        code: str,
        requester: Requester,
        outcome: FinalizeOutcome | None = None,
        idempotency_key: str | None = None,
    ) -> Outcome[int]:
        """確認定案（004 會傳入定案結果；001 預設為空）。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            outcome: 定案結果。
            idempotency_key: 前端送來的 key。

        Returns:
            新版本號。
        """
        command = Finalize(requester, outcome or FinalizeOutcome())
        return await self._execute(
            code, command, idempotency_key, lambda t, a: a.version
        )

    async def end(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> Outcome[ActivityEnded]:
        """結束活動。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            idempotency_key: 前端送來的 key。

        Returns:
            版本與未成功題。
        """

        def build(t: Transition, activity: Activity) -> ActivityEnded:
            return ActivityEnded(activity.version, activity.unsolved_questions)

        return await self._execute(
            code,
            EndActivity(requester),
            idempotency_key,
            build,
            on_change=lambda a: self._scheduler.cancel(a.code),
        )

    async def cancel(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> Outcome[int]:
        """取消活動。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            idempotency_key: 前端送來的 key。

        Returns:
            新版本號。
        """
        return await self._execute(
            code,
            CancelActivity(requester),
            idempotency_key,
            lambda t, a: a.version,
            on_change=lambda a: self._scheduler.cancel(a.code),
        )

    # ── 內部 ─────────────────────────────────────────────

    async def _close(
        self,
        code: str,
        command: CloseRound,
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> Outcome[RoundClosed]:
        def build(t: Transition, activity: Activity) -> RoundClosed:
            current = activity.current_round
            assert current is not None
            return RoundClosed(current.number, activity.version, not t.changed)

        return await self._execute(
            code,
            command,
            idempotency_key,
            build,
            now=now,
            on_change=lambda a: self._scheduler.cancel(a.code),
        )

    async def _execute(
        self,
        code: str,
        command: Command,
        idempotency_key: str | None,
        build: Callable[[Transition, Activity], T],
        *,
        now: datetime | None = None,
        issued: IssuedSecrets | None = None,
        on_change: Callable[[Activity], None] | None = None,
        on_removed_devices: Callable[[list[str]], None] | None = None,
    ) -> Outcome[T]:
        code = normalize_code_input(code)
        if self._registry.get(code) is None:
            return _gone()
        key = (
            ProcessedKey(_idempotency_identity(command), idempotency_key)
            if idempotency_key
            else None
        )
        changed_activity: Activity | None = None
        async with self._registry.lock(code):
            if key is not None:
                cached = self._registry.recall(code, key)
                if isinstance(cached, Outcome):
                    return cached
            activity = self._registry.get(code)
            if activity is None:
                return _gone()
            transition = ActivityStateMachine.apply(
                activity, command, now or self._clock.now(), issued
            )
            result_activity = transition.activity or activity
            if transition.ok:
                if transition.changed:
                    self._registry.put(result_activity)
                    changed_activity = result_activity
                    if on_change is not None:
                        on_change(result_activity)
                    if on_removed_devices is not None:
                        on_removed_devices(
                            [
                                h
                                for h in activity.devices
                                if h not in result_activity.devices
                            ]
                        )
                outcome: Outcome[T] = Outcome(
                    ok=True, value=build(transition, result_activity)
                )
            else:
                assert transition.rejection is not None
                outcome = Outcome(
                    ok=False,
                    rejection=transition.rejection,
                    message=describe_rejection(
                        transition.rejection, activity.stage, command, activity
                    ),
                )
            if key is not None:
                self._registry.remember(code, key, outcome)
        if changed_activity is not None:
            await self._publish(changed_activity)
        return outcome

    async def _disconnect(
        self, code: str, token_hashes: list[str], reason: DisconnectReason
    ) -> None:
        for token_hash in token_hashes:
            try:
                await self._publisher.disconnect_device(
                    normalize_code_input(code), token_hash, reason
                )
            except Exception:
                logger.exception("通知裝置失去身分失敗 activity=%s", code)

    async def _publish(self, activity: Activity) -> None:
        try:
            await self._publisher.publish(activity)
        except Exception:
            logger.exception("推送失敗 activity=%s", activity.code)
