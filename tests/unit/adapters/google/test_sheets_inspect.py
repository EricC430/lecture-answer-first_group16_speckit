"""`inspect`：先確認是 Google 試算表，再取得工作表清單（手寫回應 JSON）。"""

import asyncio
from urllib.parse import parse_qs, urlparse

import pytest

from lecture_quiz.adapters.google.sheets_reader import INSPECT_FIELDS, SPREADSHEET_MIME
from lecture_quiz.app.guided_notes_import.models import ImportRejection
from tests.unit.adapters.google.mock_google import (
    FakeCredentials,
    make_reader,
    ok,
    sheet_props,
    status,
)


def run(coro):
    return asyncio.run(coro)


def drive_ok(mime: str = SPREADSHEET_MIME):
    return ok({"id": "S1", "name": "學習單", "mimeType": mime})


def test_multiple_sheets_are_listed_in_order():
    """Scenario: US1-AS1"""
    reader, http = make_reader(
        [
            drive_ok(),
            ok(
                {
                    "properties": {"title": "我的試算表"},
                    "sheets": [sheet_props(0, "版面A"), sheet_props(7, "版面B")],
                }
            ),
        ]
    )
    result = run(reader.inspect("ABC234", "S1"))
    assert result.ok and result.value is not None
    assert [(s.sheet_id, s.title, s.hidden) for s in result.value.sheets] == [
        (0, "版面A", False),
        (7, "版面B", False),
    ]
    assert result.value.title == "我的試算表"
    # 先 Drive 後 Sheets，且都是 GET（唯讀）
    uris = [urlparse(r[0]) for r in http.request_sequence]
    assert uris[0].path.startswith("/drive/v3/files/")
    assert (
        "sheets.googleapis.com" in uris[1].netloc or "/v4/spreadsheets/" in uris[1].path
    )
    assert all(r[1] == "GET" for r in http.request_sequence)
    assert parse_qs(uris[1].query)["fields"] == [INSPECT_FIELDS]
    assert parse_qs(uris[0].query)["fields"] == ["id,name,mimeType"]


def test_single_sheet_is_returned_as_a_single_item():
    """Scenario: US1-AS2"""
    reader, _ = make_reader(
        [
            drive_ok(),
            ok({"properties": {"title": "T"}, "sheets": [sheet_props(5, "唯一")]}),
        ]
    )
    result = run(reader.inspect("ABC234", "S1"))
    assert result.value is not None and len(result.value.sheets) == 1


def test_hidden_flag_is_passed_through_for_the_service_to_filter():
    """Scenario: US1-AS2（隱藏旗標交給服務濾除）"""
    reader, _ = make_reader(
        [
            drive_ok(),
            ok(
                {
                    "properties": {"title": "T"},
                    "sheets": [
                        sheet_props(0, "可見"),
                        sheet_props(1, "隱藏", hidden=True),
                    ],
                }
            ),
        ]
    )
    result = run(reader.inspect("ABC234", "S1"))
    assert result.value is not None
    assert [s.hidden for s in result.value.sheets] == [False, True]


@pytest.mark.parametrize(
    "mime",
    [
        "application/vnd.google-apps.document",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    ],
)
def test_non_spreadsheets_are_rejected_before_sheets_is_called(mime):
    """Scenario: US1-AS6"""
    reader, http = make_reader([drive_ok(mime)])
    result = run(reader.inspect("ABC234", "S1"))
    assert result.rejection is ImportRejection.NOT_A_SPREADSHEET
    assert len(http.request_sequence) == 1  # 沒有再呼叫 Sheets


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (401, ImportRejection.AUTH_EXPIRED),
        (403, ImportRejection.PERMISSION_DENIED),
        (404, ImportRejection.PERMISSION_DENIED),
        (429, ImportRejection.READ_FAILED),
        (503, ImportRejection.READ_FAILED),
    ],
)
def test_google_errors_become_rejections_without_raising(code, expected):
    """Scenario: US1-AS4"""
    reader, _ = make_reader([status(code)])
    assert run(reader.inspect("ABC234", "S1")).rejection is expected


def test_not_authorized_never_calls_google():
    """Scenario: US1-AS3"""
    reader, http = make_reader([], FakeCredentials(ImportRejection.NOT_AUTHORIZED))
    assert (
        run(reader.inspect("ABC234", "S1")).rejection is ImportRejection.NOT_AUTHORIZED
    )
    assert http.request_sequence == []
