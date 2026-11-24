"""定案時保存的唯讀結果（data-model.md「FinalizedResult」）。"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from lecture_quiz.core.ranking_review.models import QuestionRanking, freeze_mapping


@dataclass(frozen=True)
class FinalizedResult:
    """定案時保存的結果，之後只讀。

    Attributes:
        version: 定案所依據的結果版本。
        rankings: 各題全部候選的順位與搶答成功者（已套用 `as_final`：名次 1 為
            `CORRECT`）。
        final_counts: 各組定案後的累計成功次數（基準加本輪成功題數）。
        solved_questions: 本輪新成功的題號。
        success_increments: 各組成功次數增量（key 為組號；只含有成功題的組）。
    """

    version: int
    rankings: tuple[QuestionRanking, ...]
    final_counts: Mapping[int, int] = field(default_factory=dict)
    solved_questions: frozenset[int] = frozenset()
    success_increments: Mapping[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """把對照表轉成唯讀。"""
        object.__setattr__(self, "final_counts", freeze_mapping(self.final_counts))
        object.__setattr__(
            self, "success_increments", freeze_mapping(self.success_increments)
        )
