"""422 `VALIDATION_FAILED` 的 `issues` 形狀（FR-022、SC-004）。"""

import re

from tests.contract.guided_notes_import.conftest import api
from tests.fixtures.guided_notes_layouts import (
    HEADER_ROW,
    NUM_COL,
    defect_cases,
    layout_a,
)
from tests.unit.core.guided_notes_import.helpers import Sheet

FORBIDDEN = re.compile(
    r"Traceback|File \"|\.py|[A-Za-z]:\\|token|secret", re.IGNORECASE
)


def import_bad(client, teacher, reader, snapshot):
    reader.add("bad", "壞的", [(0, "壞", snapshot)])
    r = client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": "bad", "sheetId": 0},
        headers=teacher.headers,
    )
    assert r.status_code == 200
    return client.post(api(teacher.code), json={}, headers=teacher.headers)


def test_issue_shape_one_based_rows_and_column_letters(
    import_client, teacher, fake_sheets_reader
):
    """Scenario: US4-AS3"""
    r = import_bad(
        import_client,
        teacher,
        fake_sheets_reader,
        defect_cases()["number_gap"].snapshot,
    )
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "VALIDATION_FAILED"
    assert "message" in error and error["issues"]
    issue = error["issues"][0]
    assert set(issue) == {"kind", "row", "col", "quoted", "hint"}
    assert issue["kind"] == "NUMBER_GAP"
    assert issue["row"] == 6  # 內部列索引 5（0 起算）→ 顯示第 6 列
    assert issue["col"] == "B"  # 題號欄 index 1 → B
    assert issue["hint"]


def test_issue_without_a_position_has_null_row_and_col(
    import_client, teacher, fake_sheets_reader
):
    """Scenario: US4-AS1"""
    r = import_bad(
        import_client,
        teacher,
        fake_sheets_reader,
        defect_cases()["missing_number_header"].snapshot,
    )
    issue = r.json()["error"]["issues"][0]
    assert issue["kind"] == "MISSING_HEADER_NUMBER"
    assert issue["row"] is None and issue["col"] is None


def test_untrusted_cell_text_is_returned_as_plain_text_and_truncated(
    import_client, teacher, fake_sheets_reader
):
    """Edge: 不可信的儲存格文字"""
    s = Sheet(HEADER_ROW + 3, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, 6, "作答")
    s.set(HEADER_ROW + 1, NUM_COL, "<script>alert(1)</script>" + "x" * 100)
    r = import_bad(import_client, teacher, fake_sheets_reader, s.snapshot())
    quoted = r.json()["error"]["issues"][0]["quoted"]
    assert quoted.startswith("<script>alert(1)</script>")  # 原樣當純文字回傳，不改寫
    assert len(quoted) <= 40  # 後端已截斷


def test_response_has_no_stack_paths_or_credentials(
    import_client, teacher, fake_sheets_reader
):
    """FR-022、SC-005"""
    for name in ("number_gap", "target_overlap", "orphan_sub_blank", "empty_sheet"):
        r = import_bad(
            import_client, teacher, fake_sheets_reader, defect_cases()[name].snapshot
        )
        assert r.status_code == 422
        assert FORBIDDEN.search(r.text) is None, r.text


def test_a_rejected_import_keeps_the_previous_result(
    import_client, teacher, fake_sheets_reader
):
    """Scenario: US4-AS5"""
    good, _ = layout_a()
    fake_sheets_reader.add("good", "好的", [(0, "好", good)])
    import_client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": "good", "sheetId": 0},
        headers=teacher.headers,
    )
    first = import_client.post(
        api(teacher.code), json={}, headers=teacher.headers
    ).json()
    bad = import_bad(
        import_client,
        teacher,
        fake_sheets_reader,
        defect_cases()["number_gap"].snapshot,
    )
    assert bad.status_code == 422
    assert import_client.get(api(teacher.code), headers=teacher.headers).json() == first
