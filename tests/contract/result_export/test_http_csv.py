"""X7：下載 CSV 的端點契約（US5）。"""

from tests.contract.result_export.conftest import url


def get(env, headers=None):
    return env.client.get(url(env, "/csv"), headers=headers or env.teacher.headers)


def test_download_headers_and_bom(api_env):
    """Scenario: US5-AS1：200、text/csv、attachment 檔名、no-store、UTF-8 BOM。"""
    env = api_env()
    response = get(env)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert response.headers["content-disposition"] == (
        f'attachment; filename="quiz-results-{env.code}.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith("\ufeff".encode())
    assert response.content.count(b"\r\n") == 12  # 表頭 1 列＋11 列（版面 A）


def test_header_only_when_no_data(api_env):
    """Scenario: US5-AS3：沒有資料時只含表頭一列。"""
    env = api_env(stage="JOINING", plan=())
    response = get(env)
    assert response.status_code == 200 and response.content.count(b"\r\n") == 1


def test_errors(api_env):
    """已取消 409、非老師 403。"""
    env = api_env()
    assert get(env, {"Authorization": "Bearer nobody"}).status_code == 403
    cancelled = api_env(stage="CANCELLED", plan=())
    r = get(cancelled)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ACTIVITY_CANCELLED"
