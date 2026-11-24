"""端點 #1～#6（含 #2 `/oauth/callback`）：授權、選檔與選定來源。"""

import pytest

from lecture_quiz.app.guided_notes_import.models import CallbackResult
from tests.conftest import create_activity
from tests.contract.guided_notes_import.conftest import api

SHEET = "sheet-1"


def test_auth_start_returns_the_google_url(import_client, teacher):
    """Scenario: US1-AS3"""
    r = import_client.post(
        api(teacher.code, "/auth/start"), json={}, headers=teacher.headers
    )
    assert r.status_code == 200
    assert r.json() == {"authUrl": "https://accounts.example.test/auth?state=fake"}


def test_auth_status_and_picker_config(import_client, teacher, fake_auth_gateway):
    """Scenario: US1-AS1"""
    status = import_client.get(
        api(teacher.code, "/auth/status"), headers=teacher.headers
    )
    assert status.status_code == 200 and status.json() == {"authorized": True}
    picker = import_client.get(
        api(teacher.code, "/picker-config"), headers=teacher.headers
    )
    assert picker.status_code == 200
    assert picker.headers["cache-control"] == "no-store"
    assert picker.json() == {
        "accessToken": "fake-token",
        "apiKey": "fake-key",
        "appId": "fake-app",
    }
    fake_auth_gateway.default_authorized = False
    unauthorized = import_client.get(
        api(teacher.code, "/picker-config"), headers=teacher.headers
    )
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "NOT_AUTHORIZED"


def test_inspect_lists_sheets_and_auto_selects_only_when_there_is_one(
    import_client, teacher
):
    """Scenario: US1-AS1、US1-AS2"""
    many = import_client.post(
        api(teacher.code, "/source/inspect"),
        json={"spreadsheetId": SHEET},
        headers=teacher.headers,
    )
    assert many.status_code == 200
    body = many.json()
    assert body["title"] == "學習單"
    assert body["sheets"] == [
        {"sheetId": 0, "title": "版面A"},
        {"sheetId": 7, "title": "版面B"},
    ]
    assert body["autoSelectSheetId"] is None
    one = import_client.post(
        api(teacher.code, "/source/inspect"),
        json={"spreadsheetId": "single-sheet"},
        headers=teacher.headers,
    )
    assert one.json()["autoSelectSheetId"] == 0 and len(one.json()["sheets"]) == 1


def test_one_visible_plus_one_hidden_still_auto_selects(
    import_client, teacher, fake_sheets_reader
):
    """Scenario: US1-AS2（隱藏工作表不列入也不計張數）"""
    fake_sheets_reader.add(
        "mixed", "混合", [(0, "可見", None), (1, "隱藏", None)], hidden=(1,)
    )
    r = import_client.post(
        api(teacher.code, "/source/inspect"),
        json={"spreadsheetId": "mixed"},
        headers=teacher.headers,
    )
    assert r.json()["autoSelectSheetId"] == 0 and len(r.json()["sheets"]) == 1


