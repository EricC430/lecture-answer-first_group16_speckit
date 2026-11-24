"""缺陷學習單必須整份拒絕並指出位置（US4、SC-004）。

先寫、先確認失敗：這份測試在 `parse` 實作之前是紅燈，且負對照真的會失敗，才能相信它。
"""

import pytest

from lecture_quiz.core.guided_notes_import.models import IssueKind, ParseResult
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import (
    ANS_FIRST,
    ANS_LAST,
    HEADER_ROW,
    NUM_COL,
    defect_cases,
    layout_a,
    layout_b,
    single_template,
)
from tests.unit.core.guided_notes_import.helpers import Sheet

CASES = defect_cases()


def assert_atomic_rejection(result: ParseResult) -> None:
    assert not result.ok
    assert result.questions == () and result.blanks == () and result.structure is None
    assert result.issues != ()


@pytest.mark.parametrize("name", sorted(CASES))
def test_defect_is_rejected_with_expected_kinds(name):
    """Scenario: US4-AS1 / US4-AS2 / US4-AS3 / US4-AS4（依案例名稱）"""
    case = CASES[name]
    result = GuidedNotesParser.parse(case.snapshot)
    assert_atomic_rejection(result)
    assert {i.kind for i in result.issues} == set(case.kinds), result.issues
    for issue in result.issues:
        assert issue.hint  # 老師可照做的修正建議
        if issue.kind not in (
            IssueKind.MISSING_HEADER_NUMBER,
            IssueKind.MISSING_HEADER_ANSWER,
        ):
            assert issue.at is not None  # 指出列欄


def test_every_sc004_category_has_a_defect_sheet():
    """SC-004：九種拒絕條件各至少一份。"""
    covered = {k for case in CASES.values() for k in case.kinds}
    assert covered == set(IssueKind)


def test_valid_layouts_are_accepted_so_the_negative_controls_are_meaningful():
    """負對照需要有正對照：合法版面通過，缺陷版面失敗。"""
    for build in (layout_a, layout_b, single_template):
        assert GuidedNotesParser.parse(build()[0]).ok
    assert not GuidedNotesParser.parse(
        CASES["near_miss_valid_format_but_gap"].snapshot
    ).ok


def test_near_miss_has_correct_headers_and_merges_but_is_still_rejected():
    """近似錯誤對照：格式與關鍵字都對、內容有缺陷。"""
    case = CASES["near_miss_valid_format_but_gap"]
    texts = {c.text for c in case.snapshot.cells.values()}
    assert {"題號", "作答"} <= texts
    result = GuidedNotesParser.parse(case.snapshot)
    assert_atomic_rejection(result)
    assert [i.kind for i in result.issues] == [IssueKind.NUMBER_GAP]


def test_issue_positions_point_at_the_offending_cell():
    """Scenario: US4-AS3"""
    gap = GuidedNotesParser.parse(CASES["number_gap"].snapshot).issues[0]
    assert gap.at is not None and gap.at.col == NUM_COL
    sub_gap = GuidedNotesParser.parse(CASES["sub_index_gap"].snapshot).issues[0]
    assert (
        sub_gap.at is not None and sub_gap.at.col == ANS_FIRST and sub_gap.at.row == 5
    )
    dup = GuidedNotesParser.parse(CASES["non_adjacent_duplicate"].snapshot).issues[0]
    assert dup.at is not None and dup.at.row == 9


def test_quoted_text_is_truncated_to_40_chars():
    s = Sheet(6, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, "Q" * 100)
    result = GuidedNotesParser.parse(s.snapshot())
    quoted = result.issues[0].quoted
    assert quoted is not None and len(quoted) <= 40


@pytest.mark.parametrize("sub", ["（１）", "( 1 )", "(１)", "（ 1）", "(1 )"])
def test_rejected_sub_index_variants(sub):
    """Edge: 子編號與作答格的位置（全形數字、括號內夾空白）"""
    s = Sheet(HEADER_ROW + 3, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    s.merge(HEADER_ROW, ANS_FIRST, HEADER_ROW, ANS_LAST)
    s.set(HEADER_ROW + 1, NUM_COL, 1.0).set(HEADER_ROW + 1, ANS_FIRST, sub)
    result = GuidedNotesParser.parse(s.snapshot())
    # 不被辨識為子編號 → 該列被當成單題，位置取作答欄首欄，不指向編號右側
    assert result.ok
    assert result.blanks[0].sub_index is None
    assert result.blanks[0].target.col == ANS_FIRST


@pytest.mark.parametrize("synonym", ["題目編號", "編號", "題號 (Q)", "No.", "Question"])
def test_number_header_synonyms_are_not_accepted(synonym):
    """Edge: 表頭同義詞不支援"""
    s = Sheet(5, 8)
    s.set(HEADER_ROW, NUM_COL, synonym).set(HEADER_ROW, ANS_FIRST, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, 1.0)
    result = GuidedNotesParser.parse(s.snapshot())
    assert_atomic_rejection(result)
    assert {i.kind for i in result.issues} == {IssueKind.MISSING_HEADER_NUMBER}


@pytest.mark.parametrize("synonym", ["答案", "Answer", "作答區", "填寫"])
def test_answer_header_synonyms_are_not_accepted(synonym):
    """Edge: 表頭同義詞不支援"""
    s = Sheet(5, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, synonym)
    s.set(HEADER_ROW + 1, NUM_COL, 1.0)
    result = GuidedNotesParser.parse(s.snapshot())
    assert_atomic_rejection(result)
    assert {i.kind for i in result.issues} == {IssueKind.MISSING_HEADER_ANSWER}


def test_all_defects_are_collected_not_just_the_first():
    """FR-015：全部收集後一起回報。"""
    s = Sheet(HEADER_ROW + 6, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, 1.0)
    s.set(HEADER_ROW + 2, NUM_COL, 3.0)  # 跳號
    s.set(HEADER_ROW + 3, NUM_COL, "Q4")  # 非數字
    s.set(HEADER_ROW + 4, ANS_FIRST, "(1)")  # 孤立子空格
    result = GuidedNotesParser.parse(s.snapshot())
    kinds = {i.kind for i in result.issues}
    assert {
        IssueKind.NUMBER_GAP,
        IssueKind.NON_NUMERIC_NUMBER,
        IssueKind.ORPHAN_SUB_BLANK,
    } <= kinds
    assert_atomic_rejection(result)


def test_two_header_blocks_but_only_one_has_valid_questions_is_still_ambiguous():
    """Edge: 兩組表頭但只有一組有合法題目"""
    result = GuidedNotesParser.parse(CASES["two_header_blocks"].snapshot)
    assert_atomic_rejection(result)
    assert {i.kind for i in result.issues} == {IssueKind.AMBIGUOUS_HEADER}


def test_header_present_but_no_questions_is_rejected():
    s = Sheet(6, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, ANS_FIRST, "作答")
    result = GuidedNotesParser.parse(s.snapshot())
    assert_atomic_rejection(result)


def test_question_with_number_but_no_answer_cell_anywhere_is_rejected():
    """Scenario: US4-AS4（題號存在卻找不到任何作答格）"""
    s = Sheet(HEADER_ROW + 2, 4)  # 欄數只到作答表頭那一欄之前：作答欄首欄超出工作表
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, 3, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, 1.0)
    snapshot = s.snapshot(col_count=3)  # 工作表只有 3 欄，作答欄（第 4 欄）不存在
    result = GuidedNotesParser.parse(snapshot)
    assert_atomic_rejection(result)
    assert IssueKind.MISSING_ANSWER_CELL in {i.kind for i in result.issues}
