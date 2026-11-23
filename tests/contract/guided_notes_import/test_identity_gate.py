"""身分與階段閘門：每個端點（#1、#3～#8）（FR-025、FR-020）。"""

import pytest

from tests.conftest import create_activity
from tests.contract.guided_notes_import.conftest import api

SHEET = "sheet-1"
ENDPOINTS = [
    ("post", "/auth/start", {}),
    ("get", "/auth/status", None),
    ("get", "/picker-config", None),
    ("post", "/source/inspect", {"spreadsheetId": SHEET}),
    ("put", "/source", {"spreadsheetId": SHEET, "sheetId": 0}),
    ("post", "", {}),
    ("get", "", None),
]


def request(client, code, method, path, body, headers):
    kwargs = {"json": body} if body is not None else {}
    return getattr(client, method)(api(code, path), headers=headers, **kwargs)


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_students_and_other_teachers_are_rejected_without_changes(
    import_client, teacher, fake_sheets_reader, method, path, body
):
    """Edge: 非老師的請求"""
    other = create_activity(import_client)
    for headers in ({}, other.headers, {"Authorization": "Bearer not-a-real-token"}):
        r = request(import_client, teacher.code, method, path, body, headers)
        assert r.status_code == 403, (method, path, r.text)
        assert r.json()["error"]["code"] == "NOT_TEACHER"
    assert fake_sheets_reader.calls == []
    assert import_client.get(api(teacher.code), headers=teacher.headers).json() == {
        "imported": False
    }


@pytest.mark.parametrize(("method", "path", "body"), ENDPOINTS)
def test_unknown_activity_is_404_without_token_and_410_with_token(
    import_client, teacher, method, path, body
):
    """Edge: 活動代碼不存在"""
    anonymous = request(import_client, "ZZZZZZ", method, path, body, {})
    assert anonymous.status_code == 404
    assert anonymous.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"
    with_token = request(import_client, "ZZZZZZ", method, path, body, teacher.headers)
    assert with_token.status_code == 410
    assert with_token.json()["error"]["code"] == "ACTIVITY_GONE"


def start_first_round(client, teacher):
    client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": SHEET, "sheetId": 0},
        headers=teacher.headers,
    )
    assert (
        client.post(api(teacher.code), json={}, headers=teacher.headers).status_code
        == 200
    )
    r = client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": [1], "fairMode": False},
        headers=teacher.headers,
    )
    assert r.status_code == 201, r.text


def test_after_the_first_round_changes_are_409_round_started(import_client, teacher):
    """Scenario: US6-AS1"""
    start_first_round(import_client, teacher)
    before = import_client.get(api(teacher.code), headers=teacher.headers).json()
    for method, path, body in (
        ("put", "/source", {"spreadsheetId": SHEET, "sheetId": 7}),
        ("post", "", {}),
    ):
        r = request(import_client, teacher.code, method, path, body, teacher.headers)
        assert r.status_code == 409, r.text
        assert r.json()["error"]["code"] == "ROUND_STARTED"
        assert "搶答已開始" in r.json()["error"]["message"]
    # 預覽仍可查看；來源映射與題目不變
    assert (
        import_client.get(api(teacher.code), headers=teacher.headers).json() == before
    )


def test_cancelled_activity_says_cancelled(import_client, teacher):
    """Edge: 活動不在「準備中」"""
    r = import_client.post(
        f"/api/activities/{teacher.code}/cancel", json={}, headers=teacher.headers
    )
    assert r.status_code == 200, r.text
    r = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ACTIVITY_CANCELLED"
    assert "已取消" in r.json()["error"]["message"]


def test_stage_changed_between_parse_and_write_is_409_gateway_rejected(
    import_client, teacher, fake_sheets_reader
):
    """Edge: 解析後、寫入前階段或身分改變"""
    import_client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": SHEET, "sheetId": 0},
        headers=teacher.headers,
    )

    original_read = fake_sheets_reader.read

    async def read_then_cancel(code, source):
        result = await original_read(code, source)
        service = import_client.app.state.activity_service
        requester = service.resolve_requester(teacher.code, teacher.token)
        await service.cancel(teacher.code, requester)
        return result

    fake_sheets_reader.read = read_then_cancel  # type: ignore[method-assign]
    r = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert r.status_code == 409 and r.json()["error"]["code"] == "GATEWAY_REJECTED"
