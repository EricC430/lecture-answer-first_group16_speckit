"""狀態機的輸入：操作者（Actor）與操作（Command）。

身分由服務層解析：服務層把 token 轉成雜湊後才放進 Actor，核心只比對雜湊。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from lecture_quiz.core.activity.models import freeze


@dataclass(frozen=True)
class Teacher:
    """以老師 token 送出的請求。

    Attributes:
        token_hash: 老師 token 的 SHA-256。
    """

    token_hash: str


@dataclass(frozen=True)
class Device:
    """以學生裝置 token 送出的請求。

    Attributes:
        token_hash: 裝置 token 的 SHA-256。
    """

    token_hash: str


@dataclass(frozen=True)
class System:
    """系統自身（倒數排程）送出的操作。"""


@dataclass(frozen=True)
class Anonymous:
    """沒有任何有效身分的請求。"""


Actor = Teacher | Device | System | Anonymous


def _no_increments() -> MappingProxyType[int, int]:
    return MappingProxyType({})


@dataclass(frozen=True)
class FinalizeOutcome:
    """定案結果，由 004 計算後提供。

    Attributes:
        solved_questions: 本輪新成功的題號。
        success_increments: 各組成功次數增量，key 為組號。
    """

    solved_questions: frozenset[int] = frozenset()
    success_increments: Mapping[int, int] = field(default_factory=_no_increments)

    def __post_init__(self) -> None:
        """把增量表轉成唯讀，避免呼叫端事後修改。"""
        object.__setattr__(self, "success_increments", freeze(self.success_increments))


@dataclass(frozen=True)
class CreateActivity:
    """建立活動。代碼與老師 token 雜湊由 `IssuedSecrets` 傳入。

    Attributes:
        actor: 操作者。
        max_groups_raw: 組數上限的原始輸入，由 `InputRules` 驗證（FR-036）。
    """

    actor: Actor
    max_groups_raw: object = None


@dataclass(frozen=True)
class JoinGroup:
    """以組號加入組別（US2）。

    Attributes:
        actor: 操作者；已是某組成員的 `Device` 會被拒絕。
        number_raw: 組號的原始輸入，由 `InputRules.normalize_group_number` 正規化。
        credential_raw: 組別加入憑證的原始輸入（加入既有組時必填）。
    """

    actor: Actor
    number_raw: object
    credential_raw: object = None


@dataclass(frozen=True)
class OpenJoining:
    """老師開放加入：準備中 → 開放加入，學生才能開始加入組別（須已匯入題目）。

    Attributes:
        actor: 操作者。
    """

    actor: Actor


@dataclass(frozen=True)
class LeaveGroup:
    """學生裝置離開本組（US7，alignment 2026-11-23 B4）。"""

    actor: Actor


@dataclass(frozen=True)
class DeleteGroup:
    """老師刪除沒有提交紀錄的組別（US7，alignment 2026-11-23 B5）。

    Attributes:
        actor: 操作者。
        number_raw: 組號的原始輸入，由 `InputRules.normalize_group_number` 正規化。
    """

    actor: Actor
    number_raw: object


@dataclass(frozen=True)
class MarkGroupSubmitted:
    """標記組別已有提交紀錄（由 003 在接受提交時呼叫，只在搶答中生效）。

    Attributes:
        actor: 操作者（系統）。
        group_number: 組號。
    """

    actor: Actor
    group_number: int


@dataclass(frozen=True)
class OpenRound:
    """開輪。

    Attributes:
        actor: 操作者。
        question_numbers: 所選題號；`None` 表示全部未成功題。
        fair_mode: 公平模式。
        countdown_raw: 倒數秒數的原始輸入，由 `InputRules` 驗證。
    """

    actor: Actor
    question_numbers: tuple[int, ...] | None = None
    fair_mode: bool = False
    countdown_raw: object = None


@dataclass(frozen=True)
class CloseRound:
    """關輪（老師手動或倒數截止）。"""

    actor: Actor


@dataclass(frozen=True)
class Finalize:
    """確認定案本輪結果。

    Attributes:
        actor: 操作者。
        outcome: 定案結果（由 004 提供；001 預設為空）。
    """

    actor: Actor
    outcome: FinalizeOutcome = field(default_factory=FinalizeOutcome)


@dataclass(frozen=True)
class EndActivity:
    """結束活動。"""

    actor: Actor


@dataclass(frozen=True)
class CancelActivity:
    """取消活動。"""

    actor: Actor


@dataclass(frozen=True)
class ReplaceQuestions:
    """以整份新題號取代舊題號（002 成功匯入時呼叫）。

    Attributes:
        actor: 操作者。
        question_numbers: 新的題號。
    """

    actor: Actor
    question_numbers: tuple[int, ...]


Command = (
    CreateActivity
    | OpenJoining
    | JoinGroup
    | LeaveGroup
    | DeleteGroup
    | MarkGroupSubmitted
    | OpenRound
    | CloseRound
    | Finalize
    | EndActivity
    | CancelActivity
    | ReplaceQuestions
)
