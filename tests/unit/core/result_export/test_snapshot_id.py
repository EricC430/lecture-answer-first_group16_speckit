"""成果快照識別（US1-AS3）。"""

from lecture_quiz.core.result_export.snapshot import snapshot_id_of


def test_id_is_sorted_dot_joined():
    """Scenario: US1-AS3（預覽後新增定案結果）：輪次集合決定識別，與順序無關。"""
    assert snapshot_id_of({1, 2}) == "1.2"
    assert snapshot_id_of([2, 1, 2]) == "1.2"
    assert snapshot_id_of(()) == ""


def test_new_round_changes_id_and_repeat_is_stable():
    """Scenario: US1-AS3：新輪次定案後識別改變；重複計算相同。"""
    assert snapshot_id_of({1}) != snapshot_id_of({1, 2})
    assert snapshot_id_of({1, 2}) == snapshot_id_of({1, 2})
