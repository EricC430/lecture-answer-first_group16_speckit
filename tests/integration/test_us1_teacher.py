"""T025：US1 老師建立活動並獨占控制權。"""

import re

from fastapi.testclient import TestClient

from lecture_quiz.app.activity.secrets_gen import CODE_ALPHABET
from tests.conftest import call, create_activity, join_group, service_of

TEACHER_ONLY_REQUESTS = [
    ("post", "/rounds", {}),
    ("post", "/rounds/current/close", {}),
    ("post", "/rounds/current/finalize", {}),
    ("post", "/end", {}),
    ("post", "/cancel", {}),
]
NOT_TEACHER_MESSAGE = "需要這個活動的老師身分才能操作。"


def _version(client, teacher):
    return client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()["version"]


def test_second_activity_gets_distinct_valid_code(client):
    """Scenario: US1-AS1

    已有一個活動時再建立一個，兩個代碼都是 6 碼、字元都在字元集內、互不相同，
    都在準備中。
    """
    first = create_activity(client)
    second = create_activity(client)
    for teacher in (first, second):
        assert re.fullmatch(f"[{CODE_ALPHABET}]{{6}}", teacher.code)
        snap = client.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        ).json()
        assert snap["stage"] == "PREPARING"
        assert snap["roundNumber"] is None
        assert snap["questionNumbers"] == []
    assert first.code != second.code


def test_same_token_in_new_client_keeps_teacher_identity(client):
    """Scenario: US1-AS2

    用同一個 token 建立新的 client（模擬重新整理或同瀏覽器新分頁），
    仍可取得老師快照並操作。
    """
    teacher = create_activity(client)
    other_tab = TestClient(client.app)
    snap = other_tab.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    )
    assert snap.status_code == 200
    assert snap.json()["role"] == "teacher"
    # 通過老師權限檢查：得到的是階段錯誤（準備中只能取消），而不是 403
    end = other_tab.post(
        f"/api/activities/{teacher.code}/end", json={}, headers=teacher.headers
    )
    assert end.status_code == 409
    assert end.json()["error"]["message"] == "準備中只能取消活動。"


def test_client_without_token_is_rejected(client):
    """Scenario: US1-AS3

    另一個瀏覽器（沒有 token）的老師專用操作一律 403 NOT_TEACHER。
    """
    teacher = create_activity(client)
    other_browser = TestClient(client.app)
    for method, path, body in TEACHER_ONLY_REQUESTS:
        response = getattr(other_browser, method)(
            f"/api/activities/{teacher.code}{path}", json=body
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "NOT_TEACHER"
    assert _version(client, teacher) == 1


def test_student_device_token_is_rejected(client):
    """Scenario: US1-AS4

    學生裝置 token 送出老師專用請求 → 403，狀態不變，回應不含任何 token。
    """
    teacher = create_activity(client)
    device_token = join_group(client, teacher.code, "第一組")
    version_before = _version(client, teacher)
    for method, path, body in TEACHER_ONLY_REQUESTS:
        response = getattr(client, method)(
            f"/api/activities/{teacher.code}{path}",
            json=body,
            headers={"Authorization": f"Bearer {device_token}"},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "NOT_TEACHER"
        assert teacher.token not in response.text
        assert device_token not in response.text
    assert _version(client, teacher) == version_before


def test_other_activity_teacher_is_rejected(client):
    """Scenario: US1-AS5

    活動 B 的老師 token 操作活動 A → 403，A 的 version 不變。
    """
    a = create_activity(client)
    b = create_activity(client)
    for method, path, body in TEACHER_ONLY_REQUESTS:
        response = getattr(client, method)(
            f"/api/activities/{a.code}{path}", json=body, headers=b.headers
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "NOT_TEACHER"
    assert _version(client, a) == 1
    # 服務層的 ActivityGateway 也以活動區分老師
    service = service_of(client)
    assert service.is_teacher(a.code, service.resolve_requester(a.code, a.token))
    assert not service.is_teacher(a.code, service.resolve_requester(a.code, b.token))


def test_code_only_request_gets_teacher_required_message(client):
    """Scenario: US1-AS6

    只帶活動代碼、不帶 token → 403，訊息為「需要這個活動的老師身分才能操作。」，
    不洩漏老師資料。
    """
    teacher = create_activity(client)
    response = client.post(f"/api/activities/{teacher.code}/rounds", json={})
    assert response.status_code == 403
    assert response.json()["error"]["message"] == NOT_TEACHER_MESSAGE
    snapshot = client.get(f"/api/activities/{teacher.code}/snapshot")
    assert snapshot.status_code == 403
    assert "groups" not in snapshot.text


def test_concurrent_create_with_same_key_creates_one_activity(client):
    """同一個 key 並行建立只產生一個活動（FR-033、PR #15 審查第 2 項）。"""
    import asyncio

    service = service_of(client)

    async def both():
        return await asyncio.gather(
            service.create("same-key"), service.create("same-key")
        )

    first, second = call(client, both)
    assert first == second
    assert len(service.registry.codes()) == 1
