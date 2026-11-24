"""順位計算：基準、速度模式排名、公平模式排名、整輪重算與受影響題目（FR-004～FR-018）。

全部是純函式：輸入相同則輸出完全相同（FR-017）；不讀時鐘，時間資料只來自
`Candidate.received_at`。
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from lecture_quiz.core.ranking_review.models import (
    Candidate,
    QuestionRanking,
    RankEntry,
    RankingInput,
    RoundResult,
    WinReason,
    display_status,
)


def _time_key(c: Candidate) -> tuple[object, int]:
    return (c.received_at, c.sequence)


class RankingCalculator:
    """順位計算的純函式集合。"""

    @staticmethod
    def initial_counts(
        baseline: Mapping[int, int], group_numbers: Iterable[int]
    ) -> dict[int, int]:
        """本輪處理前各組的成功次數：基準的複本，基準沒有的組視為 0。

        不修改傳入的基準；基準有、但 `group_numbers` 沒有的組保留原值。

        Args:
            baseline: 組號 → 開輪時的成功次數。
            group_numbers: 本輪會用到的組號（例如有提交的組別）。

        Returns:
            新的對照表。
        """
        counts = dict(baseline)
        for group in group_numbers:
            counts.setdefault(group, 0)
        return counts

    @staticmethod
    def _reason(
        ahead: Candidate,
        behind: Candidate,
        fair_mode: bool,
        counts: Mapping[int, int],
    ) -> WinReason:
        """排在前面的候選為什麼排在後面的候選之前（research R9）。"""
        if fair_mode and counts[ahead.group_number] != counts[behind.group_number]:
            return WinReason.FEWER_SUCCESSES
        if ahead.received_at != behind.received_at:
            return WinReason.EARLIER_SUBMISSION
        return WinReason.BACKEND_ORDER

    @staticmethod
    def _build(
        question_number: int,
        ranked: Sequence[Candidate],
        wrong: Sequence[Candidate],
        fair_mode: bool,
        counts: Mapping[int, int],
    ) -> QuestionRanking:
        entries: list[RankEntry] = []
        for index, candidate in enumerate(ranked, start=1):
            if len(ranked) == 1:
                reason = WinReason.SOLE_CANDIDATE
            elif index == 1:
                reason = RankingCalculator._reason(
                    ranked[0], ranked[1], fair_mode, counts
                )
            else:
                reason = RankingCalculator._reason(
                    ranked[index - 2], candidate, fair_mode, counts
                )
            entries.append(
                RankEntry(
                    group_number=candidate.group_number,
                    rank=index,
                    count_at_processing=counts[candidate.group_number]
                    if fair_mode
                    else None,
                    reason=reason,
                    wrong=False,
                    display_status=display_status(index, False),
                )
            )
        for candidate in wrong:
            entries.append(
                RankEntry(
                    group_number=candidate.group_number,
                    rank=None,
                    count_at_processing=None,
                    reason=None,
                    wrong=True,
                    display_status=display_status(None, True),
                )
            )
        success = ranked[0].group_number if ranked else None
        return QuestionRanking(question_number, tuple(entries), success)

    @staticmethod
    def rank_speed(
        question_number: int,
        candidates: Sequence[Candidate],
        wrong_groups: frozenset[int],
    ) -> QuestionRanking:
        """速度模式：未被判錯的候選依（接收時間, 接收序號）遞增排名（FR-006）。

        與成功次數無關（FR-009）；被判錯者沒有名次，附在後面。

        Args:
            question_number: 題號。
            candidates: 該題全部已接受的提交。
            wrong_groups: 該題被判錯的組號。

        Returns:
            該題排名。
        """
        valid = sorted(
            (c for c in candidates if c.group_number not in wrong_groups),
            key=_time_key,  # type: ignore[arg-type]
        )
        wrong = sorted(
            (c for c in candidates if c.group_number in wrong_groups),
            key=_time_key,  # type: ignore[arg-type]
        )
        return RankingCalculator._build(question_number, valid, wrong, False, {})

    @staticmethod
    def rank_fair(
        question_number: int,
        candidates: Sequence[Candidate],
        wrong_groups: frozenset[int],
        counts: Mapping[int, int],
    ) -> QuestionRanking:
        """公平模式：未被判錯的候選依（目前成功次數, 接收時間, 接收序號）遞增排名。

        Args:
            question_number: 題號。
            candidates: 該題全部已接受的提交。
            wrong_groups: 該題被判錯的組號。
            counts: 處理這一題當下各組的成功次數（包含本輪較前題目的暫算次數）。

        Returns:
            該題排名；每個候選的 `count_at_processing` 是處理當下的次數。
        """
        valid = sorted(
            (c for c in candidates if c.group_number not in wrong_groups),
            key=lambda c: (counts[c.group_number], c.received_at, c.sequence),
        )
        wrong = sorted(
            (c for c in candidates if c.group_number in wrong_groups),
            key=_time_key,  # type: ignore[arg-type]
        )
        return RankingCalculator._build(question_number, valid, wrong, True, counts)

    @staticmethod
    def _check(data: RankingInput, order: Sequence[int]) -> None:
        """輸入不變式（data-model）；違反是程式錯誤。"""
        keys = [(c.question_number, c.group_number) for c in data.candidates]
        assert len(keys) == len(set(keys)), "同一（題號, 組號）只能有一個候選"
        sequences = [c.sequence for c in data.candidates]
        assert len(sequences) == len(set(sequences)), "接收序號不得重複"
        questions = set(data.question_numbers)
        assert all(c.question_number in questions for c in data.candidates), (
            "候選的題號必須在本輪題號內"
        )
        marks_ok = all((q, g) in set(keys) for (g, q) in data.wrong_marks)
        assert marks_ok, "判錯集合的每一項都必須對應一個候選"
        assert sorted(order) == sorted(data.question_numbers), (
            "題序必須涵蓋本輪全部題號"
        )

    @staticmethod
    def recompute(data: RankingInput, order: Sequence[int]) -> RoundResult:
        """整輪重算：從基準與固定題序出發，依模式逐題處理（FR-015、FR-017）。

        一律從 `data.baseline` 開始，不使用任何舊的暫算次數；題序由呼叫端傳入，
        不在這裡重新計算，所以判錯不會移動題序。

        Args:
            data: 整輪重算的完整輸入。
            order: 固定題序（關輪時由 `QuestionOrder.compute` 決定並保存）。

        Returns:
            本輪結果。
        """
        RankingCalculator._check(data, order)
        by_question: dict[int, list[Candidate]] = defaultdict(list)
        for candidate in data.candidates:
            by_question[candidate.question_number].append(candidate)
        counts = RankingCalculator.initial_counts(
            data.baseline, {c.group_number for c in data.candidates}
        )
        wins: dict[int, int] = {}
        rankings: list[QuestionRanking] = []
        for question in order:
            wrong_groups = frozenset(g for (g, q) in data.wrong_marks if q == question)
            candidates = by_question.get(question, [])
            ranking = (
                RankingCalculator.rank_fair(question, candidates, wrong_groups, counts)
                if data.fair_mode
                else RankingCalculator.rank_speed(question, candidates, wrong_groups)
            )
            rankings.append(ranking)
            if ranking.success_group is not None:
                counts[ranking.success_group] += 1
                wins[ranking.success_group] = wins.get(ranking.success_group, 0) + 1
        return RoundResult(tuple(order), tuple(rankings), counts, wins)

    @staticmethod
    def diff(old: RoundResult, new: RoundResult) -> frozenset[int]:
        """重算前後有變的題號（成功者或任一候選的名次、次數、理由、判錯狀態不同）。

        Args:
            old: 重算前的結果。
            new: 重算後的結果。

        Returns:
            受影響的題號。
        """
        return frozenset(
            ranking.question_number
            for ranking in new.rankings
            if old.ranking_of(ranking.question_number) != ranking
        )
