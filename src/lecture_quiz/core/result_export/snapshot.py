"""成果快照與覆寫影響（純函式；FR-002、FR-003、FR-005、FR-011）。"""

from collections.abc import Iterable, Mapping, Sequence

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import (
    CURRENT_DISPLAY_LIMIT,
    BlankTarget,
    CellKind,
    CurrentCell,
    FinalizedQuestion,
    OverwriteImpact,
    ResultSnapshot,
    SubmissionFact,
    WritePlanItem,
)


def snapshot_id_of(round_numbers: Iterable[int]) -> str:
    """由已定案輪次編號集合決定成果快照識別。

    Args:
        round_numbers: 已定案的輪次編號。

    Returns:
        遞增排序後以點連接的字串（例如 `1.2`）；沒有輪次時為空字串。
    """
    return ".".join(str(n) for n in sorted(set(round_numbers)))


def _impact(answer: str, current: CurrentCell) -> tuple[OverwriteImpact, str | None]:
    """依目標格目前內容算覆寫影響；`SAME` 只有逐字相同的文字。"""
    if current.kind is CellKind.EMPTY:
        return OverwriteImpact.EMPTY, None
    if current.kind is CellKind.TEXT and current.text == answer:
        return OverwriteImpact.SAME, None
    shown = current.text if current.kind is CellKind.TEXT else current.display
    return OverwriteImpact.REPLACE, (shown or "")[:CURRENT_DISPLAY_LIMIT]


def build_snapshot(
    finalized_questions: Sequence[FinalizedQuestion],
    submissions: Sequence[SubmissionFact],
    blanks: Sequence[BlankTarget],
    question_numbers: Sequence[int],
    current_cells: Mapping[CellRef, CurrentCell],
    round_numbers: Iterable[int],
) -> ResultSnapshot:
    """由已定案成果組成寫回預覽用的成果快照。

    只處理傳入的已定案題；資料不一致時明確失敗，不略過。

    Args:
        finalized_questions: 已定案輪次中每題的搶答成功者。
        submissions: 已接受提交（至少含搶答成功者的）。
        blanks: 002 的來源映射（每個空格的題號、子編號與目標位置）。
        question_numbers: 活動的全部題號。
        current_cells: 目標格目前的內容；沒有的格視為空。
        round_numbers: 已定案的輪次編號。

    Returns:
        成果快照。

    Raises:
        ValueError: 找不到搶答成功者的提交、答案數與格數不符、同一題有兩個搶答成功者，
            或題號沒有來源映射。
    """
    by_submission = {
        (s.round_number, s.question_number, s.group_number): s for s in submissions
    }
    by_question: dict[int, list[BlankTarget]] = {}
    for blank in blanks:
        by_question.setdefault(blank.question_number, []).append(blank)
    for group in by_question.values():
        group.sort(key=lambda b: b.sub_index or 0)
    items: list[WritePlanItem] = []
    winners: set[int] = set()
    for fq in finalized_questions:
        if fq.success_group is None:
            continue
        if fq.question_number in winners:
            raise ValueError("同一題出現兩個搶答成功者")
        winners.add(fq.question_number)
        fact = by_submission.get(
            (fq.round_number, fq.question_number, fq.success_group)
        )
        if fact is None:
            raise ValueError("找不到搶答成功者的提交")
        targets = by_question.get(fq.question_number)
        if not targets:
            raise ValueError("題號沒有來源映射")
        if len(fact.answers) != len(targets):
            raise ValueError("答案數與格數不符")
        for blank, answer in zip(targets, fact.answers, strict=True):
            impact, shown = _impact(
                answer, current_cells.get(blank.target, CurrentCell(CellKind.EMPTY))
            )
            items.append(
                WritePlanItem(
                    fq.round_number,
                    fq.question_number,
                    blank.sub_index,
                    fq.success_group,
                    answer,
                    blank.target,
                    impact,
                    shown,
                )
            )
    items.sort(key=lambda i: (i.question_number, i.sub_index or 0))
    return ResultSnapshot(
        snapshot_id_of(round_numbers),
        tuple(items),
        tuple(sorted(set(question_numbers) - winners)),
    )
