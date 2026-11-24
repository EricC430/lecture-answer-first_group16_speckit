"""005 錯誤回應的安全性（FR-031；憲章原則 V）：中文訊息、不含堆疊／路徑／憑證。"""

import re

from lecture_quiz.app.guided_notes_import.models import ImportRejection
from tests.contract.result_export.conftest import url

LEAKS = ("Traceback", 'File "', ".py", "Bearer", "client_secret", "refresh_token")
CJK = re.compile(r"[一-鿿]")


def check(response, secrets=()):
    assert response.status_code >= 400, response.text
    error = response.json()["error"]
    assert CJK.search(error["message"]), error
    for leak in (*LEAKS, *secrets):
        assert leak not in response.text, leak
    return error["code"]


def test_every_http_error_is_safe(api_env):
    """每一種可由 HTTP 觸發的 ExportRejection 都有中文訊息且不含內部細節。"""
    env = api_env()
    secrets = (env.teacher.token,)
    h = env.teacher.headers
    outsider = {"Authorization": "Bearer nobody"}
    seen = set()

    def call(method, path, body=None, headers=None, base=None):
        target = base or url(env, path)
        if method == "GET":
            return env.client.get(target, headers=headers or h)
        return env.client.post(
            target, json=body if body is not None else {}, headers=headers or h
        )

    seen.add(check(call("POST", "/preview", headers=outsider), secrets))
    seen.add(check(call("POST", "/writes", {}), secrets))  # INVALID_REQUEST
    seen.add(check(call("POST", "/writes", {"snapshotId": "9"}), secrets))  # STALE
    seen.add(check(call("POST", "/writes/9/recheck"), secrets))  # ATTEMPT_NOT_FOUND
    first = call("POST", "/writes", {"snapshotId": "1.2"}).json()
    call("POST", f"/writes/{first['attemptId']}/retry")
    seen.add(check(call("POST", f"/writes/{first['attemptId']}/retry"), secrets))
    gone = env.client.post("/api/activities/ZZZZZZ/export/preview", json={}, headers=h)
    seen.add(check(gone, secrets))
    seen.add(
        check(
            call(
                "POST",
                "/preview",
                base="/api/activities/ZZZZZZ/export/preview",
                headers={"X-Anonymous": "1"},
            ),
            secrets,
        )
    )
    empty = api_env(plan=())
    seen.add(
        check(
            empty.client.post(
                url(empty, "/preview"), json={}, headers=empty.teacher.headers
            ),
            secrets,
        )
    )
    cancelled = api_env(stage="CANCELLED", plan=())
    seen.add(
        check(
            cancelled.client.get(
                url(cancelled, "/csv"), headers=cancelled.teacher.headers
            ),
            secrets,
        )
    )
    env.reader.read_failure = ImportRejection.AUTH_EXPIRED
    seen.add(check(call("POST", "/preview"), secrets))
    env.reader.read_failure = ImportRejection.PERMISSION_DENIED
    seen.add(check(call("POST", "/preview"), secrets))
    env.reader.read_failure = ImportRejection.READ_FAILED
    seen.add(check(call("POST", "/preview"), secrets))
    env.auth.configured = False
    seen.add(check(call("POST", "/authorization"), secrets))
    expected = {
        "NOT_TEACHER",
        "INVALID_REQUEST",
        "STALE_SNAPSHOT",
        "ATTEMPT_NOT_FOUND",
        "NOT_LATEST_ATTEMPT",
        "ACTIVITY_GONE",
        "ACTIVITY_NOT_FOUND",
        "NO_RESULTS",
        "ACTIVITY_CANCELLED",
        "AUTH_EXPIRED",
        "PERMISSION_DENIED",
        "READ_FAILED",
        "GOOGLE_NOT_CONFIGURED",
    }
    assert expected <= seen, expected - seen
