"""US5 端到端：真實 001～004，下載 CSV 並以 csv.reader 逐列比對。"""

import csv
import io

from lecture_quiz.core.result_export.csv_export import HEADER


def parse(response):
    assert response.status_code == 200, response.text
    return list(
        csv.reader(io.StringIO(response.content.decode("utf-8-sig"), newline=""))
    )


def test_group_questions_wrong_marks_and_unfinalized_round(export_stack):
    """Scenario: US5-AS1～AS4：題組、答錯、搶答失敗、無人提交與未定案輪次。"""
    s = export_stack("a")
    s.join(1, 2, 3)
    s.open_round()
    s.submit(1, 1, 1, ["甲一", "甲二"])  # 題 1（兩格題組）：組 1 最早
    s.submit(1, 1, 2, ["乙一", "乙二"])
    s.submit(1, 3, 3, ["單題"])  # 題 3（單題）
    s.close()
    s.judge(1, 1, 1, True)  # 組 1 的題組整筆判錯 → 組 2 遞補
    s.finalize()
    s.open_round([2, 4])  # 第 2 輪（未定案）
    s.submit(2, 2, 3, ["暫時一", "暫時二"])

    rows = parse(s.export("GET", "/csv"))
    assert rows[0] == list(HEADER) and all(len(r) == 9 for r in rows)
    body = rows[1:]
    assert {r[0] for r in body} == {"1"}, "未定案輪次不納入"
    q1 = [r for r in body if r[1] == "1"]
    assert len(q1) == 4  # 兩組各兩個子空格
    wrong = [r for r in q1 if r[3] == "1"]
    winner = [r for r in q1 if r[3] == "2"]
    assert [(r[2], r[4], r[6], r[7], r[8]) for r in wrong] == [
        ("1", "甲一", "", "否", "是"),
        ("2", "甲二", "", "否", "是"),
    ]
    assert [(r[2], r[4], r[6], r[7], r[8]) for r in winner] == [
        ("1", "乙一", "1", "是", "否"),
        ("2", "乙二", "1", "是", "否"),
    ]
    q3 = [r for r in body if r[1] == "3"]
    assert len(q3) == 1 and q3[0][2] == "" and q3[0][7] == "是"
    assert all(r[1] not in ("2", "4") for r in body)  # 沒有定案的題不虛構


def test_header_only_before_any_finalized_round(export_stack):
    """Scenario: US5-AS3：尚無已定案輪次 → 只有表頭。"""
    s = export_stack("a")
    s.join(1)
    s.open_round()
    s.submit(1, 1, 1, ["暫時", "暫時"])
    assert parse(s.export("GET", "/csv")) == [list(HEADER)]
