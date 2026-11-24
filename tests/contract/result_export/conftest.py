"""005 HTTP 契約測試：用 `make_env` 的服務（真閘門、假資料與假 Google）接上 app。"""

import pytest

from tests.unit.app.result_export.conftest import make_env  # noqa: F401


@pytest.fixture
def api_env(make_env):  # noqa: F811
    """回傳已把 `ExportService` 接到 app 的環境。"""

    def factory(**kwargs):
        env = make_env(**kwargs)
        env.client.app.state.export_service = env.service
        return env

    return factory


def url(env, path: str) -> str:
    """005 端點網址。"""
    return f"/api/activities/{env.code}/export{path}"
