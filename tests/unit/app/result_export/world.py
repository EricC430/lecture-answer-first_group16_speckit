"""005 服務層測試的世界：依版面自動產生 004 定案結果、003 提交與 002 匯入記錄。

全部是手寫資料（不是真實系統產出），只用來驗證 005 的行為。
"""

from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from lecture_quiz.app.guided_notes_import.models import ImportRecord, SourceRef
from lecture_quiz.app.ranking_review.ports import FinalizedRound
from lecture_quiz.core.ranking_review.models import (
    DisplayStatus,
    QuestionRanking,
    RankEntry,
)
from lecture_quiz.core.ranking_review.outcome import FinalizedResult
from lecture_quiz.core.round_submission.models import Submission
from tests.unit.app.result_export.fakes import FakeRankingReader, FakeSubmissionReader
from tests.unit.core.result_export.helpers import T0, Parsed, parsed

# (輪次, 題號, 組號, 名次, 是否被判錯)；名次為 None 代表被判錯
DEFAULT_PLAN = (
    (1, 1, 1, 1, False),
    (1, 1, 2, 2, False),
    (1, 2, 2, None, True),
    (1, 3, 2, 1, False),
    (1, 3, 3, 2, False),
    (1, 3, 1, None, True),
    (2, 2, 3, 1, False),
)

SOURCE = SourceRef("S1", 0)


def answers_for(
    p: Parsed, question: int, group: int, round_number: int
) -> tuple[str, ...]:
    """依題目的子空格數產生可辨識的答案文字。"""
    count = sum(1 for b in p.blanks if b.question_number == question)
    return tuple(f"答{round_number}-{question}-{group}-{i + 1}" for i in range(count))


@dataclass
class World:
    """一個測試世界。"""

    parsed: Parsed
    record: ImportRecord
    ranking: FakeRankingReader
    submissions: FakeSubmissionReader
    winners: dict[int, tuple[int, int, tuple[str, ...]]]  # 題號 → (輪次, 組號, 答案)


def build_world(
    layout: str = "a",
    plan: tuple = DEFAULT_PLAN,
    unfinalized: tuple = ((3, 4, 1),),
    code: str = "ABC123",
) -> World:
    """建立世界；`unfinalized` 是未定案輪次的 (輪次, 題號, 組號) 提交，只放在 003。"""
    p = parsed(layout)
    record = ImportRecord(
        source=SOURCE,
        sheet_title="試算表",
        blanks=p.blanks,
        structure=p.structure,
        question_numbers=tuple(sorted({b.question_number for b in p.blanks})),
        version=1,
    )
    by_round: dict[int, dict[int, list[tuple[int, int | None, bool]]]] = {}
    for rnd, q, g, rank, wrong in plan:
        by_round.setdefault(rnd, {}).setdefault(q, []).append((g, rank, wrong))
    finalized: list[FinalizedRound] = []
    subs: list[Submission] = []
    winners: dict[int, tuple[int, int, tuple[str, ...]]] = {}
    seq = 0
    for rnd in sorted(by_round):
        rankings = []
        for q in sorted(by_round[rnd]):
            entries = sorted(by_round[rnd][q], key=lambda e: (e[1] is None, e[1] or 0))
            rank_entries = []
            success = None
            for g, rank, wrong in entries:
                seq += 1
                answers = answers_for(p, q, g, rnd)
                subs.append(
                    Submission(
                        code, rnd, q, g, answers, T0 + timedelta(seconds=seq), seq
                    )
                )
                if rank == 1 and not wrong:
                    success = g
                    winners[q] = (rnd, g, answers)
                status = (
                    DisplayStatus.WRONG
                    if wrong
                    else DisplayStatus.CORRECT
                    if rank == 1
                    else DisplayStatus.FAILED
                )
                rank_entries.append(RankEntry(g, rank, None, None, wrong, status))
            rankings.append(QuestionRanking(q, tuple(rank_entries), success))
        finalized.append(
            FinalizedRound(rnd, FinalizedResult(version=1, rankings=tuple(rankings)))
        )
    for rnd, q, g in unfinalized:
        seq += 1
        subs.append(
            Submission(
                code,
                rnd,
                q,
                g,
                answers_for(p, q, g, rnd),
                T0 + timedelta(seconds=seq),
                seq,
            )
        )
    return World(
        p,
        record,
        FakeRankingReader(rounds=tuple(finalized)),
        FakeSubmissionReader(submissions=tuple(subs)),
        winners,
    )


def counts_of(p: Parsed) -> Counter[int]:
    """每題的子空格數。"""
    return Counter(b.question_number for b in p.blanks)
