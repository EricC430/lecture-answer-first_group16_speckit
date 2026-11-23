"""T024：建立活動與快照端點的契約（contracts/http-api.md #1、#2）。"""

import re

from lecture_quiz.app.activity.secrets_gen import CODE_ALPHABET
from tests.conftest import create_activity

LEAK_MARKERS = ("Traceback", 'File "', ".py")


def test_create_activity_returns_201_with_code_token_version(client):
    response = client.post("/api/activities", json={"maxGroups": 6})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"code", "teacherToken", "maxGroups", "version"}
    assert body["maxGroups"] == 6
    assert re.fullmatch(f"[{CODE_ALPHABET}]{{6}}", body["code"])
    assert len(body["teacherToken"]) >= 40
    assert body["version"] == 1


def test_create_activity_is_idempotent_with_same_key(client):
    headers = {"Idempotency-Key": "create-1"}
    body = {"maxGroups": 6}
    first = client.post("/api/activities", json=body, headers=headers).json()
    second = client.post("/api/activities", json=body, headers=headers).json()
    assert first == second


def test_unknown_code_without_token_is_404(client):
    response = client.get("/api/activities/ZZZZZZ/snapshot")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "ACTIVITY_NOT_FOUND"
    assert error["message"] == "找不到這個活動代碼，請確認後再輸入。"


def test_unknown_code_with_token_is_410_gone(client):
    response = client.get(
        "/api/activities/ZZZZZZ/snapshot", headers={"Authorization": "Bearer old-token"}
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "ACTIVITY_GONE"


def test_teacher_snapshot_contract(client):
    teacher = create_activity(client)
    response = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    )
    assert response.status_code == 200
    snap = response.json()
    assert snap["type"] == "snapshot"
    assert snap["role"] == "teacher"
    assert snap["code"] == teacher.code
    assert snap["stage"] == "PREPARING"
    assert snap["version"] == 1
    assert snap["groups"] == []
    assert snap["maxGroups"] == 6
    assert snap["questionNumbers"] == []


def test_lowercase_and_spaced_code_is_normalized(client):
    teacher = create_activity(client)
    response = client.get(
        f"/api/activities/%20{teacher.code.lower()}%20/snapshot",
        headers=teacher.headers,
    )
    assert response.status_code == 200


def test_error_responses_leak_nothing(client):
    teacher = create_activity(client)
    responses = [
        client.get("/api/activities/ZZZZZZ/snapshot"),
        client.get(f"/api/activities/{teacher.code}/snapshot"),
        client.post(f"/api/activities/{teacher.code}/cancel", json={}),
    ]
    for response in responses:
        assert response.status_code >= 400
        text = response.text
        for marker in LEAK_MARKERS:
            assert marker not in text
        assert teacher.token not in text


def test_create_activity_rejects_invalid_max_groups(client):
    """T090：maxGroups 不合法時回 400 INVALID_MAX_GROUPS，不產生活動。"""
    for raw in (0, 100, 2.5, "6", None, True):
        response = client.post("/api/activities", json={"maxGroups": raw})
        assert response.status_code == 400, raw
        error = response.json()["error"]
        assert error["code"] == "INVALID_MAX_GROUPS"
        assert error["message"] == "組數上限須為 1～99 的整數。"
    missing = client.post("/api/activities", json={})
    assert missing.json()["error"]["code"] == "INVALID_MAX_GROUPS"
    assert client.app.state.activity_service.registry.codes() == frozenset()
