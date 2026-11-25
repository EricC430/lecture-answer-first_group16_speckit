"""005 的日誌不含答案、原儲存格內容、token、授權網址與 state（FR-033）。"""

import logging

from tests.integration.conftest import SHEET_FOR

ANSWERS = ["獨特答案甲", "獨特答案乙"]


def test_logs_have_ids_and_counts_but_no_secrets(export_stack, caplog, capsys):
    """Scenario: FR-033：預覽、寫入、核對、重試、CSV、重新授權的日誌只含識別與數字。"""
    s = export_stack("a")
    s.join(1)
    s.open_round()
    s.submit(1, 1, 1, ANSWERS)
    s.close()
    s.finalize()
    from lecture_quiz.core.guided_notes_import.models import CellRef, CellValue

    key = ("sheet-1", SHEET_FOR["a"])
    snap = s.reader.snapshots[key]
    cells = dict(snap.cells)
    cells[CellRef(4, 7)] = CellValue(
        text="原儲存格機敏內容", display="原儲存格機敏內容"
    )
    s.reader.snapshots[key] = type(snap)(
        snap.spreadsheet_id,
        snap.sheet_id,
        snap.sheet_name,
        snap.row_count,
        snap.col_count,
        cells,
        snap.merges,
    )
    caplog.set_level(logging.DEBUG)
    preview = s.export("POST", "/preview").json()
    first = s.export("POST", "/writes", {"snapshotId": preview["snapshotId"]}).json()
    attempt = first["attemptId"]
    s.export("POST", f"/writes/{attempt}/recheck")
    s.export("POST", f"/writes/{attempt}/retry")
    s.export("GET", "/csv")
    s.export("POST", "/authorization")

    text = "\n".join(
        f"{r.name} {r.getMessage()}"
        for r in caplog.records
        if r.name.startswith("lecture_quiz")
    )
    for secret in (
        *ANSWERS,
        "原儲存格機敏內容",
        s.teacher.token,
        "state=fake",
        "accounts.example.test",
        "Bearer",
    ):
        assert secret not in text, secret
    assert f"activity={s.code}" in text and "attempt=" in text and "status=" in text
    assert "snapshot=" in text and "cells=" in text
    assert capsys.readouterr().out == "", "不得使用 print"
