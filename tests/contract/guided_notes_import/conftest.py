"""002 HTTP 契約測試的共用工具。"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TeacherSession, create_activity


@pytest.fixture
def teacher(import_client: TestClient) -> TeacherSession:
    """在注入 Fake Google 連接埠的 app 上建立活動，回傳老師身分。"""
    return create_activity(import_client)


def api(code: str, path: str = "") -> str:
    return f"/api/activities/{code}/import{path}"
