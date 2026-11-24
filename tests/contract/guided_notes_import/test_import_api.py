"""端點 #7（匯入）與 #8（恢復預覽）。"""

from tests.contract.guided_notes_import.conftest import api

SHEET = "sheet-1"


def select(client, teacher, sheet_id=0, spreadsheet=SHEET):
    r = client.put(
        api(teacher.code, "/source"),
        json={"spreadsheetId": spreadsheet, "sheetId": sheet_id},
        headers=teacher.headers,
    )
    assert r.status_code == 200, r.text


def snapshot(client, teacher):
    r = client.get(f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers)
    assert r.status_code == 200
    return r.json()


def test_import_returns_the_result_shape_with_001_version(import_client, teacher):
    """Scenario: US2-AS1、US5-AS1"""
    select(import_client, teacher, 0)
    r = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] is True
    assert body["sheetTitle"] == "版面A"
    assert body["questionNumbers"] == [1, 2, 3, 4]
    assert body["blanksPerQuestion"] == {"1": 2, "2": 2, "3": 1, "4": 1}
    assert (body["totalQuestions"], body["totalBlanks"]) == (4, 6)
    assert (
        body["version"] == snapshot(import_client, teacher)["version"]
    )  # 001 的新版本


def test_import_without_a_selected_source_is_422(import_client, teacher):
    """Scenario: US1-AS1"""
    r = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SOURCE_NOT_SELECTED"


def test_same_idempotency_key_returns_the_first_result_without_reimporting(
    import_client, teacher
):
    """FR-019"""
    select(import_client, teacher, 0)
    headers = {**teacher.headers, "Idempotency-Key": "key-1"}
    first = import_client.post(api(teacher.code), json={}, headers=headers)
    version = snapshot(import_client, teacher)["version"]
    second = import_client.post(api(teacher.code), json={}, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert snapshot(import_client, teacher)["version"] == version  # 沒有重複匯入


def test_get_import_restores_the_preview_after_refresh(import_client, teacher):
    """Scenario: US5-AS1"""
    assert import_client.get(api(teacher.code), headers=teacher.headers).json() == {
        "imported": False
    }
    select(import_client, teacher, 7)
    done = import_client.post(
        api(teacher.code), json={}, headers=teacher.headers
    ).json()
    restored = import_client.get(api(teacher.code), headers=teacher.headers).json()
    assert restored == done
    assert restored["totalBlanks"] == 7  # 版面 B：題組算一題，總格數累計子空格


def test_reimport_replaces_the_previous_result_in_preparing_and_joining(
    import_client, teacher
):
    """Scenario: US5-AS2（準備中與開放加入都可以）"""
    select(import_client, teacher, 0)
    assert (
        import_client.post(
            api(teacher.code), json={}, headers=teacher.headers
        ).status_code
        == 200
    )
    select(import_client, teacher, 7)
    second = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert second.json()["sheetTitle"] == "版面B"
    # 001：老師按「開放加入」之後仍屬第一輪開始前，可以重新匯入
    r = import_client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    assert r.status_code == 200, r.text
    select(import_client, teacher, 0)
    third = import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    assert third.status_code == 200 and third.json()["sheetTitle"] == "版面A"


def test_import_record_for_005_is_kept_by_002(import_client, teacher):
    """FR-024"""
    select(import_client, teacher, 0)
    import_client.post(api(teacher.code), json={}, headers=teacher.headers)
    record = import_client.app.state.import_service.get_import_record(teacher.code)
    assert record is not None and len(record.blanks) == 6
    assert record.structure.data_start_row == 4
    assert (
        record.version
        == import_client.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        ).json()["version"]
    )
