"""X6：重新授權入口（US2-AS5）。"""

import pytest

from tests.contract.result_export.conftest import url


def start(env, headers=None):
    return env.client.post(
        url(env, "/authorization"), json={}, headers=headers or env.teacher.headers
    )


@pytest.mark.parametrize("stage", ["PREPARING", "ROUND_OPEN", "RESULT_FINAL", "ENDED"])
def test_returns_auth_url(api_env, stage):
    """Scenario: US2-AS5：任何非取消階段回 200 與 authUrl。"""
    env = api_env(stage=stage, plan=())
    response = start(env)
    assert response.status_code == 200 and set(response.json()) == {"authUrl"}


def test_errors(api_env):
    """非老師 403、已取消 409、未設定 503。"""
    env = api_env()
    assert start(env, {"Authorization": "Bearer nobody"}).status_code == 403
    env.auth.configured = False
    r = start(env)
    assert r.status_code == 503
    assert "變數" not in r.json()["error"]["message"]
    cancelled = api_env(stage="CANCELLED", plan=())
    r = start(cancelled)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ACTIVITY_CANCELLED"


def test_callback_route_is_002s_and_no_new_callback(api_env):
    """授權完成後沿用 002 的回呼；005 沒有新增回呼端點。"""
    env = api_env()
    response = env.client.get(
        "/api/oauth/callback?state=x&code=y", follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"].startswith("/teacher.html?")
    assert "auth=" in response.headers["location"]
    assert env.client.get("/api/activities/X/export/callback").status_code == 404
