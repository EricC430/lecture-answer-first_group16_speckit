"""活動的核心資料（data-model.md「實體」）。

全部是不可變的 frozen dataclass；狀態變更一律產生新物件。集合欄位使用 `tuple`、
`frozenset` 與 `MappingProxyType`。時間欄位都是有時區的 `datetime`，由呼叫端傳入。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, TypeVar

CloseCause = Literal["teacher", "deadline"]
K = TypeVar("K")
V = TypeVar("V")


def freeze(mapping: Mapping[K, V]) -> MappingProxyType[K, V]:
    """把對照表複製成唯讀的 `MappingProxyType`。

    Args:
        mapping: 來源對照表。

    Returns:
        內容相同、不可修改的對照表。
    """
    return MappingProxyType(dict(mapping))


class Stage(StrEnum):
    """活動階段（spec「活動階段狀態機」）。"""

    PREPARING = "PREPARING"
    ROUND_OPEN = "ROUND_OPEN"
    RESULT_PENDING = "RESULT_PENDING"
    RESULT_FINAL = "RESULT_FINAL"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        """是否為終止階段（已結束、已取消）。"""
        return self in (Stage.ENDED, Stage.CANCELLED)

    @property
    def label(self) -> str:
        """給使用者看的中文名稱。"""
        return _STAGE_LABELS[self]


_STAGE_LABELS = {
    Stage.PREPARING: "準備中",
    Stage.ROUND_OPEN: "搶答中",
    Stage.RESULT_PENDING: "結果未定案",
    Stage.RESULT_FINAL: "結果已定案",
    Stage.ENDED: "已結束",
    Stage.CANCELLED: "已取消",
}


@dataclass(frozen=True)
class TeacherIdentity:
    """老師身分；只保存 token 的 SHA-256。

    Attributes:
        token_hash: 老師 token 的 SHA-256（十六進位）。
    """

    token_hash: str


@dataclass(frozen=True)
class Group:
    """組別，以組號識別（alignment 2026-11-23 A1）。

    Attributes:
        number: 組號，1～`Activity.max_groups`。
        join_credential: 6 碼組別加入憑證（由服務層產生）。
        success_count: 歷史成功次數，只由定案增加。
        has_submissions: 是否已有提交紀錄（由 003 標記）。
    """

    number: int
    join_credential: str
    success_count: int = 0
    has_submissions: bool = False


@dataclass(frozen=True)
class DeviceIdentity:
    """學生裝置身分。

    Attributes:
        token_hash: 裝置 token 的 SHA-256。
        group_number: 所屬組號。
    """

    token_hash: str
    group_number: int


@dataclass(frozen=True)
class RoundRules:
    """開輪時固定的規則快照，開輪後不可變。

    Attributes:
        question_numbers: 本輪所選題號（至少 1 題，皆未成功）。
        fair_mode: 公平模式，預設關閉。
        countdown_seconds: 倒數秒數；`None` 表示不倒數。
        deadline: 截止時間；沒有倒數時為 `None`。
    """

    question_numbers: tuple[int, ...]
    fair_mode: bool
    countdown_seconds: int | None
    deadline: datetime | None


@dataclass(frozen=True)
class Round:
    """一個輪次。

    Attributes:
        number: 輪次編號，從 1 開始。
        rules: 規則快照。
        opened_at: 開輪時間。
        baseline: 開輪當下各組（key 為組號）的歷史成功次數。
        closed: 是否已關輪（只能由 False 變成 True 一次）。
        closed_at: 關輪時間。
        close_cause: 先生效的關輪來源。
    """

    number: int
    rules: RoundRules
    opened_at: datetime
    baseline: Mapping[int, int]
    closed: bool = False
    closed_at: datetime | None = None
    close_cause: CloseCause | None = None


@dataclass(frozen=True)
class Activity:
    """一次課堂搶答活動。

    Attributes:
        code: 6 碼活動代碼。
        stage: 目前階段。
        version: 狀態版本，從 1 開始，每次真正變更加 1。
        changed_at: 最近一次狀態變更時間。
        teacher: 老師身分。
        max_groups: 組數上限 N（1～99），建立後不變。
        question_numbers: 題號（由 002 的成功匯入提供）。
        solved_questions: 已成功題號（由定案結果提供）。
        groups: 組別，key 為組號。
        devices: 學生裝置，key 為裝置 token 的雜湊。
        rounds: 輪次，最後一個是目前輪次。
    """

    code: str
    stage: Stage
    version: int
    changed_at: datetime
    teacher: TeacherIdentity
    max_groups: int
    question_numbers: tuple[int, ...] = ()
    solved_questions: frozenset[int] = frozenset()
    groups: Mapping[int, Group] = field(default_factory=lambda: freeze({}))
    devices: Mapping[str, DeviceIdentity] = field(default_factory=lambda: freeze({}))
    rounds: tuple[Round, ...] = ()

    @property
    def current_round(self) -> Round | None:
        """目前輪次；還沒開過輪時為 `None`。"""
        return self.rounds[-1] if self.rounds else None

    @property
    def unsolved_questions(self) -> tuple[int, ...]:
        """尚未成功的題號，保留匯入時的順序。"""
        return tuple(q for q in self.question_numbers if q not in self.solved_questions)
