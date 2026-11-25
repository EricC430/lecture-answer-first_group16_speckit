"""X1、X2 的端點契約（US1）。"""

from tests.contract.result_export.conftest import url
from tests.unit.app.result_export.world import SOURCE  # noqa: F401


def post(env, path, body=None, headers=None):
    return env.client.post(
        url(env, path),
        json=body if body is not None else {},
        headers=headers or env.teacher.headers,
    )


def test_preview_shape_and_a1_targets(api_env):
    """Scenario: US1-AS2：回應形狀符合 http-api.md，target 由列欄換算成 A1。"""
    env = api_env()
    response = post(env, "/preview")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "snapshotId",
        "canConfirm",
        "structure",
        "items",
        "unwrittenQuestions",
        "sheetTitle",
    }
    assert body["snapshotId"] == "1.2" and body["canConfirm"] is True
    assert body["structure"] == {"ok": True, "differences": [], "moreDifferences": 0}
    item = body["items"][0]
    assert set(item) == {
        "roundNumber",
        "questionNumber",
        "subIndex",
        "groupNumber",
        "answer",
        "target",
        "impact",
        "currentDisplay",
    }
    # 版面 A 的題 1 第一個子空格在（列 4, 欄 7）→ H5
    assert item["target"] == "H5" and item["impact"] == "EMPTY"
    assert body["unwrittenQuestions"] == [4]


def test_write_returns_attempt(api_env):
    """Scenario: US1-AS1：確認寫回回傳嘗試，三個格數與總格數一致。"""
    env = api_env()
    snapshot_id = post(env, "/preview").json()["snapshotId"]
    response = post(env, "/writes", {"snapshotId": snapshot_id})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "SUCCESS" and body["kind"] == "WRITE"
    assert body["confirmedCells"] == body["totalCells"] > 0
    assert body["alreadyInProgress"] is False


def test_invalid_requests_are_400(api_env):
    """INVALID_REQUEST：缺 snapshotId、非字串。"""
    env = api_env()
    for body in ({}, {"snapshotId": 5}, {"snapshotId": None}):
        response = post(env, "/writes", body)
        assert (
            response.status_code == 400
            and response.json()["error"]["code"] == "INVALID_REQUEST"
        )
    assert env.writer.write_calls == []


def test_identity_and_stage_errors(api_env):
    """身分與階段錯誤：403、410、404、409 各一。"""
    env = api_env()
    student = {"Authorization": "Bearer nobody"}
    r = post(env, "/preview", headers=student)
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_TEACHER"
    gone = env.client.post(
        "/api/activities/ZZZZZZ/export/preview", json={}, headers=env.teacher.headers
    )
    assert gone.status_code == 410 and gone.json()["error"]["code"] == "ACTIVITY_GONE"
    missing = env.client.post("/api/activities/ZZZZZZ/export/preview", json={})
    assert missing.status_code == 404
    stale = post(env, "/writes", {"snapshotId": "9"})
    assert (
        stale.status_code == 409 and stale.json()["error"]["code"] == "STALE_SNAPSHOT"
    )
    empty = api_env(plan=())
    r = post(empty, "/preview")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NO_RESULTS"
    cancelled = api_env(stage="CANCELLED", plan=())
    r = post(cancelled, "/preview")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ACTIVITY_CANCELLED"
    assert "活動已取消" in r.json()["error"]["message"]
