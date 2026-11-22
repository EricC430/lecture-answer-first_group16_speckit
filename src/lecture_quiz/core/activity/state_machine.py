"""活動狀態機：`apply(activity, command, now)` 是確定性的純函式（FR-032）。

檢查順序（data-model.md「狀態轉移」）：
1. 活動已終止 → `STAGE_NOT_ALLOWED`。
2. 權限 → `NOT_TEACHER`。
3. 階段與操作是否相容 → `STAGE_NOT_ALLOWED`（或 `RULES_LOCKED`）。
4. 輸入 → `InputRules`。
5. 業務條件。
"""

import dataclasses
import hmac
from collections.abc import Callable
from datetime import datetime, timedelta

from lecture_quiz.core.activity.commands import (
    CancelActivity,
    CloseRound,
    Command,
    CreateActivity,
    EndActivity,
    Finalize,
    JoinGroup,
    OpenRound,
    ReplaceQuestions,
    System,
    Teacher,
)
from lecture_quiz.core.activity.input_rules import InputRules, InvalidInputError
from lecture_quiz.core.activity.models import (
    Activity,
    DeviceIdentity,
    Group,
    Round,
    RoundRules,
    Stage,
    TeacherIdentity,
    freeze,
)
from lecture_quiz.core.activity.results import (
    IssuedSecrets,
    RejectionReason,
    Transition,
)

_NON_TERMINAL = frozenset(s for s in Stage if not s.is_terminal)

# 「階段 × 操作」相容表（spec 兩張表）。CloseRound 另外處理「已關輪」的冪等成功。
_ALLOWED_STAGES: dict[type, frozenset[Stage]] = {
    JoinGroup: _NON_TERMINAL,
    OpenRound: frozenset({Stage.PREPARING, Stage.RESULT_FINAL}),
    CloseRound: frozenset({Stage.ROUND_OPEN}),
    Finalize: frozenset({Stage.RESULT_PENDING}),
    EndActivity: frozenset({Stage.RESULT_FINAL}),
    CancelActivity: frozenset({Stage.PREPARING}),
    ReplaceQuestions: frozenset({Stage.PREPARING}),
}

# 只有本活動老師能執行的操作（FR-004）。CloseRound 也允許 System（倒數）。
_TEACHER_ONLY = (
    OpenRound,
    CloseRound,
    Finalize,
    EndActivity,
    CancelActivity,
    ReplaceQuestions,
)

Handler = Callable[[Activity, Command, datetime, IssuedSecrets | None], Transition]


def _reject(activity: Activity, reason: RejectionReason) -> Transition:
    return Transition(ok=False, activity=activity, changed=False, rejection=reason)


def _unchanged(activity: Activity) -> Transition:
    return Transition(ok=True, activity=activity, changed=False)


def _changed(activity: Activity, issued: IssuedSecrets | None = None) -> Transition:
    return Transition(ok=True, activity=activity, changed=True, issued=issued)


class ActivityStateMachine:
    """活動階段狀態機；所有方法都是純函式。"""

    @staticmethod
    def is_teacher(activity: Activity, actor: object) -> bool:
        """`actor` 是否為這個活動的老師（以雜湊比對）。

        Args:
            activity: 活動。
            actor: 操作者。

        Returns:
            是本活動老師時為 True。
        """
        return isinstance(actor, Teacher) and hmac.compare_digest(
            actor.token_hash, activity.teacher.token_hash
        )

    @staticmethod
    def is_deadline_passed(round_: Round, now: datetime) -> bool:
        """本輪是否已到截止時間；沒有倒數時永遠為 False。

        Args:
            round_: 輪次。
            now: 呼叫端傳入的時間。

        Returns:
            `deadline` 不為 `None` 且 `now >= deadline` 時為 True。
        """
        deadline = round_.rules.deadline
        return deadline is not None and now >= deadline

    @staticmethod
    def apply(
        activity: Activity | None,
        command: Command,
        now: datetime,
        issued: IssuedSecrets | None = None,
    ) -> Transition:
        """套用一個操作。

        Args:
            activity: 目前狀態；建立活動時為 `None`。
            command: 操作。
            now: 呼叫端傳入的時間（核心不讀系統時鐘）。
            issued: 服務層產生的新秘密（活動代碼、token 雜湊等）。

        Returns:
            `Transition`。成功且有變化時，`version` 加 1、`changed_at = now`。

        Raises:
            ValueError: 建立活動時缺少 `issued`，或其他操作時 `activity` 為 `None`。
        """
        if isinstance(command, CreateActivity):
            return _create(command, now, issued)
        if activity is None:
            raise ValueError("除了建立活動，其他操作都需要既有的活動")

        if activity.stage.is_terminal:
            return _reject(activity, RejectionReason.STAGE_NOT_ALLOWED)
        if isinstance(command, _TEACHER_ONLY):
            is_system_close = isinstance(command, CloseRound) and isinstance(
                command.actor, System
            )
            if not is_system_close and not ActivityStateMachine.is_teacher(
                activity, command.actor
            ):
                return _reject(activity, RejectionReason.NOT_TEACHER)

        if not _stage_allowed(activity, command):
            return _stage_rejection(activity, command)

        handler = _HANDLERS.get(type(command))
        if handler is None:
            return _reject(activity, RejectionReason.STAGE_NOT_ALLOWED)
        transition = handler(activity, command, now, issued)
        if transition.ok and transition.changed and transition.activity is not None:
            bumped = dataclasses.replace(
                transition.activity, version=activity.version + 1, changed_at=now
            )
            return dataclasses.replace(transition, activity=bumped)
        return transition


def _stage_allowed(activity: Activity, command: Command) -> bool:
    return activity.stage in _ALLOWED_STAGES.get(type(command), frozenset())


