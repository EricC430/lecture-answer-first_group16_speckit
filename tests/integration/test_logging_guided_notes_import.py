"""日誌不得含機敏資料（技術限制 3、原則 V；FR-022）。

走完授權、匯入成功與各種失敗後，伺服端日誌只含活動代碼、端點名稱、結果代碼、題數、格數與
001 版本；不含 token、授權碼、`state`、client secret、試算表標題與儲存格內容。
（TestClient 自己的 `httpx` 日誌是測試端的，不是伺服端，
這裡只檢查伺服端與 Google 程式庫的記錄。）
"""

import ast
import logging
from pathlib import Path

from tests.conftest import create_activity
from tests.fixtures.guided_notes_layouts import defect_cases
from tests.unit.app.guided_notes_import.fakes import CallbackResult

SRC = Path(__file__).resolve().parents[2] / "src" / "lecture_quiz"
SECRETS = (
    "fake-token",
    "fake-key",
    "fake-app",
    "SECRET-AUTH-CODE",
    "SECRET-STATE-VALUE",
    "學習單",  # 試算表標題
    "版面A",  # 工作表標題
    "敘述 1",  # 儲存格內容
    "Week 3",
    "<script>",
)


def server_log_text(caplog) -> str:
    return "\n".join(
        r.getMessage()
        for r in caplog.records
        if r.name.startswith(("lecture_quiz", "googleapiclient", "google"))
    )


def test_full_flow_logs_contain_no_secrets(
    import_client, fake_auth_gateway, fake_sheets_reader, caplog
):
    caplog.set_level(logging.DEBUG)
    teacher = create_activity(import_client)
    base = f"/api/activities/{teacher.code}/import"
    h = teacher.headers
    import_client.post(f"{base}/auth/start", json={}, headers=h)
    fake_auth_gateway.callback_result = CallbackResult(teacher.code, "ok")
    import_client.get(
        "/api/oauth/callback?state=SECRET-STATE-VALUE&code=SECRET-AUTH-CODE",
        follow_redirects=False,
    )
    import_client.get(f"{base}/picker-config", headers=h)
    import_client.post(
        f"{base}/source/inspect", json={"spreadsheetId": "sheet-1"}, headers=h
    )
    import_client.put(
        f"{base}/source", json={"spreadsheetId": "sheet-1", "sheetId": 0}, headers=h
    )
    assert import_client.post(base, json={}, headers=h).status_code == 200
    bad = defect_cases()["number_gap"].snapshot
    fake_sheets_reader.add("bad", "壞的<script>", [(0, "壞", bad)])
    import_client.put(
        f"{base}/source", json={"spreadsheetId": "bad", "sheetId": 0}, headers=h
    )
    assert import_client.post(base, json={}, headers=h).status_code == 422
    import_client.get(base, headers={})  # 學生
    text = server_log_text(caplog)
    assert text, "應該有伺服端日誌可檢查"
    for secret in SECRETS:
        assert secret not in text, secret
    assert "壞的" not in text
    # 成功匯入的請求日誌有活動代碼、結果代碼與 001 版本
    assert (
        f"activity={teacher.code}" in text
        and "result=OK" in text
        and "version=" in text
    )
    assert "VALIDATION_FAILED" in text and "NOT_TEACHER" in text


def test_no_print_in_guided_notes_import_code():
    """技術限制 3：只用 logging，不用 print。"""
    paths = [
        *(SRC / "core" / "guided_notes_import").rglob("*.py"),
        *(SRC / "app" / "guided_notes_import").rglob("*.py"),
        *(SRC / "adapters" / "google").rglob("*.py"),
        SRC / "adapters" / "web" / "guided_notes_import.py",
    ]
    assert len(paths) >= 15
    offenders = []
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []
