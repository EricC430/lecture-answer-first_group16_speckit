"""單題學習單解析（US2）。"""

from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import single_template


def summarize(result):
    return (
        tuple((q.number, q.blank_count, q.is_group) for q in result.questions),
        tuple(
            (b.question_number, b.sub_index, (b.target.row, b.target.col))
            for b in result.blanks
        ),
    )


def test_single_template_six_questions_six_blanks():
    """Scenario: US2-AS1"""
    snapshot, expected = single_template()
    result = GuidedNotesParser.parse(snapshot)
    assert result.ok, result.issues
    assert len(result.questions) == 6
    assert len(result.blanks) == 6
    assert summarize(result) == (expected.questions, expected.blanks)
    # 答案位置是橫向合併範圍的左上角（首欄），不是範圍內的其他格
    assert {b.target.col for b in result.blanks} == {4 + 1}


def test_shifted_and_renamed_sheet_gives_same_counts_new_positions():
    """Scenario: US2-AS2"""
    base_snapshot, base_expected = single_template(origin=(0, 0), sheet_name="單題")
    moved_snapshot, moved_expected = single_template(
        origin=(9, 5), sheet_name="完全不同的名稱"
    )
    base = GuidedNotesParser.parse(base_snapshot)
    moved = GuidedNotesParser.parse(moved_snapshot)
    assert base.ok and moved.ok
    assert [(q.number, q.blank_count) for q in base.questions] == [
        (q.number, q.blank_count) for q in moved.questions
    ]
    assert len(base.blanks) == len(moved.blanks) == 6
    assert summarize(moved) == (moved_expected.questions, moved_expected.blanks)
    for old, new in zip(base.blanks, moved.blanks, strict=True):
        assert (new.target.row - old.target.row, new.target.col - old.target.col) == (
            9,
            5,
        )
