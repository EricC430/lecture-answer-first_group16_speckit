"""T079：錯誤回應的安全性（SC-008、原則 V）。

觸發每一種 RejectionReason、404、400 INVALID_REQUEST，確認回應都有中文 message，
而且不含堆疊追蹤、檔案路徑、token 或憑證。500 的情況由 test_http_common 涵蓋。
"""

import re

from lecture_quiz.core.activity.results import RejectionReason
from tests.conftest import create_activity, join_group, seed_questions

LEAKS = ("Traceback", 'File "', ".py")
CJK = re.compile(r"[一-鿿]")


def _post(client, path, body=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(path, json=body if body is not None else {}, headers=headers)


def _check(response, secrets, code=None):
    assert response.status_code >= 400, response.text
    error = response.json()["error"]
    if code:
        assert error["code"] == code
    assert CJK.search(error["message"]), error
    for leak in (*LEAKS, *secrets):
        assert leak not in response.text, leak
    return error["code"]


def test_every_rejection_reason_is_safe(client):
    teacher = create_activity(client)
    base = f"/api/activities/{teacher.code}"
    device = join_group(client, teacher.code, 1)
    cred = client.get(f"{base}/snapshot", headers=teacher.headers).json()["groups"][0][
        "credential"
    ]
    secrets = (teacher.token, device, cred)
    seen = set()

    seen.add(_check(_post(client, f"{base}/rounds", token=device), secrets))
    seen.add(_check(_post(client, f"{base}/end", token=teacher.token), secrets))
    seen.add(_check(_post(client, f"{base}/rounds", token=teacher.token), secrets))
    seed_questions(client, teacher)
    seen.add(
        _check(
            _post(client, f"{base}/rounds", {"questionNumbers": []}, teacher.token),
            secrets,
        )
    )
    seen.add(
        _check(
            _post(client, f"{base}/rounds", {"countdownSeconds": 0}, teacher.token),
            secrets,
        )
    )
    seen.add(_check(_post(client, f"{base}/groups/join", {"groupNumber": 99}), secrets))
    seen.add(_check(_post(client, f"{base}/groups/join", {"groupNumber": 1}), secrets))
    seen.add(_check(_post(client, "/api/activities", {"maxGroups": 0}), secrets))
    seen.add(
        _check(
            _post(client, "/api/activities", {"maxGroups": 6}, teacher.token), secrets
        )
    )
    seen.add(
        _check(
            _post(client, f"{base}/groups/join", {"groupNumber": 2}, device), secrets
        )
    )
    seen.add(_check(_post(client, f"{base}/groups/leave"), secrets))
    seen.add(
        _check(client.delete(f"{base}/groups/4", headers=teacher.headers), secrets)
    )
    assert _post(client, f"{base}/rounds", token=teacher.token).status_code == 201
    seen.add(_check(_post(client, f"{base}/rounds", token=teacher.token), secrets))
    seen.add(_check(_post(client, f"{base}/groups/leave", token=device), secrets))
    service = client.app.state.activity_service
    client.portal.call(service.mark_group_submitted, teacher.code, 1)
    seen.add(
        _check(client.delete(f"{base}/groups/1", headers=teacher.headers), secrets)
    )
    gone = client.get(
        "/api/activities/ZZZZZZ/snapshot", headers={"Authorization": "Bearer x"}
    )
    seen.add(_check(gone, secrets))
    assert {r.value for r in RejectionReason} <= seen | {"STAGE_NOT_ALLOWED"}
    assert "STAGE_NOT_ALLOWED" in seen


def test_404_and_invalid_request_are_safe(client):
    teacher = create_activity(client)
    _check(client.get("/api/activities/ZZZZZZ/snapshot"), (), "ACTIVITY_NOT_FOUND")
    _check(client.get("/api/no-such-endpoint"), ())
    bad = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"fairMode": "yes"},
        headers=teacher.headers,
    )
    _check(bad, (teacher.token,), "INVALID_REQUEST")


def test_overlong_group_number_is_rejected_on_join_and_delete(client, teacher):
    """超長組號在加入（400）與刪除（依契約 #5 回 404）兩個端點都不得變成 500
    （PR #15 第三次審查問題 1）。"""
    for digits in (4301, 5000):
        join = client.post(
            f"/api/activities/{teacher.code}/groups/join",
            json={"groupNumber": "9" * digits},
        )
        assert join.status_code == 400, join.text
        assert join.json()["error"]["code"] == "INVALID_GROUP_NUMBER"
        delete = client.delete(
            f"/api/activities/{teacher.code}/groups/{'9' * digits}",
            headers=teacher.headers,
        )
        assert delete.status_code == 404, delete.text
        assert delete.json()["error"]["code"] == "GROUP_NOT_FOUND"
