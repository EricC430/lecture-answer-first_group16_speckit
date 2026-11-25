"""US6 端到端：公式字元只在 CSV 被保護；原始提交、004 結果與寫回的答案不受影響。"""

import csv
import io

from tests.fixtures.guided_notes_layouts import layout_a

TRICKY_GROUP = ["含,逗號\n第二行", '含"雙引號"']
FORMULA = "=1+1"


def build(export_stack):
    s = export_stack("a")
    s.join(1)
    s.open_round()
    s.submit(1, 1, 1, TRICKY_GROUP)  # 題 1：兩格題組
    s.submit(1, 3, 1, [FORMULA])  # 題 3：單題，答案以等號開頭
    s.close()
    s.finalize()
    return s


def test_csv_protects_but_nothing_else_is_modified(export_stack):
    """Scenario: US6-AS3：保護前綴只在 CSV；原始提交與寫回的答案都沒有。"""
    s = build(export_stack)
    data = s.export("GET", "/csv").content
    assert data.startswith("\ufeff".encode()), "UTF-8 BOM"
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    assert all(len(r) == 9 for r in rows)
    q3 = [r for r in rows[1:] if r[1] == "3"][0]
    assert q3[4] == "'" + FORMULA
    q1 = [r for r in rows[1:] if r[1] == "1"]
    assert [r[4] for r in q1] == TRICKY_GROUP  # 逗號、引號、換行正確還原

    originals = {
        s_.question_number: s_.answers
        for s_ in s.client.app.state.submission_service.all_submissions(s.code)
    }
    assert originals[3] == (FORMULA,) and originals[1] == tuple(TRICKY_GROUP)

    preview = s.export("POST", "/preview").json()
    s.export("POST", "/writes", {"snapshotId": preview["snapshotId"]})
    sent = {text for call in s.writer.write_calls for _, text in call}
    assert FORMULA in sent and "'" + FORMULA not in sent
    _, expected = layout_a()
    pos = next(p for q, sub, p in expected.blanks if q == 3)
    assert s.cell_text(*pos) == FORMULA


def test_chinese_header_and_yes_no_columns(export_stack):
    """Scenario: US6-AS5：繁體中文表頭與答案可還原，布林顯示「是」「否」。"""
    s = build(export_stack)
    text = s.export("GET", "/csv").content.decode("utf-8-sig")
    assert text.startswith(
        "輪次,題號,子空格,組別,答案,送出時間,順位,是否成功,是否被判錯"
    )
    rows = list(csv.reader(io.StringIO(text, newline="")))
    assert {r[7] for r in rows[1:]} <= {"是", "否"}
    assert {r[8] for r in rows[1:]} <= {"是", "否"}
    assert (
        rows[1][5].endswith(("+00:00", "Z"))
        or "+" in rows[1][5]
        or "-" in rows[1][5][10:]
    )
