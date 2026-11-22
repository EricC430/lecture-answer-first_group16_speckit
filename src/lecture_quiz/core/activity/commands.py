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


def _no_increments() -> MappingProxyType[str, int]:
    return MappingProxyType({})


@dataclass(frozen=True)
class FinalizeOutcome:
    """定案結果，由 004 計算後提供。

    Attributes:
        solved_questions: 本輪新成功的題號。
        success_increments: 各組成功次數增量。
    """

    solved_questions: frozenset[int] = frozenset()
    success_increments: Mapping[str, int] = field(default_factory=_no_increments)

    def __post_init__(self) -> None:
        """把增量表轉成唯讀，避免呼叫端事後修改。"""
        object.__setattr__(self, "success_increments", freeze(self.success_increments))


@dataclass(frozen=True)
class CreateActivity:
    """建立活動。代碼與老師 token 雜湊由 `IssuedSecrets` 傳入。"""

    actor: Actor


@dataclass(frozen=True)
class JoinGroup:
    """最小的組別加入入口（暫時版本）。

    US2 會依 alignment 2026-11-22 決議改為「組號＋組數上限」並加上組別加入憑證；
    目前只建立組別並登記裝置，不做組名正規化與憑證檢查，也沒有 HTTP 端點。

    Attributes:
        actor: 操作者。
        group_name: 組別識別。
    """

    actor: Actor
    group_name: str


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
    | JoinGroup
    | OpenRound
    | CloseRound
    | Finalize
    | EndActivity
    | CancelActivity
    | ReplaceQuestions
)
