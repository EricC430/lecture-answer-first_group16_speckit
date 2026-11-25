"""成果快照與覆寫影響（US1）。"""

import pytest

from lecture_quiz.core.result_export.models import OverwriteImpact
from lecture_quiz.core.result_export.snapshot import build_snapshot
from tests.unit.core.result_export.helpers import (
    cell,
    cur_empty,
    cur_other,
    cur_text,
    fact,
    fq,
    mixed_world,
    parsed,
    targets,
)


def build(world=None, current=None):
    w = world or mixed_world()
    return build_snapshot(
        w["finalized_questions"],
        w["submissions"],
        w["blanks"],
        w["question_numbers"],
        current or {},
        w["round_numbers"],
    )


def test_only_finalized_winners_are_written():
    """Scenario: US1-AS1（活動中匯出歷史成果）：只含已定案且有搶答成功者的題。"""
    snap = build()
    keys = [(i.round_number, i.question_number, i.sub_index) for i in snap.items]
    assert keys == [(1, 1, 1), (1, 1, 2), (2, 2, 1), (2, 2, 2), (1, 3, None)]
    # 沒有任何第 1 輪第 2 題的項目（該輪全被判錯）
    assert all(not (i.round_number == 1 and i.question_number == 2) for i in snap.items)


def test_items_have_required_fields():
    """Scenario: US1-AS2：每個子空格一列，含題號、子空格、成功者、答案、目標、影響。"""
    snap = build()
    first = snap.items[0]
    assert first.question_number == 1 and first.sub_index == 1
    assert first.group_number == 1 and first.answer == "甲一"
    assert first.target == cell(4, 7)
    assert first.impact is OverwriteImpact.EMPTY
    single = [i for i in snap.items if i.question_number == 3][0]
    assert single.sub_index is None and single.target == cell(8, 6)


def test_unwritten_questions_listed_sorted():
    """Scenario: US1-AS2：無人提交、全被判錯、尚未成功的題另列。"""
    snap = build()
    assert snap.unwritten_questions == (4,)
    w = mixed_world()
    only_round_one = build_snapshot(
        w["finalized_questions"][:3],
        w["submissions"][:5],
        w["blanks"],
        w["question_numbers"],
        {},
        (1,),
    )
    assert only_round_one.unwritten_questions == (2, 4)


def test_overwrite_impact_kinds_and_truncation():
    """Scenario: US1-AS2：EMPTY／REPLACE（附原內容，截斷 40 字）／SAME。"""
    long = "字" * 60
    current = {
        cell(4, 7): cur_text("甲一"),  # 逐字相同
        cell(5, 7): cur_text(long),  # 不同文字
        cell(6, 7): cur_other("123"),  # 數字
        cell(7, 7): cur_empty(),
    }
    snap = build(current=current)
    by_target = {i.target: i for i in snap.items}
    assert by_target[cell(4, 7)].impact is OverwriteImpact.SAME
    replaced = by_target[cell(5, 7)]
    assert replaced.impact is OverwriteImpact.REPLACE
    assert replaced.current_display == "字" * 40
    assert by_target[cell(6, 7)].impact is OverwriteImpact.REPLACE
    assert by_target[cell(6, 7)].current_display == "123"
    assert by_target[cell(7, 7)].impact is OverwriteImpact.EMPTY
    assert by_target[cell(7, 7)].current_display is None


def test_number_with_same_digits_is_not_same():
    """Scenario: US1-AS2：數字 123 與文字答案 "123" 不算內容相同（型別會改變）。"""
    p = parsed("a")
    w = {
        "finalized_questions": (fq(1, 3, 1),),
        "submissions": (fact(1, 3, 1, ("123",)),),
        "blanks": targets(p),
        "question_numbers": (1, 2, 3, 4),
        "round_numbers": (1,),
    }
    snap = build_snapshot(
        w["finalized_questions"],
        w["submissions"],
        w["blanks"],
        w["question_numbers"],
        {cell(8, 6): cur_other("123")},
        (1,),
    )
    assert snap.items[0].impact is OverwriteImpact.REPLACE


def test_multi_round_question_written_once():
    """Scenario: US5-AS6 的寫回面：先前全被判錯、第二輪成功的題只寫成功那一筆。"""
    snap = build()
    q2 = [i for i in snap.items if i.question_number == 2]
    assert {i.round_number for i in q2} == {2} and len(q2) == 2


def test_inconsistent_data_fails_loudly():
    """資料不一致時明確失敗，不略過。"""
    w = mixed_world()
    with pytest.raises(ValueError):  # 找不到搶答成功者的提交
        build_snapshot(
            w["finalized_questions"],
            w["submissions"][1:],
            w["blanks"],
            w["question_numbers"],
            {},
            w["round_numbers"],
        )
    with pytest.raises(ValueError):  # answers 長度不等於格數
        build_snapshot(
            (fq(1, 1, 1),),
            (fact(1, 1, 1, ("只有一格",)),),
            w["blanks"],
            w["question_numbers"],
            {},
            (1,),
        )
    with pytest.raises(ValueError):  # 同一題兩個搶答成功者
        build_snapshot(
            (fq(1, 3, 2), fq(2, 3, 3)),
            (fact(1, 3, 2, ("a",)), fact(2, 3, 3, ("b",))),
            w["blanks"],
            w["question_numbers"],
            {},
            (1, 2),
        )


def test_snapshot_is_deterministic():
    """相同輸入輸出逐項相同。"""
    assert build() == build()
