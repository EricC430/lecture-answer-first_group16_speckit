"""CSV 資料列（US5）。"""

import pytest

from lecture_quiz.core.result_export.csv_export import build_rows
from tests.unit.core.result_export.helpers import (
    T0,
    entry,
    fact,
    mixed_world,
    parsed,
    targets,
)


def rows_for(entries, submissions, p=None):
    p = p or parsed("a")
    return build_rows(entries, submissions, targets(p))


def test_group_question_with_wrong_group_gives_four_rows():
    """Scenario: US5-AS1（題組與判錯紀錄）：兩組各提交兩格題組、一組被判錯。"""
    entries = (entry(1, 1, 1, 1), entry(1, 1, 2, None, True))
    subs = (fact(1, 1, 1, ("甲一", "甲二"), 1), fact(1, 1, 2, ("乙一", "乙二"), 2))
    rows = rows_for(entries, subs)
    assert len(rows) == 4
    ok = [r for r in rows if r.group_number == 1]
    bad = [r for r in rows if r.group_number == 2]
    assert [(r.rank, r.succeeded, r.judged_wrong, r.sub_index) for r in ok] == [
        (1, True, False, 1),
        (1, True, False, 2),
    ]
    assert [(r.rank, r.succeeded, r.judged_wrong, r.sub_index) for r in bad] == [
        (None, False, True, 1),
        (None, False, True, 2),
    ]
    assert [r.answer for r in bad] == ["乙一", "乙二"]


def test_three_candidates_failed_are_not_wrong():
    """Scenario: US5-AS4：排名 1、2、3 都沒被判錯；只有順位 1 成功，其餘不算答錯。"""
    entries = (entry(1, 3, 5, 3), entry(1, 3, 6, 1), entry(1, 3, 7, 2))
    subs = (
        fact(1, 3, 5, ("c",), 3),
        fact(1, 3, 6, ("a",), 1),
        fact(1, 3, 7, ("b",), 2),
    )
    rows = rows_for(entries, subs)
    assert [(r.group_number, r.rank, r.succeeded, r.judged_wrong) for r in rows] == [
        (6, 1, True, False),
        (7, 2, False, False),
        (5, 3, False, False),
    ]
    assert all(r.sub_index is None for r in rows)  # 單題子空格留空


def test_order_wrong_after_ranked_and_by_receive_time():
    """Scenario: US5-AS4 / FR-026：依輪次、題號、順位；被判錯者排後、依接收時間。"""
    entries = (
        entry(1, 3, 1, None, True),
        entry(1, 3, 2, 1),
        entry(1, 3, 3, None, True),
        entry(1, 4, 4, 1),
    )
    subs = (
        fact(1, 3, 1, ("w2",), 9),
        fact(1, 3, 2, ("ok",), 1),
        fact(1, 3, 3, ("w1",), 4),
        fact(1, 4, 4, ("q4",), 2),
    )
    rows = rows_for(entries, subs)
    assert [(r.question_number, r.group_number) for r in rows] == [
        (3, 2),
        (3, 3),
        (3, 1),
        (4, 4),
    ]


def test_no_invented_rows_and_unfinalized_input_is_not_expanded():
    """Scenario: US5-AS2 ↔ OpenSpec「沒有提交與未定案輪次」：沒有 entry 就沒有列。"""
    w = mixed_world()
    # 傳入含未定案輪次 3 的提交，但沒有對應 entry → 不產生列
    extra = fact(3, 1, 1, ("暫時",), 50)
    rows = build_rows(w["entries"], (*w["submissions"], extra), w["blanks"])
    assert all(r.round_number != 3 for r in rows)
    assert all(r.question_number != 4 for r in rows)  # 無人提交的題不虛構
    assert build_rows((), w["submissions"], w["blanks"]) == ()


def test_multi_round_distinguished_by_round():
    """Scenario: US5-AS6：同一題兩輪的提交各有列並以輪次區分。"""
    w = mixed_world()
    rows = build_rows(w["entries"], w["submissions"], w["blanks"])
    q2 = [r for r in rows if r.question_number == 2]
    assert {r.round_number for r in q2} == {1, 2}
    r1 = [r for r in q2 if r.round_number == 1]
    assert all(r.judged_wrong and r.rank is None for r in r1)
    assert [r.sub_index for r in q2 if r.round_number == 2] == [1, 2]


def test_missing_submission_fails_loudly_and_is_deterministic():
    """找不到對應提交時明確失敗；相同輸入輸出相同。"""
    with pytest.raises(ValueError):
        rows_for((entry(1, 3, 2, 1),), ())
    w = mixed_world()
    a = build_rows(w["entries"], w["submissions"], w["blanks"])
    assert a == build_rows(w["entries"], w["submissions"], w["blanks"])
    assert a[0].received_at.tzinfo is not None and a[0].received_at >= T0
