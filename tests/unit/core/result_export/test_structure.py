"""來源結構比對（US2）：layout_a 與 layout_b 各測一次。"""

from dataclasses import replace

import pytest

from lecture_quiz.core.guided_notes_import.models import CellRef, MergeRange
from lecture_quiz.core.result_export.models import DiffKind
from lecture_quiz.core.result_export.structure import compare_structure
from tests.unit.core.result_export.helpers import (
    insert_row,
    parsed,
    renamed,
    reparse,
    with_text,
    without_cell,
)

LAYOUTS = ["a", "b"]


def kinds(check):
    return {d.kind for d in check.differences}


@pytest.mark.parametrize("layout", LAYOUTS)
def test_identical_snapshot_is_ok(layout):
    """Scenario: US2-AS3 的基線：相同快照相符，沒有差異。"""
    p = parsed(layout)
    check = compare_structure(p.structure, reparse(p.snapshot))
    assert check.ok and check.differences == ()


@pytest.mark.parametrize("layout", LAYOUTS)
def test_answer_text_change_is_not_a_structure_change(layout):
    """Scenario: US2-AS3（只有原答案內容改變）：作答格已有文字不算結構變更。"""
    p = parsed(layout)
    changed = p.snapshot
    for blank in p.blanks:
        changed = with_text(changed, blank.target, "老師先填的佔位文字")
    assert compare_structure(p.structure, reparse(changed)).ok


@pytest.mark.parametrize("layout", LAYOUTS)
def test_rename_is_not_a_structure_change(layout):
    """Scenario: US2-AS3：工作表只改名（識別不變）不算結構變更。"""
    p = parsed(layout)
    assert compare_structure(p.structure, reparse(renamed(p.snapshot, "新名字"))).ok


def test_unrelated_region_change_is_not_a_structure_change():
    """FR-009：與表頭列及資料區無關的區域有改動（表頭之上的標題合併）不算變更。"""
    p = parsed("a")
    merged = replace(p.snapshot, merges=(*p.snapshot.merges, MergeRange(0, 0, 0, 3)))
    assert compare_structure(p.structure, reparse(merged)).ok


@pytest.mark.parametrize("layout", LAYOUTS)
def test_inserted_row_moves_answer_cells(layout):
    """Scenario: US2-AS1（表頭不變但答案列移動）：表頭文字仍在、答案格位移。"""
    p = parsed(layout)
    header_row = min(p.structure.header_number.row, p.structure.header_answer.row)
    moved = insert_row(p.snapshot, header_row + 1)
    check = compare_structure(p.structure, reparse(moved))
    assert not check.ok
    assert DiffKind.ANSWER_CELL in kinds(check) or DiffKind.QUESTION_NUMBER in kinds(
        check
    )
    assert DiffKind.UNRECOGNIZED not in kinds(check)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_row_inserted_above_header_moves_headers(layout):
    """Scenario: US2-AS2：表頭位置不同 → HEADER_POSITION。"""
    p = parsed(layout)
    check = compare_structure(p.structure, reparse(insert_row(p.snapshot, 0)))
    assert not check.ok and DiffKind.HEADER_POSITION in kinds(check)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_deleted_header_is_unrecognized(layout):
    """Scenario: US2-AS2：表頭被刪（無法再辨識為合法學習單）→ 單一 UNRECOGNIZED。"""
    p = parsed(layout)
    broken = without_cell(p.snapshot, p.structure.header_answer)
    check = compare_structure(p.structure, reparse(broken))
    assert not check.ok
    assert [d.kind for d in check.differences] == [DiffKind.UNRECOGNIZED]
    assert check.differences[0].at is None


def test_each_difference_kind_is_reported_with_position():
    """Scenario: US2-AS2：題號、子空格、答案格、合併範圍各自歸類並指出位置。"""
    p = parsed("a")
    current = reparse(p.snapshot)
    s = p.structure
    # 題號：某列的題號與現況不同
    row = next(iter(s.row_numbers))
    changed_numbers = {**s.row_numbers, row: s.row_numbers[row] + 100}
    check = compare_structure(replace(s, row_numbers=changed_numbers), current)
    assert kinds(check) == {DiffKind.QUESTION_NUMBER}
    assert check.differences[0].at == CellRef(row, 0)
    # 子空格：匯入時多一個現況沒有的子空格
    extra = {**s.answer_cells, (9, 3): CellRef(30, 30)}
    check = compare_structure(replace(s, answer_cells=extra), current)
    assert kinds(check) == {DiffKind.SUB_BLANK}
    # 答案格：同一個（題號, 子編號）位置不同
    key = next(iter(s.answer_cells))
    moved = {**s.answer_cells, key: CellRef(99, 99)}
    check = compare_structure(replace(s, answer_cells=moved), current)
    assert kinds(check) == {DiffKind.ANSWER_CELL}
    assert (
        check.differences[0].at == CellRef(99, 99)
        or check.differences[0].at == s.answer_cells[key]
    )
    # 合併範圍
    check = compare_structure(replace(s, merges=s.merges[:-1]), current)
    assert kinds(check) == {DiffKind.MERGE_RANGE}
    # 表頭位置與資料起始列
    check = compare_structure(replace(s, data_start_row=s.data_start_row + 1), current)
    assert kinds(check) == {DiffKind.HEADER_POSITION}


def test_differences_sorted_deterministic_and_text_free():
    """差異依位置排序、相同輸入輸出相同，detail 不含試算表文字。"""
    p = parsed("a")
    changed = with_text(insert_row(p.snapshot, 4), CellRef(0, 0), "機敏標題文字")
    a = compare_structure(p.structure, reparse(changed))
    b = compare_structure(p.structure, reparse(changed))
    assert a == b
    positions = [(d.at.row, d.at.col) if d.at else (-1, -1) for d in a.differences]
    assert positions == sorted(positions)
    assert all("機敏標題文字" not in d.detail for d in a.differences)
