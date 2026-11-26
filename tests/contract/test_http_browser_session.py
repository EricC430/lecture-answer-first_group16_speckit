"""007 T005：`POST /api/browser-session` 的契約（contracts §1）。"""

from fastapi.testclient import TestClient

from lecture_quiz.app.activity.secrets_gen import is_browser_key

URL = "/api/browser-session"


def _set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


def test_issues_httponly_strict_cookie_without_body(client: TestClient):
    client.cookies.clear()
    response = client.post(URL)
    assert response.status_code == 204
    assert response.content == b""
    headers = _set_cookie_headers(response)
    assert len(headers) == 1
    header = headers[0]
    lowered = header.lower()
    assert header.startswith("lq_browser=")
    assert "httponly" in lowered
    assert "samesite=strict" in lowered
    assert "path=/" in lowered
    assert "max-age=86400" in lowered
    assert "secure" not in lowered
    assert "domain=" not in lowered
    assert is_browser_key(response.cookies["lq_browser"])


def test_existing_valid_cookie_is_kept_and_refreshed(client: TestClient):
    """已有金鑰：沿用同一把，並重新設定 1 天期限（審查第 1 點：滑動期限，
    避免第一次開頁滿 1 天後在上課中途失效）。"""
    client.cookies.clear()
    first = client.post(URL).cookies["lq_browser"]
    again = client.post(URL)
    assert again.status_code == 204
    headers = _set_cookie_headers(again)
    assert len(headers) == 1
    assert headers[0].startswith(f"lq_browser={first};")
    assert "max-age=86400" in headers[0].lower()
    assert client.cookies.get("lq_browser") == first


def test_malformed_cookie_is_replaced(client: TestClient):
    client.cookies.clear()
    client.cookies.set("lq_browser", "not-a-valid-key")
    response = client.post(URL)
    assert response.status_code == 204
    issued = response.cookies["lq_browser"]
    assert is_browser_key(issued)
    assert issued != "not-a-valid-key"


def test_repeated_calls_keep_same_key(client: TestClient):
    client.cookies.clear()
    client.post(URL)
    first = client.cookies.get("lq_browser")
    for _ in range(3):
        assert client.post(URL).status_code == 204
    assert client.cookies.get("lq_browser") == first
