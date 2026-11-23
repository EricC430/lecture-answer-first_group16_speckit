"""共用 HTTP 基礎的契約測試（contracts/http-api.md「共通規則」「日誌」）。"""

import logging
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from lecture_quiz.adapters.web.common import (
    ApiError,
    annotate_request_log,
    bearer_token,
    idempotency_key,
)
from tests.conftest import make_app

SECRET = "super-secret-token-value"


class JoinBody(BaseModel):
    name: str
    credential: str | None = None


def _app_with_probe_routes():
    app = make_app()
    router = APIRouter(prefix="/api/probe")

    @router.post("/activities/{code}/join")
    async def join(
        code: str,
        body: JoinBody,
        token: Annotated[str | None, Depends(bearer_token)],
        key: Annotated[str | None, Depends(idempotency_key)],
    ):
        return {"code": code, "token": token, "key": key, "name": body.name}

    @router.post("/activities/{code}/annotated")
    async def annotated(code: str, request: Request):
        annotate_request_log(request, result="OK", version=7)
        return {"version": 7}

    @router.get("/business-error")
    async def business_error():
        raise ApiError(403, "NOT_TEACHER", "需要這個活動的老師身分才能操作。")

    @router.get("/crash")
    async def crash():
        raise RuntimeError(f"boom {SECRET} C:/secret/path.py")

    app.include_router(router)
    # /api fallback 與掛在 "/" 的靜態檔必須最後匹配，把它們移回路由表最後
    routes = app.router.routes
    tail = [
        r
        for r in routes
        if getattr(r, "name", "") == "static"
        or getattr(r, "path", "") == "/api/{rest:path}"
    ]
    for route in tail:
        routes.remove(route)
    routes.extend(sorted(tail, key=lambda r: getattr(r, "name", "") == "static"))
    return app


@pytest.fixture
def probe_client():
    with TestClient(_app_with_probe_routes(), raise_server_exceptions=False) as c:
        yield c


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "time": "2026-11-21T09:00:00+08:00"}


def test_unknown_api_path_uses_error_envelope(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "找不到這個路徑。"}
    }


def test_validation_error_is_invalid_request_naming_field(probe_client):
    response = probe_client.post(
        "/api/probe/activities/ABC123/join", json={"credential": 1}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert "name" in error["message"]
    assert "credential" in error["message"]


def test_api_error_is_converted(probe_client):
    response = probe_client.get("/api/probe/business-error")
    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "NOT_TEACHER", "message": "需要這個活動的老師身分才能操作。"}
    }


def test_unexpected_error_hides_details(probe_client):
    response = probe_client.get("/api/probe/crash")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    text = response.text
    for leaked in ("Traceback", SECRET, "secret/path", ".py", "RuntimeError"):
        assert leaked not in text


def test_bearer_and_idempotency_key_are_parsed(probe_client):
    response = probe_client.post(
        "/api/probe/activities/ABC123/join",
        json={"name": "第一組"},
        headers={"Authorization": f"Bearer {SECRET}", "Idempotency-Key": "k-1"},
    )
    assert response.status_code == 200
    assert response.json()["token"] == SECRET
    assert response.json()["key"] == "k-1"


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "Bearer"])
def test_missing_or_malformed_bearer_is_anonymous(header):
    assert bearer_token(header) is None


def test_too_long_idempotency_key_is_rejected(probe_client):
    response = probe_client.post(
        "/api/probe/activities/ABC123/join",
        json={"name": "x"},
        headers={"Idempotency-Key": "k" * 129},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_request_log_uses_whitelist_only(probe_client, caplog):
    caplog.set_level(logging.INFO, logger="lecture_quiz.request")
    probe_client.post(
        "/api/probe/activities/K7QH2M/join?token=" + SECRET,
        json={"name": "第一組", "credential": SECRET},
        headers={"Authorization": f"Bearer {SECRET}", "Idempotency-Key": "k-2"},
    )
    lines = [r.getMessage() for r in caplog.records if r.name == "lecture_quiz.request"]
    assert len(lines) == 1
    line = lines[0]
    assert "method=POST" in line
    assert "path=/api/probe/activities/{code}/join" in line
    assert "activity=K7QH2M" in line
    assert "result=OK" in line
    assert "status=200" in line
    assert "elapsed_ms=" in line
    assert SECRET not in line
    assert "第一組" not in line


def test_request_log_records_annotation_and_errors(probe_client, caplog):
    caplog.set_level(logging.INFO, logger="lecture_quiz.request")
    probe_client.post("/api/probe/activities/K7QH2M/annotated")
    probe_client.get("/api/probe/business-error")
    probe_client.get("/api/probe/crash")
    lines = [r.getMessage() for r in caplog.records if r.name == "lecture_quiz.request"]
    assert "version=7" in lines[0]
    assert "result=NOT_TEACHER" in lines[1] and "status=403" in lines[1]
    assert "status=500" in lines[2]
    assert all(SECRET not in line for line in lines)


def test_request_log_path_template_for_nested_and_static(client, caplog):
    caplog.set_level(logging.INFO, logger="lecture_quiz.request")
    client.get("/api/health")
    client.get("/js/api.js")
    client.get("/api/no-such-path/" + SECRET)
    lines = [r.getMessage() for r in caplog.records if r.name == "lecture_quiz.request"]
    assert "path=/api/health " in lines[0]
    assert "path=<static> " in lines[1]
    # 未知的 /api 路徑由 fallback 路由回 404，只記樣板，不記原始網址
    assert "path=/api/{rest} " in lines[2] and "status=404" in lines[2]
    assert all(SECRET not in line for line in lines)


@pytest.mark.parametrize(
    "raw_code",
    [
        "K7QH2M%0AINFO%20lecture_quiz.request%20method=POST%20activity=FORGED",
        "K7QH2M%0D%0Aforged",
        "A" * 3000,
        "k7qh2m",
        "K7QH2M%20",
    ],
)
def test_request_log_rejects_untrusted_activity_code(probe_client, caplog, raw_code):
    """Scenario: 日誌偽造（PR #14 審查第 1 項）。

    不符合活動代碼格式的路徑參數不得寫入日誌，日誌恰好一行。
    """
    caplog.set_level(logging.INFO, logger="lecture_quiz.request")
    probe_client.post(f"/api/probe/activities/{raw_code}/annotated")
    records = [r for r in caplog.records if r.name == "lecture_quiz.request"]
    assert len(records) == 1
    line = records[0].getMessage()
    assert "\n" not in line and "\r" not in line
    assert "activity=<invalid>" in line
    assert "FORGED" not in line and "forged" not in line
    assert "A" * 50 not in line


def test_annotate_request_log_also_validates_activity_code(probe_client, caplog):
    caplog.set_level(logging.INFO, logger="lecture_quiz.request")
    app = probe_client.app
    router = APIRouter()

    @router.get("/api/probe/forge")
    async def forge(request: Request):
        annotate_request_log(request, activity_code="X\nINFO forged", result="A\nB")
        return {}

    app.router.routes.insert(0, router.routes[0])
    probe_client.get("/api/probe/forge")
    line = [r.getMessage() for r in caplog.records if r.name == "lecture_quiz.request"][
        0
    ]
    assert "\n" not in line
    assert "activity=<invalid>" in line
    assert "result=<invalid>" in line


def test_unknown_api_post_is_404_not_405(client):
    response = client.post("/api/does-not-exist", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
