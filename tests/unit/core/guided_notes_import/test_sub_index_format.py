"""被接受的子編號格式（Edge: 子編號與作答格的位置）。"""

import pytest

from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import ANS_FIRST, ANS_LAST, HEADER_ROW, NUM_COL
from tests.unit.core.guided_notes_import.helpers import Sheet


def sheet_with_sub(sub_text: str, sub_col: int = ANS_FIRST) -> Sheet:
    s = Sheet(HEADER_ROW + 3, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    s.merge(HEADER_ROW, ANS_FIRST, HEADER_ROW, ANS_LAST)
    s.set(HEADER_ROW + 1, NUM_COL, 1.0).set(HEADER_ROW + 1, sub_col, sub_text)
    return s


@pytest.mark.parametrize("text", ["(1)", "（1）", "(1）", "（1)", " (1) "])
def test_accepted_formats(text):
    """Edge: 子編號與作答格的位置"""
    result = GuidedNotesParser.parse(sheet_with_sub(text).snapshot())
    assert result.ok, result.issues
    assert result.blanks[0].sub_index == 1
    assert result.blanks[0].target.col == ANS_FIRST + 1


def test_sub_index_outside_answer_header_columns_is_not_a_sub_index():
    """Edge: 子編號與作答格的位置"""
    # 編號在題號欄之外、作答表頭涵蓋範圍之外的欄 → 不被辨識為子編號；
    # 該列有題號、沒有子編號 → 視為單題，位置取作答欄首欄（空格仍存在）
    s = sheet_with_sub("(1)", sub_col=3)
    result = GuidedNotesParser.parse(s.snapshot())
    assert result.ok, result.issues
    assert result.blanks[0].sub_index is None
    assert result.blanks[0].target.col == ANS_FIRST
