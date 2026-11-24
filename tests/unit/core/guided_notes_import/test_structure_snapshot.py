"""`StructureSnapshot` 的內容（FR-024，供 005 寫回前比對）。"""

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import (
    ANS_FIRST,
    ANS_LAST,
    HEADER_ROW,
    NUM_COL,
    layout_a,
    layout_b,
)


def test_layout_a_structure():
    snapshot, expected = layout_a()
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok and result.structure is not None
    st = result.structure
    assert st.header_number == CellRef(HEADER_ROW, NUM_COL)
    assert st.header_answer == CellRef(HEADER_ROW, ANS_FIRST)
    assert st.answer_cols == (ANS_FIRST, ANS_LAST)
    assert st.data_start_row == HEADER_ROW + 1
    assert dict(st.row_numbers) == {4: 1, 5: 1, 6: 2, 7: 2, 8: 3, 9: 4}
    assert dict(st.answer_cells) == {
        (q, sub): CellRef(*pos) for q, sub, pos in expected.blanks
    }
    # 只含與表頭列及資料區相交的合併範圍；範本 A 的全部合併都在表頭列或資料區
    assert set(st.merges) == set(snapshot.merges)


def test_layout_b_structure_is_shifted():
    snapshot, expected = layout_b()
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok and result.structure is not None
    st = result.structure
    assert st.header_number == CellRef(1 + 6, 0 + 3)
    assert st.header_answer == CellRef(1 + 6, 4 + 3)
    assert st.answer_cols == (4 + 3, 6 + 3)
    assert st.data_start_row == 2 + 6
    assert dict(st.row_numbers) == {8: 1, 9: 2, 10: 2, 11: 3, 12: 3, 13: 3, 14: 4}
    assert dict(st.answer_cells) == {
        (q, sub): CellRef(*pos) for q, sub, pos in expected.blanks
    }


def test_merges_above_the_header_are_not_recorded():
    snapshot, _ = layout_a()
    from dataclasses import replace

    from lecture_quiz.core.guided_notes_import.models import MergeRange

    title_merge = MergeRange(0, 0, 0, 3)  # 標題列的合併，在表頭之上，不相交
    result = GuidedNotesParser.parse(
        replace(snapshot, merges=(*snapshot.merges, title_merge))
    )
    assert result.ok and result.structure is not None
    assert title_merge not in result.structure.merges
