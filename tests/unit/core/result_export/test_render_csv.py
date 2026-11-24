"""CSV 文字（US6）：用標準 csv 解析器嚴格還原。"""

import csv
import io
from datetime import timedelta

from lecture_quiz.core.result_export.csv_export import HEADER, render_csv
from lecture_quiz.core.result_export.models import ExportRow
from tests.unit.core.result_export.helpers import T0

ANSWERS = [
    "含,逗號",
    '含"雙引號"',
    "第一行\n第二行",
    "含\r\n歸位換行",
    "=1+1",
    "+1",
    "-5",
    "@SUM(A1)",
    "\t開頭是tab",
    "普通答案",
    "中文答案",
]


def make_row(answer, i=0, rank=1, ms=0, sub=None, group=3):
    return ExportRow(
        1,
        i + 1,
        sub,
        group,
        answer,
        T0 + timedelta(milliseconds=ms),
        rank,
        rank == 1,
        rank is None,
    )


def parse(text):
    return list(csv.reader(io.StringIO(text, newline="")))


def test_header_is_fixed_nine_columns():
    """Scenario: US6-AS1 / FR-024：表頭固定九欄。"""
    assert HEADER == (
        "輪次",
        "題號",
        "子空格",
        "組別",
        "答案",
        "送出時間",
        "順位",
        "是否成功",
        "是否被判錯",
    )
    assert parse(render_csv(()))[0] == list(HEADER)
    assert render_csv(()).count("\r\n") == 1


def test_special_text_roundtrips_with_nine_columns():
    """Scenario: US6-AS1（SC-007）：特殊文字樣本每列 9 欄、還原差異 0（前綴除外）。"""
    rows = tuple(make_row(a, i) for i, a in enumerate(ANSWERS))
    parsed_rows = parse(render_csv(rows))
    assert len(parsed_rows) == len(ANSWERS) + 1
    assert all(len(r) == 9 for r in parsed_rows)
    for original, line in zip(ANSWERS, parsed_rows[1:], strict=True):
        restored = line[4][1:] if line[4].startswith("'") else line[4]
        assert restored == original


def test_none_values_empty_and_booleans_are_yes_no():
    """Scenario: US6-AS5：順位、子空格為 None 輸出空字串；布林輸出「是」「否」。"""
    ok = parse(render_csv((make_row("a", rank=1, sub=2),)))[1]
    bad = parse(render_csv((make_row("b", rank=None),)))[1]
    assert ok[2] == "2" and ok[6] == "1" and ok[7] == "是" and ok[8] == "否"
    assert bad[2] == "" and bad[6] == "" and bad[7] == "否" and bad[8] == "是"


def test_time_has_timezone_and_millisecond_precision():
    """Scenario: US6-AS4：含時區位移、精度到毫秒，差 1 毫秒的提交輸出不同。"""
    a, b = parse(render_csv((make_row("x", ms=0), make_row("y", ms=1))))[1:]
    assert a[5] == "2026-11-24T20:00:00.000+08:00"
    assert b[5] == "2026-11-24T20:00:00.001+08:00"
    assert a[5] != b[5]


def test_crlf_line_endings_and_determinism():
    """行結尾為 CRLF；相同輸入逐位元組相同。"""
    rows = (make_row("x"), make_row("y", 1))
    text = render_csv(rows)
    assert text.endswith("\r\n") and "\n" not in text.replace("\r\n", "")
    assert text == render_csv(rows)
    assert text.encode("utf-8") == render_csv(rows).encode("utf-8")