def test_non_spreadsheet_is_422_with_a_clear_message(import_client, teacher):
    """Scenario: US1-AS6"""
    r = import_client.post(
        api(teacher.code, "/source/inspect"),
        json={"spreadsheetId": "a-pdf"},
        headers=teacher.headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NOT_A_SPREADSHEET"
    assert "Google 試算表" in r.json()["error"]["message"]


def test_put_source_returns_the_selection_and_rejects_unknown_sheets(
    import_client, teacher
):
    """Scenario: US1-AS1"""
    ok = import_client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": SHEET, "sheetId": 7},
        headers=teacher.headers,
    )
    assert ok.status_code == 200
    assert ok.json() == {"spreadsheetId": SHEET, "sheetId": 7, "sheetTitle": "版面B"}
    bad = import_client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": SHEET, "sheetId": 999},
        headers=teacher.headers,
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "SHEET_NOT_FOUND"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/source/inspect", {}),
        ("post", "/source/inspect", {"spreadsheetId": ""}),
        ("post", "/source/inspect", {"spreadsheetId": 5}),
        ("post", "/source/inspect", {"spreadsheetId": None}),
        ("post", "/source/inspect", {"spreadsheetId": "x", "extra": 1}),
        ("post", "/source/inspect", {"spreadsheetId": "x" * 201}),
        ("put", "/source", {"spreadsheetId": "x"}),
        ("put", "/source", {"spreadsheetId": "x", "sheetId": "1"}),
        ("put", "/source", {"spreadsheetId": "x", "sheetId": True}),
        ("put", "/source", {"spreadsheetId": "x", "sheetId": 1.5}),
        ("put", "/source", {"spreadsheetId": "x", "sheetId": None}),
        ("put", "/source", {"spreadsheetId": "x", "sheetId": 1, "more": 1}),
        ("post", "/auth/start", {"unexpected": 1}),
        ("post", "", {"unexpected": 1}),
    ],
)
def test_malformed_requests_are_400_and_change_nothing(
    import_client, teacher, fake_sheets_reader, method, path, body
):
    """Edge: 輸入驗證失敗（FR-021）"""
    before = list(fake_sheets_reader.calls)
    r = getattr(import_client, method)(
        api(teacher.code, path), json=body, headers=teacher.headers
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "INVALID_REQUEST"
    assert fake_sheets_reader.calls == before  # 沒有任何請求送到 Google
    state = import_client.get(api(teacher.code), headers=teacher.headers)
    assert state.json() == {"imported": False}


def test_oauth_callback_redirects_and_never_needs_authorization_header(
    import_client, teacher, fake_auth_gateway
):
    """Scenario: US1-AS3、US1-AS4"""
    for status, expected in (("ok", "ok"), ("denied", "denied"), ("error", "error")):
        fake_auth_gateway.callback_result = CallbackResult(teacher.code, status)
        r = import_client.get(
            "/api/oauth/callback?state=s&code=c", follow_redirects=False
        )
        assert r.status_code == 302
        assert (
            r.headers["location"]
            == f"/teacher.html?code={teacher.code}&auth={expected}"
        )
        assert r.headers["cache-control"] == "no-store"
    fake_auth_gateway.callback_result = CallbackResult(None, "error")
    r = import_client.get("/api/oauth/callback?state=forged", follow_redirects=False)
    assert r.headers["location"] == "/teacher.html?auth=error"  # 不含活動代碼


def test_google_not_configured_is_503_without_variable_names(
    import_client, teacher, fake_auth_gateway
):
    """Edge: 輸入驗證失敗"""
    fake_auth_gateway.configured = False
    for method, path, body in (
        ("post", "/auth/start", {}),
        ("get", "/picker-config", None),
        ("post", "/source/inspect", {"spreadsheetId": SHEET}),
    ):
        kwargs = {"json": body} if body is not None else {}
        r = getattr(import_client, method)(
            api(teacher.code, path), headers=teacher.headers, **kwargs
        )
        assert r.status_code == 503, (path, r.text)
        error = r.json()["error"]
        assert error["code"] == "GOOGLE_NOT_CONFIGURED"
        assert "GOOGLE_" not in error["message"] and "OAUTH" not in error["message"]


def test_no_local_file_upload_endpoint_exists(import_client):
    """Scenario: US1-AS6（FR-005：不提供本地 XLSX 上傳）"""
    paths = import_client.app.openapi()["paths"]
    for path, operations in paths.items():
        assert "upload" not in path.lower() and "xlsx" not in path.lower()
        for operation in operations.values():
            content = operation.get("requestBody", {}).get("content", {})
            assert "multipart/form-data" not in content, path
            assert "application/octet-stream" not in content, path
    found = {
        (path, method.upper())
        for path, operations in paths.items()
        if "/import" in path or "oauth" in path
        for method in operations
    }
    assert found == {
        ("/api/activities/{code}/import", "POST"),
        ("/api/activities/{code}/import", "GET"),
        ("/api/activities/{code}/import/auth/start", "POST"),
        ("/api/activities/{code}/import/auth/status", "GET"),
        ("/api/activities/{code}/import/picker-config", "GET"),
        ("/api/activities/{code}/import/source", "PUT"),
        ("/api/activities/{code}/import/source/inspect", "POST"),
        ("/api/oauth/callback", "GET"),
    }


def test_a_second_teacher_cannot_use_the_first_teachers_activity(
    import_client, teacher
):
    """Edge: 非老師的請求（其他活動的老師）"""
    other = create_activity(import_client)
    assert other.code != teacher.code
    r = import_client.post(
        api(teacher.code, "/auth/start"), json={}, headers=other.headers
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_TEACHER"
