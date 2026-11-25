"""US3 端到端：兩份版面各寫回一次並逐格比對（SC-002）。

`FakeSheetsWriter` 與讀取器共用試算表狀態。
"""

import pytest

from lecture_quiz.core.guided_notes_import.models import CellRef
from tests.fixtures.guided_notes_layouts import layout_a, layout_b
from tests.integration.conftest import SHEET_FOR

LAYOUT = {"a": layout_a, "b": layout_b}


def run_world(s, layout):
    """第 1 輪：組 1 答題 1、2、3（含特殊文字），組 2 也答題 2；關輪並定案。"""
    _, expected = LAYOUT[layout]()
    counts = {q: n for q, n, _ in expected.questions}
    s.join(1, 2)
    s.open_round()
    special = "  =1+1\n第二行  "
    answers = {q: [f"答{q}-{i + 1}" for i in range(counts[q])] for q in (1, 2, 3)}
    answers[1][0] = special
    for q in (1, 2, 3):
        s.submit(1, q, 1, answers[q])
    s.submit(1, 2, 2, [f"乙{i}" for i in range(counts[2])])
    s.close()
    s.finalize()
    return expected, answers


@pytest.mark.parametrize("layout", ["a", "b"])
def test_exact_write_and_everything_else_preserved(export_stack, layout):
    """Scenario: US3-AS1、AS2：混合題型與兩份版面，目標格正確、其餘不變。"""
    s = export_stack(layout)
    expected, answers = run_world(s, layout)
    key = ("sheet-1", SHEET_FOR[layout])
    before = s.reader.snapshots[key]
    body = s.export("POST", "/preview").json()
    result = s.export("POST", "/writes", {"snapshotId": body["snapshotId"]})
    assert result.status_code == 200 and result.json()["status"] == "SUCCESS", (
        result.text
    )
    after = s.reader.snapshots[key]
    targets = {
        CellRef(*pos): (q, sub) for q, sub, pos in expected.blanks if q in (1, 2, 3)
    }
    for ref, (q, sub) in targets.items():
        text = answers[q][(sub or 1) - 1]
        assert after.cells[ref].text == text  # 逐字相同
    changed = {
        r
        for r in set(before.cells) | set(after.cells)
        if before.cells.get(r) != after.cells.get(r)
    }
    assert changed == set(targets), "只有目標格被改動，題組編號與其他格完全不變"
    assert after.merges == before.merges and after.sheet_name == before.sheet_name
    # 題 4（沒有成功）的作答格完全沒動
    for q, _sub, pos in expected.blanks:
        if q == 4:
            assert after.cells.get(CellRef(*pos)) == before.cells.get(CellRef(*pos))


@pytest.mark.parametrize("layout", ["a", "b"])
def test_second_preview_after_write_is_still_same_structure(export_stack, layout):
    """研究 R5 風險：寫入後再預覽，結構仍相符、覆寫影響變成 SAME。"""
    s = export_stack(layout)
    run_world(s, layout)
    key = ("sheet-1", SHEET_FOR[layout])
    first = s.export("POST", "/preview").json()
    first_cells = dict(s.reader.snapshots[key].cells)
    assert {i["impact"] for i in first["items"]} == {"EMPTY"}
    s.export("POST", "/writes", {"snapshotId": first["snapshotId"]})
    assert dict(s.reader.snapshots[key].cells) != first_cells, (
        "寫入前後讀取器內容必須不同"
    )
    again = s.export("POST", "/preview").json()
    assert again["structure"]["ok"] is True and again["canConfirm"] is True
    assert {i["impact"] for i in again["items"]} == {"SAME"}


@pytest.mark.parametrize("layout", ["a", "b"])
def test_placeholder_replaced_for_winners_kept_for_unsolved(export_stack, layout):
    """Scenario: US3-AS5：成功題的佔位文字被取代（預覽顯示原內容）；未成功題保留。"""
    from tests.unit.core.result_export.helpers import with_text

    s = export_stack(layout)
    expected, _ = run_world(s, layout)
    key = ("sheet-1", SHEET_FOR[layout])
    win = next(CellRef(*pos) for q, sub, pos in expected.blanks if q == 3)
    lose = next(CellRef(*pos) for q, sub, pos in expected.blanks if q == 4)
    snap = with_text(s.reader.snapshots[key], win, "請填答案")
    s.reader.snapshots[key] = with_text(snap, lose, "未成功題的佔位")
    preview = s.export("POST", "/preview").json()
    replaced = [i for i in preview["items"] if i["impact"] == "REPLACE"]
    assert [i["currentDisplay"] for i in replaced] == ["請填答案"]
    s.export("POST", "/writes", {"snapshotId": preview["snapshotId"]})
    after = s.reader.snapshots[key]
    assert after.cells[win].text != "請填答案"
    assert after.cells[lose].text == "未成功題的佔位"
