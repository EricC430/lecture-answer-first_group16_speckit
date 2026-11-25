"""X3、X4、X5 的端點契約（US4）。"""

from lecture_quiz.app.result_export.models import AttemptReason
from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.result_export.models import OutcomeStatus
from tests.contract.result_export.conftest import url

PENDING = WriteResult(OutcomeStatus.PENDING, AttemptReason.UNKNOWN)


def post(env, path, body=None, headers=None):
    return env.client.post(
        url(env, path),
        json=body if body is not None else {},
        headers=headers or env.teacher.headers,
    )


def confirmed(env):
    sid = post(env, "/preview").json()["snapshotId"]
    return post(env, "/writes", {"snapshotId": sid}).json()


def test_latest_is_null_then_attempt(api_env):
    """X5：沒有嘗試時 {"attempt": null}；有嘗試時回完整 Attempt。"""
    env = api_env()
    empty = env.client.get(url(env, "/writes/latest"), headers=env.teacher.headers)
    assert empty.status_code == 200 and empty.json() == {"attempt": None}
    confirmed(env)
    latest = env.client.get(
        url(env, "/writes/latest"), headers=env.teacher.headers
    ).json()
    assert (
        latest["attempt"]["status"] == "SUCCESS" and latest["attempt"]["attemptId"] == 1
    )


def test_recheck_has_cell_checks_other_responses_do_not(api_env):
    """Scenario: US4-AS2：cellChecks 只在核對回應有值。"""
    env = api_env()
    env.writer.next_result = PENDING
    env.writer.apply_on_pending = True
    first = confirmed(env)
    assert first["status"] == "PENDING" and first["cellChecks"] == []
    assert first["reason"] == "UNKNOWN" and first["reasonText"]
    response = post(env, f"/writes/{first['attemptId']}/recheck")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS" and len(body["cellChecks"]) == body["totalCells"]
    assert set(body["cellChecks"][0]) == {
        "questionNumber",
        "subIndex",
        "expected",
        "currentDisplay",
        "matches",
    }


def test_retry_returns_new_attempt_and_failures_are_200(api_env):
    """X4：回新的嘗試（kind=RETRY）；授權、結構等失敗回 200＋FAILED 而非 4xx。"""
    from lecture_quiz.app.guided_notes_import.models import ImportRejection

    env = api_env()
    first = confirmed(env)
    retried = post(env, f"/writes/{first['attemptId']}/retry")
    assert retried.status_code == 200 and retried.json()["kind"] == "RETRY"
    env.reader.read_failure = ImportRejection.AUTH_EXPIRED
    again = post(env, f"/writes/{retried.json()['attemptId']}/retry")
    assert again.status_code == 200
    assert (
        again.json()["status"] == "FAILED" and again.json()["reason"] == "AUTH_EXPIRED"
    )


def test_error_codes(api_env):
    """NOT_LATEST_ATTEMPT／ATTEMPT_NOT_FOUND／NOT_TEACHER／INVALID_REQUEST。"""
    env = api_env()
    first = confirmed(env)
    post(env, f"/writes/{first['attemptId']}/retry")
    r = post(env, f"/writes/{first['attemptId']}/retry")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_LATEST_ATTEMPT"
    r = post(env, "/writes/99/recheck")
    assert r.status_code == 404 and r.json()["error"]["code"] == "ATTEMPT_NOT_FOUND"
    r = post(env, "/writes/1/recheck", headers={"Authorization": "Bearer nobody"})
    assert r.status_code == 403
    r = post(env, "/writes/0/recheck")
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_REQUEST"
    r = env.client.get(
        url(env, "/writes/latest"), headers={"Authorization": "Bearer nobody"}
    )
    assert r.status_code == 403
