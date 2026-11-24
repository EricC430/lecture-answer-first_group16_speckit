"""005 的 JSON 序列化（HTTP 回應與老師快照的 `export` 摘要共用）。

位置以 A1 字串顯示（欄以字母、列 1 起算）；不可信文字（答案、原儲存格內容）原樣放入，
前端一律以 `textContent` 顯示。
"""

from lecture_quiz.app.result_export.messages import reason_text
from lecture_quiz.app.result_export.models import (
    AttemptStatus,
    PreviewView,
    WriteAttempt,
)
from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import (
    StructureCheck,
    StructureDifference,
    WritePlanItem,
)

MAX_DIFFERENCES = 20
"""預覽與回應最多列出的結構差異筆數。"""


def column_letters(col: int) -> str:
    """0 起算的欄索引轉成字母（0 → A、26 → AA）。"""
    letters = ""
    number = col + 1
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def a1(ref: CellRef) -> str:
    """0 起算的列欄轉成 A1 顯示字串（例如 `C7`）。"""
    return f"{column_letters(ref.col)}{ref.row + 1}"


def difference_json(diff: StructureDifference) -> JsonDict:
    """單項結構差異；沒有位置時 `row`、`col` 為 `None`。"""
    return {
        "kind": diff.kind.value,
        "row": None if diff.at is None else diff.at.row + 1,
        "col": None if diff.at is None else column_letters(diff.at.col),
        "detail": diff.detail,
    }


def structure_json(check: StructureCheck) -> JsonDict:
    """結構比對結論；差異最多回 `MAX_DIFFERENCES` 筆並附其餘筆數。"""
    shown = check.differences[:MAX_DIFFERENCES]
    return {
        "ok": check.ok,
        "differences": [difference_json(d) for d in shown],
        "moreDifferences": len(check.differences) - len(shown),
    }


def item_json(item: WritePlanItem) -> JsonDict:
    """預覽的一列。"""
    return {
        "roundNumber": item.round_number,
        "questionNumber": item.question_number,
        "subIndex": item.sub_index,
        "groupNumber": item.group_number,
        "answer": item.answer,
        "target": a1(item.target),
        "impact": item.impact.value,
        "currentDisplay": item.current_display,
    }


def preview_json(view: PreviewView) -> JsonDict:
    """預覽回應。"""
    return {
        "snapshotId": view.snapshot.snapshot_id,
        "canConfirm": view.can_confirm,
        "structure": structure_json(view.structure),
        "items": [item_json(i) for i in view.snapshot.items],
        "unwrittenQuestions": list(view.snapshot.unwritten_questions),
        "sheetTitle": view.sheet_title,
    }


def _iso(value: object) -> str | None:
    return None if value is None else value.isoformat(timespec="milliseconds")  # type: ignore[attr-defined]


def attempt_json(attempt: WriteAttempt) -> JsonDict:
    """寫回嘗試的完整回應（只給發出請求的老師）。"""
    return {
        "attemptId": attempt.attempt_id,
        "kind": attempt.kind.value,
        "snapshotId": attempt.snapshot_id,
        "status": attempt.status.value,
        "reason": None if attempt.reason is None else attempt.reason.value,
        "reasonText": None if attempt.reason is None else reason_text(attempt.reason),
        "totalCells": attempt.total_cells,
        "confirmedCells": attempt.confirmed_cells,
        "notWrittenCells": attempt.not_written_cells,
        "pendingCells": attempt.pending_cells,
        "differences": [
            difference_json(d) for d in attempt.differences[:MAX_DIFFERENCES]
        ],
        "cellChecks": [
            {
                "questionNumber": c.question_number,
                "subIndex": c.sub_index,
                "expected": c.expected,
                "currentDisplay": c.current_display,
                "matches": c.matches,
            }
            for c in attempt.cell_checks
        ],
        "startedAt": _iso(attempt.started_at),
        "finishedAt": _iso(attempt.finished_at),
        "alreadyInProgress": attempt.already_in_progress,
    }


def attempt_summary(attempt: WriteAttempt) -> JsonDict:
    """老師快照 `export` 欄位的摘要：不含逐格答案、原內容、差異清單與網址。"""
    return {
        "attemptId": attempt.attempt_id,
        "kind": attempt.kind.value,
        "snapshotId": attempt.snapshot_id,
        "status": attempt.status.value,
        "reason": None if attempt.reason is None else attempt.reason.value,
        "totalCells": attempt.total_cells,
        "confirmedCells": attempt.confirmed_cells,
        "notWrittenCells": attempt.not_written_cells,
        "pendingCells": attempt.pending_cells,
        "inProgress": attempt.status is AttemptStatus.IN_PROGRESS,
        "startedAt": _iso(attempt.started_at),
        "finishedAt": _iso(attempt.finished_at),
    }
