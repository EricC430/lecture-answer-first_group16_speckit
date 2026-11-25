"""005 核心測試資料：以手寫版面（不是真實 Google 回應）建構輸入。"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from lecture_quiz.core.guided_notes_import.models import (
    Blank,
    CellRef,
    SheetSnapshot,
    StructureSnapshot,
)
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from lecture_quiz.core.result_export.models import (
    BlankTarget,
    CellKind,
    CurrentCell,
    FinalizedEntry,
    FinalizedQuestion,
    SubmissionFact,
)
from tests.fixtures.guided_notes_layouts import layout_a, layout_b

TZ = timezone(timedelta(hours=8))
T0 = datetime(2026, 11, 24, 20, 0, 0, tzinfo=TZ)


@dataclass(frozen=True)
class Parsed:
    """一份版面的解析結果。"""

    snapshot: SheetSnapshot
    blanks: tuple[Blank, ...]
    structure: StructureSnapshot


def parsed(layout: str = "a") -> Parsed:
    """解析 `layout_a`（4 題 6 格）或 `layout_b`，回傳快照、空格與匯入時結構。"""
    snapshot, _ = layout_a() if layout == "a" else layout_b()
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok and result.structure is not None
    return Parsed(snapshot, result.blanks, result.structure)


def targets(p: Parsed) -> tuple[BlankTarget, ...]:
    """把 002 的 `Blank` 轉成 005 核心的 `BlankTarget`。"""
    return tuple(
        BlankTarget(b.question_number, b.sub_index, b.target) for b in p.blanks
    )


def entry(
    round_number: int,
    question: int,
    group: int,
    rank: int | None,
    wrong: bool = False,
) -> FinalizedEntry:
    """一個已定案候選。"""
    return FinalizedEntry(round_number, question, group, rank, wrong)


def fq(
    round_number: int, question: int, success_group: int | None
) -> FinalizedQuestion:
    """某輪某題的搶答成功者。"""
    return FinalizedQuestion(round_number, question, success_group)


def fact(
    round_number: int,
    question: int,
    group: int,
    answers: tuple[str, ...],
    second: float = 0.0,
) -> SubmissionFact:
    """一筆已接受提交；`second` 是相對 `T0` 的秒數（可含小數）。"""
    return SubmissionFact(
        round_number, question, group, answers, T0 + timedelta(seconds=second)
    )


def cur_empty() -> CurrentCell:
    """沒有內容的格。"""
    return CurrentCell(CellKind.EMPTY, None, "")


def cur_text(text: str) -> CurrentCell:
    """文字格。"""
    return CurrentCell(CellKind.TEXT, text, text)


def cur_other(display: str) -> CurrentCell:
    """數字、公式、布林等非文字內容。"""
    return CurrentCell(CellKind.OTHER, None, display)


def cell(row: int, col: int) -> CellRef:
    """方便建立座標。"""
    return CellRef(row, col)


def mixed_world(p: "Parsed | None" = None) -> dict:
    """版面 A 的混合世界：兩輪。

    - 第 1 輪：題 1（兩格題組）組 1 成功；題 3（單題）組 2 成功、組 3 搶答失敗、
      組 1 答錯；
      題 2（兩格題組）全被判錯（組 2 答錯）。
    - 第 2 輪：題 2 由組 3 成功；題 4 無人提交。
    """
    p = p or parsed("a")
    finalized_questions = (
        fq(1, 1, 1),
        fq(1, 2, None),
        fq(1, 3, 2),
        fq(2, 2, 3),
    )
    entries = (
        entry(1, 1, 1, 1),
        entry(1, 2, 2, None, True),
        entry(1, 3, 2, 1),
        entry(1, 3, 3, 2),
        entry(1, 3, 1, None, True),
        entry(2, 2, 3, 1),
    )
    submissions = (
        fact(1, 1, 1, ("甲一", "甲二"), 1),
        fact(1, 2, 2, ("錯一", "錯二"), 2),
        fact(1, 3, 2, ("第三題答案",), 3),
        fact(1, 3, 3, ("較慢",), 4),
        fact(1, 3, 1, ("錯的",), 5),
        fact(2, 2, 3, ("乙一", "乙二"), 6),
    )
    return {
        "p": p,
        "finalized_questions": finalized_questions,
        "entries": entries,
        "submissions": submissions,
        "blanks": targets(p),
        "question_numbers": (1, 2, 3, 4),
        "round_numbers": (1, 2),
    }


# ── 對 SheetSnapshot 的修改（模擬老師在匯入之後改動學習單）──────────


def insert_row(snapshot: SheetSnapshot, at_row: int) -> SheetSnapshot:
    """在 `at_row` 插入一個空白列：該列（含）以下的儲存格與合併範圍整體下移一列。"""
    from dataclasses import replace

    from lecture_quiz.core.guided_notes_import.models import MergeRange

    cells = {
        (CellRef(r.row + 1, r.col) if r.row >= at_row else r): v
        for r, v in snapshot.cells.items()
    }
    merges = tuple(
        MergeRange(
            m.first_row + (1 if m.first_row >= at_row else 0),
            m.first_col,
            m.last_row + (1 if m.last_row >= at_row else 0),
            m.last_col,
        )
        for m in snapshot.merges
    )
    return replace(
        snapshot, cells=cells, merges=merges, row_count=snapshot.row_count + 1
    )


def with_text(snapshot: SheetSnapshot, ref: CellRef, text: str) -> SheetSnapshot:
    """把某格設為文字。"""
    from dataclasses import replace

    from lecture_quiz.core.guided_notes_import.models import CellValue

    cells = dict(snapshot.cells)
    cells[ref] = CellValue(number=None, text=text, display=text)
    return replace(snapshot, cells=cells)


def without_cell(snapshot: SheetSnapshot, ref: CellRef) -> SheetSnapshot:
    """清掉某格的內容。"""
    from dataclasses import replace

    cells = dict(snapshot.cells)
    cells.pop(ref, None)
    return replace(snapshot, cells=cells)


def renamed(snapshot: SheetSnapshot, name: str) -> SheetSnapshot:
    """只改工作表名稱。"""
    from dataclasses import replace

    return replace(snapshot, sheet_name=name)


def reparse(snapshot: SheetSnapshot):
    """以 002 的解析器重新辨識（回傳 `ParseResult`）。"""
    return GuidedNotesParser.parse(snapshot)
