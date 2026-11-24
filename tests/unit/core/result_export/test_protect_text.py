"""CSV 公式字元文字保護（US6）。"""

import csv
import io

import pytest

from lecture_quiz.core.result_export.csv_export import protect_text, render_csv
from lecture_quiz.core.result_export.models import ExportRow
from tests.unit.core.result_export.helpers import T0


@pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
def test_formula_leading_characters_get_prefix(lead):
    """Scenario: US6-AS2 ↔ OpenSpec「特殊文字匯出」：公式字元開頭加保護前綴。"""
    assert protect_text(lead + "x") == "'" + lead + "x"


@pytest.mark.parametrize("value", ["", "普通", "1+1", "a=b", "'已有前綴", "中文"])
def test_other_text_is_unchanged(value):
    """Scenario: US6-AS2：其他字元或空字串原樣。"""
    assert protect_text(value) == value


def test_negative_number_answer_is_protected():
    """答案 -5 也被保護（介面說明涵蓋）。"""
    assert protect_text("-5") == "'-5"


def test_only_group_and_answer_columns_are_protected():
    """Scenario: US6-AS2：只保護組別與答案，輪次、題號、時間、順位、是／否不加前綴。"""
    row = ExportRow(1, 2, None, 3, "=HYPERLINK()", T0, 1, True, False)
    line = list(csv.reader(io.StringIO(render_csv((row,)), newline="")))[1]
    assert line[4] == "'=HYPERLINK()"
    assert line[0] == "1" and line[1] == "2" and line[3] == "3"
    assert not line[5].startswith("'") and line[6] == "1"
    assert line[7] == "是" and line[8] == "否"


def test_removing_first_quote_restores_original():
    """保護後以 csv.reader 解析，去掉第一個 ' 即為原答案。"""
    original = "=1+1"
    row = ExportRow(1, 1, None, 1, original, T0, 1, True, False)
    cell = list(csv.reader(io.StringIO(render_csv((row,)), newline="")))[1][4]
    assert cell[1:] == original
