"""題組與單題混合（US3）。"""

import pytest

from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import (
    ANS_FIRST,
    ANS_LAST,
    HEADER_ROW,
    NUM_COL,
    STANDARD_ITEMS,
    from_items,
    layout_a,
    layout_b,
)
from tests.unit.core.guided_notes_import.helpers import Sheet


def summarize(result):
    return (
        tuple((q.number, q.blank_count, q.is_group) for q in result.questions),
        tuple(
            (b.question_number, b.sub_index, (b.target.row, b.target.col))
            for b in result.blanks
        ),
    )


def test_original_group_example_four_questions_six_blanks():
    """Scenario: US3-AS1"""
    snapshot, expected = layout_a()
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert len(result.questions) == 4 and len(result.blanks) == 6
    assert summarize(result) == (expected.questions, expected.blanks)
    sub_blanks = [b for b in result.blanks if b.sub_index is not None]
    # 第二個子空格沒有被跳過
    assert {(b.question_number, b.sub_index) for b in sub_blanks} == {
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2),
    }
    # 答案位置在編號右側（H 欄），不是編號所在的 G 欄
    assert all(b.target.col == ANS_LAST for b in sub_blanks)
    assert all(b.target.col != ANS_FIRST for b in sub_blanks)
    # 編號位於作答表頭涵蓋的欄範圍內
    assert result.structure is not None
    assert result.structure.answer_cols == (ANS_FIRST, ANS_LAST)


def test_adjacent_repeated_numbers_equal_vertical_merge():
    """Scenario: US3-AS2"""
    merged, _ = from_items(STANDARD_ITEMS, repeated=False)
    repeated, expected = from_items(STANDARD_ITEMS, repeated=True)
    a = GuidedNotesParser.parse(merged)
    b = GuidedNotesParser.parse(repeated)
    assert a.ok and b.ok, (a.issues, b.issues)
    assert summarize(a) == summarize(b) == (expected.questions, expected.blanks)


@pytest.mark.parametrize("repeated", [False, True])
def test_spacer_rows_are_ignored_and_do_not_inherit_number(repeated):
    """Scenario: US3-AS3"""
    items = [
        ("sub", 1, 1),
        ("sub", 1, 2),
        ("note", 0, None),
        ("blank", 0, None),
        ("sub", 2, 1),
        ("sub", 2, 2),
        ("note", 0, None),
        ("single", 3, None),
        ("blank", 0, None),
        ("single", 4, None),
    ]
    snapshot, expected = from_items(items, repeated=repeated)
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert summarize(result) == (expected.questions, expected.blanks)
    assert len(result.blanks) == 6  # 間隔列沒有被建立成子題


def test_blank_number_inherits_only_inside_vertical_merge():
    """Scenario: US3-AS4"""
    snapshot, expected = from_items(STANDARD_ITEMS, repeated=False)
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok
    # 合併範圍內的續列（沒有明寫題號）繼承了題號
    assert result.structure is not None
    first_row = HEADER_ROW + 1
    assert result.structure.row_numbers[first_row] == 1
    assert result.structure.row_numbers[first_row + 1] == 1
    # 合併範圍外的空白題號不繼承：把一個沒題號的子編號列放在合併範圍之外 → 孤立子空格
    s = Sheet(HEADER_ROW + 4, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, 1.0).set(HEADER_ROW + 1, ANS_FIRST, "(1)")
    s.set(HEADER_ROW + 2, ANS_FIRST, "(2)")  # 沒有合併，也沒有明寫題號
    outside = GuidedNotesParser.parse(s.snapshot())
    assert not outside.ok


def test_mixed_single_and_group_total_questions_not_by_sub_blank():
    """Scenario: US3-AS5"""
    for build in (layout_a, layout_b):
        snapshot, expected = build()
        result = GuidedNotesParser.parse(snapshot)
        assert result.ok, result.issues
        assert len(result.questions) == len(expected.questions) == 4
        assert len(result.blanks) == expected.total_blanks
        assert len(result.blanks) > len(result.questions)  # 題組不按子空格增加題數
        assert any(q.is_group for q in result.questions)
        assert any(not q.is_group for q in result.questions)


@pytest.mark.parametrize("repeated", [False, True])
def test_blank_row_between_two_sub_blanks_is_ignored(repeated):
    """Scenario: US3-AS6"""
    items = [
        ("sub", 1, 1),
        ("blank", 0, None),
        ("sub", 1, 2),
        ("single", 2, None),
    ]
    snapshot, expected = from_items(items, repeated=repeated)
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert summarize(result) == (expected.questions, expected.blanks)
    assert result.questions[0].blank_count == 2


def test_merge_range_that_swallows_trailing_spacer_rows():
    """Scenario: US3-AS6"""
    items = [
        ("sub", 1, 1),
        ("sub", 1, 2),
        ("note", 0, None),
        ("blank", 0, None),
        ("single", 2, None),
    ]
    snapshot, expected = from_items(items, repeated=False, merge_over_trailing=True)
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert summarize(result) == (expected.questions, expected.blanks)


def test_answer_cell_with_placeholder_text_is_still_an_answer_cell():
    """Edge: 作答格已有佔位文字"""
    snapshot, expected = layout_a()
    cells = dict(snapshot.cells)
    from lecture_quiz.core.guided_notes_import.models import CellRef, CellValue

    for blank in expected.blanks:
        row, col = blank[2]
        cells[CellRef(row, col)] = CellValue(text="請填寫", display="請填寫")
    from dataclasses import replace

    result = GuidedNotesParser.parse(replace(snapshot, cells=cells))
    assert result.ok, result.issues
    assert summarize(result) == (expected.questions, expected.blanks)