def _stage_rejection(activity: Activity, command: Command) -> Transition:
    """階段不相容時的結果；部分組合有專屬的拒絕原因或冪等成功。"""
    if isinstance(command, OpenRound) and activity.stage is Stage.ROUND_OPEN:
        return _reject(activity, RejectionReason.RULES_LOCKED)
    if isinstance(command, CloseRound):
        current = activity.current_round
        if current is not None and current.closed:
            # 已關輪：冪等成功、不改變狀態（FR-019；PR #15 審查第 1 項）
            return _unchanged(activity)
    return _reject(activity, RejectionReason.STAGE_NOT_ALLOWED)


def _create(
    command: CreateActivity, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    if issued is None or not issued.activity_code or not issued.teacher_token_hash:
        raise ValueError("建立活動需要服務層傳入活動代碼與老師 token 雜湊")
    activity = Activity(
        code=issued.activity_code,
        stage=Stage.PREPARING,
        version=1,
        changed_at=now,
        teacher=TeacherIdentity(issued.teacher_token_hash),
    )
    return Transition(ok=True, activity=activity, changed=True, issued=issued)


def _join_group(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """最小的組別加入：組別不存在就建立，並登記裝置（US2 會改為組號＋憑證）。"""
    assert isinstance(command, JoinGroup)
    if issued is None or not issued.device_token_hash:
        raise ValueError("加入組別需要服務層傳入裝置 token 雜湊")
    groups = dict(activity.groups)
    groups.setdefault(command.group_name, Group(command.group_name))
    devices = dict(activity.devices)
    devices[issued.device_token_hash] = DeviceIdentity(
        issued.device_token_hash, command.group_name
    )
    updated = dataclasses.replace(
        activity, groups=freeze(groups), devices=freeze(devices)
    )
    return _changed(updated, issued)


def _open_round(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """開輪：驗證輸入、固定規則快照、保存各組成功次數基準（FR-013～017）。"""
    assert isinstance(command, OpenRound)
    if activity.stage is Stage.PREPARING and not activity.question_numbers:
        return _reject(activity, RejectionReason.NO_QUESTIONS)
    try:
        countdown = InputRules.validate_countdown(command.countdown_raw)
        selected = InputRules.validate_selection(
            command.question_numbers,
            activity.question_numbers,
            activity.solved_questions,
        )
    except InvalidInputError as exc:
        return _reject(activity, exc.reason)
    deadline = now + timedelta(seconds=countdown) if countdown is not None else None
    rules = RoundRules(selected, bool(command.fair_mode), countdown, deadline)
    baseline = freeze({name: g.success_count for name, g in activity.groups.items()})
    new_round = Round(len(activity.rounds) + 1, rules, now, baseline)
    updated = dataclasses.replace(
        activity, stage=Stage.ROUND_OPEN, rounds=(*activity.rounds, new_round)
    )
    return _changed(updated)


def _replace_questions(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """以整份新題號取代舊的；被拒時既有題目完全不變（原則 III）。"""
    assert isinstance(command, ReplaceQuestions)
    try:
        numbers = InputRules.validate_question_numbers(command.question_numbers)
    except InvalidInputError as exc:
        return _reject(activity, exc.reason)
    updated = dataclasses.replace(
        activity, question_numbers=numbers, solved_questions=frozenset()
    )
    return _changed(updated)


def _close_round(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """關輪：老師立即生效；System（倒數）只在 now >= deadline 時生效（FR-019）。"""
    assert isinstance(command, CloseRound)
    current = activity.current_round
    assert current is not None  # 搶答中必定有目前輪次
    is_system = isinstance(command.actor, System)
    if is_system and not ActivityStateMachine.is_deadline_passed(current, now):
        # 防止排程誤觸發：成功但不改變狀態
        return _unchanged(activity)
    closed = dataclasses.replace(
        current,
        closed=True,
        closed_at=now,
        close_cause="deadline" if is_system else "teacher",
    )
    updated = dataclasses.replace(
        activity, stage=Stage.RESULT_PENDING, rounds=(*activity.rounds[:-1], closed)
    )
    return _changed(updated)


def _finalize(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """定案：套用 004 提供的結果（新成功題、各組成功次數增量）（FR-020）。"""
    assert isinstance(command, Finalize)
    current = activity.current_round
    assert current is not None
    outcome = command.outcome
    increments = dict(outcome.success_increments)
    if (
        not outcome.solved_questions <= set(current.rules.question_numbers)
        or not set(increments) <= set(activity.groups)
        or any(not isinstance(v, int) or v < 0 for v in increments.values())
    ):
        return _reject(activity, RejectionReason.INVALID_SELECTION)
    groups = {
        name: dataclasses.replace(
            g, success_count=g.success_count + increments.get(name, 0)
        )
        for name, g in activity.groups.items()
    }
    updated = dataclasses.replace(
        activity,
        stage=Stage.RESULT_FINAL,
        solved_questions=activity.solved_questions | outcome.solved_questions,
        groups=freeze(groups),
    )
    return _changed(updated)


def _end_activity(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """結束活動（只允許結果已定案；可以仍有未成功題，FR-022）。"""
    return _changed(dataclasses.replace(activity, stage=Stage.ENDED))


def _cancel_activity(
    activity: Activity, command: Command, now: datetime, issued: IssuedSecrets | None
) -> Transition:
    """取消活動（只允許準備中，FR-025）。"""
    return _changed(dataclasses.replace(activity, stage=Stage.CANCELLED))


_HANDLERS: dict[type, Handler] = {
    JoinGroup: _join_group,
    OpenRound: _open_round,
    ReplaceQuestions: _replace_questions,
    CloseRound: _close_round,
    Finalize: _finalize,
    EndActivity: _end_activity,
    CancelActivity: _cancel_activity,
}
