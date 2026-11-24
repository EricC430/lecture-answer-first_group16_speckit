"""順位計算的核心資料型別（data-model.md「核心」）。

全部是不可變的 frozen dataclass；集合欄位使用 `tuple`、`frozenset` 與
`MappingProxyType`。核心不讀時鐘，時間資料只來自 `Candidate.received_at`。
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

K = TypeVar("K")
V = TypeVar("V")


def freeze_mapping(mapping: Mapping[K, V]) -> MappingProxyType[K, V]:
    """把對照表複製成唯讀的 `MappingProxyType`。

    Args:
        mapping: 來源對照表。

    Returns:
        內容相同、不可修改的對照表。
    """
    return MappingProxyType(dict(mapping))


class WinReason(StrEnum):
    """勝出（或排在前一名之後）的理由（research R9）。"""

    SOLE_CANDIDATE = "SOLE_CANDIDATE"
    EARLIER_SUBMISSION = "EARLIER_SUBMISSION"
    FEWER_SUCCESSES = "FEWER_SUCCESSES"
    BACKEND_ORDER = "BACKEND_ORDER"


class DisplayStatus(StrEnum):
    """每筆提交的顯示狀態。

    整題的「未成功」由 `QuestionRanking.success_group is None` 表示。

    `recompute` 只產生 `SUCCESS`、`WRONG`、`FAILED`；`CORRECT`（搶答正確）只在定案後
    由 `as_final` 產生（spec FR-033）。
    """

    SUCCESS = "SUCCESS"
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    FAILED = "FAILED"


def display_status(rank: int | None, wrong: bool) -> DisplayStatus:
    """依名次與是否被判錯推導顯示狀態（結果未定案）。

    Args:
        rank: 名次；被判錯者為 `None`。
        wrong: 是否被老師判錯。

    Returns:
        被判錯 → `WRONG`；名次 1 → `SUCCESS`；其餘 → `FAILED`。
    """
    if wrong:
        return DisplayStatus.WRONG
    if rank == 1:
        return DisplayStatus.SUCCESS
    return DisplayStatus.FAILED


@dataclass(frozen=True)
class Candidate:
    """一筆已被 003 接受的提交中，排名所需的欄位（答案不進核心）。

    Attributes:
        group_number: 組號。
        question_number: 題號。
        received_at: 後端接收時間。
        sequence: 後端接收序號，全活動唯一。
    """

    group_number: int
    question_number: int
    received_at: datetime
    sequence: int


@dataclass(frozen=True)
class RankingInput:
    """整輪重算的完整輸入。

    Attributes:
        question_numbers: 本輪題號清單。
        fair_mode: 是否公平模式（開輪時固定）。
        baseline: 組號 → 開輪時的成功次數；沒有的組視為 0。
        candidates: 本輪全部已接受的提交（每個（題號, 組號）最多一筆）。
        wrong_marks: 被判錯的（組號, 題號）集合。
    """

    question_numbers: tuple[int, ...]
    fair_mode: bool
    baseline: Mapping[int, int]
    candidates: tuple[Candidate, ...]
    wrong_marks: frozenset[tuple[int, int]] = frozenset()

    def __post_init__(self) -> None:
        """把基準轉成唯讀，避免呼叫端事後修改。"""
        object.__setattr__(self, "baseline", freeze_mapping(self.baseline))


@dataclass(frozen=True)
class RankEntry:
    """一個候選在某題的排名。

    Attributes:
        group_number: 組號。
        rank: 名次；被判錯者為 `None`。
        count_at_processing: 公平模式處理該題當下的成功次數；速度模式為 `None`。
        reason: 勝出（排在前一名之後）的理由；被判錯者為 `None`。
        wrong: 是否被老師判錯。
        display_status: 顯示狀態。
    """

    group_number: int
    rank: int | None
    count_at_processing: int | None
    reason: WinReason | None
    wrong: bool
    display_status: DisplayStatus


@dataclass(frozen=True)
class QuestionRanking:
    """某題的排名結果。

    Attributes:
        question_number: 題號。
        entries: 先放有名次者（名次由小到大），再放被判錯者（依接收時間、序號）。
        success_group: 搶答成功者的組號；沒有任何有名次者時為 `None`（未成功）。
    """

    question_number: int
    entries: tuple[RankEntry, ...]
    success_group: int | None


@dataclass(frozen=True)
class RoundResult:
    """整輪的結果。

    Attributes:
        order: 固定題序。
        rankings: 依題序排列的各題排名。
        group_counts: 各組處理完本輪後的暫算成功次數（基準加本輪成功題數）。
        wins: 各組本輪成功題數（定案時的 `success_increments`）。
    """

    order: tuple[int, ...]
    rankings: tuple[QuestionRanking, ...]
    group_counts: Mapping[int, int] = field(default_factory=dict)
    wins: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """把對照表轉成唯讀。"""
        object.__setattr__(self, "group_counts", freeze_mapping(self.group_counts))
        object.__setattr__(self, "wins", freeze_mapping(self.wins))

    def ranking_of(self, question_number: int) -> QuestionRanking | None:
        """取得某題的排名。

        Args:
            question_number: 題號。

        Returns:
            該題排名；題號不在本輪時為 `None`。
        """
        for ranking in self.rankings:
            if ranking.question_number == question_number:
                return ranking
        return None


def as_final(rankings: Iterable[QuestionRanking]) -> tuple[QuestionRanking, ...]:
    """定案後的顯示狀態：名次 1 的 `SUCCESS` 改為 `CORRECT`（搶答正確）。

    `WRONG`、`FAILED` 不變；輸入不被修改。

    Args:
        rankings: 各題排名。

    Returns:
        新的各題排名。
    """
    result: list[QuestionRanking] = []
    for ranking in rankings:
        entries = tuple(
            replace(entry, display_status=DisplayStatus.CORRECT)
            if entry.display_status is DisplayStatus.SUCCESS
            else entry
            for entry in ranking.entries
        )
        result.append(replace(ranking, entries=entries))
    return tuple(result)
