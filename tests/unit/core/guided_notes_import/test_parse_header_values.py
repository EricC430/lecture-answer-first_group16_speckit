"""表頭與題號值的辨識（US2-AS3、AS4、AS5）。"""

from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import layout_a, layout_b, single_template
from tests.unit.core.guided_notes_import.helpers import Sheet


def test_headers_with_half_and_full_width_spaces_are_recognised():
    """Scenario: US2-AS3"""
    s = Sheet(4, 6)
    s.set(0, 0, "　 題號 　").set(0, 3, "	作答 ")
    s.set(1, 0, 1.0).set(2, 0, 2.0)
    result = GuidedNotesParser.parse(s.snapshot())
    assert result.ok, result.issues
    assert [q.number for q in result.questions] == [1, 2]


def test_numeric_one_and_text_one_are_both_question_one():
    """Scenario: US2-AS4"""
    for value in (1.0, "1", " 1 ", 1):
        s = Sheet(3, 5)
        s.set(0, 0, "題號").set(0, 3, "作答").set(1, 0, value)
        result = GuidedNotesParser.parse(s.snapshot())
        assert result.ok, (value, result.issues)
        assert [q.number for q in result.questions] == [1]


def test_description_text_is_never_stored_or_shown():
    """Scenario: US2-AS5"""
    for build in (layout_a, layout_b, single_template):
        snapshot, _ = build()
        result = GuidedNotesParser.parse(snapshot)
        assert result.ok
        dump = repr(result)
        for ref, value in snapshot.cells.items():
            if ref.col == 2 and value.text:  # 題目敘述欄（版面 A、單題範本）
                assert value.text not in dump
        for secret in ("敘述 1", "題目 1", "內容", "Week", "學習單"):
            assert secret not in dump
