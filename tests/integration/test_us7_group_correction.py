"""T072：US7 離開本組與刪除空組（HTTP 加 WebSocket）。"""

import asyncio

from tests.conftest import (
    call,
    create_joinable,
    service_of,
)


def _join(client, code, number, credential=None):
    body = {"groupNumber": number, "credential": credential}
    return client.post(f"/api/activities/{code}/groups/join", json=body).json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _groups(client, teacher):
    snap = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
    ).json()
    return {g["number"]: g for g in snap["groups"]}


def _open_round(client, teacher):
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201


def test_leave_notifies_device_and_keeps_group(client):
    """Scenario: US7-AS1

    裝置離開本組：該裝置的 WebSocket 收到 unauthorized（LEFT_GROUP）；
    組別與其他裝置不變。
    """
    teacher = create_joinable(client)
    x = _join(client, teacher.code, 1)
    _join(client, teacher.code, 1, x["credential"])
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": x["deviceToken"]})
        ws.receive_json()
        response = client.post(
            f"/api/activities/{teacher.code}/groups/leave",
            json={},
            headers=_auth(x["deviceToken"]),
        )
        assert response.status_code == 200
        assert ws.receive_json() == {"type": "unauthorized", "reason": "LEFT_GROUP"}
    group = _groups(client, teacher)[1]
    assert group["deviceCount"] == 1
    assert group["credential"] == x["credential"]


def test_after_leave_device_joins_correct_group(client):
    """Scenario: US7-AS2

    離開後以組號 2 與第 2 組的憑證加入，取得第 2 組身分。
    """
    teacher = create_joinable(client)
    x = _join(client, teacher.code, 1)
    y = _join(client, teacher.code, 2)
    client.post(
        f"/api/activities/{teacher.code}/groups/leave",
        json={},
        headers=_auth(x["deviceToken"]),
    )
    moved = _join(client, teacher.code, 2, y["credential"])
    snap = client.get(
        f"/api/activities/{teacher.code}/snapshot", headers=_auth(moved["deviceToken"])
    ).json()
    assert snap["ownGroup"]["number"] == 2


def test_leave_rejected_during_round(client):
    """Scenario: US7-AS3

    搶答中離開回 409，訊息說明搶答中不能換組，身分不變。
    """
    teacher = create_joinable(client)
    x = _join(client, teacher.code, 1)
    _open_round(client, teacher)
    response = client.post(
        f"/api/activities/{teacher.code}/groups/leave",
        json={},
        headers=_auth(x["deviceToken"]),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_GROUP_SWITCH_DURING_ROUND"
    assert "搶答進行中不能換組" in response.json()["error"]["message"]
    assert _groups(client, teacher)[1]["deviceCount"] == 1


def test_submissions_remain_with_original_group(client):
    """Scenario: US7-AS4

    裝置替第 1 組送出後離開並加入第 2 組，第 1 組仍有提交紀錄。
    """
    teacher = create_joinable(client)
    x = _join(client, teacher.code, 1)
    y = _join(client, teacher.code, 2)
    _open_round(client, teacher)
    service = service_of(client)
    assert call(client, service.mark_group_submitted, teacher.code, 1).ok
    client.post(
        f"/api/activities/{teacher.code}/rounds/current/close",
        json={},
        headers=teacher.headers,
    )
    client.post(
        f"/api/activities/{teacher.code}/groups/leave",
        json={},
        headers=_auth(x["deviceToken"]),
    )
    _join(client, teacher.code, 2, y["credential"])
    groups = _groups(client, teacher)
    assert groups[1]["hasSubmissions"] is True
    assert groups[2]["hasSubmissions"] is False


def test_delete_group_with_devices_notifies_devices(client):
    """Scenario: US7-AS5

    開放加入階段刪除從未提交的組別，即使還有裝置：原組裝置收到 unauthorized
    （GROUP_DELETED），組別從看板消失；組號可再使用並取得新憑證，舊憑證失效。
    """
    teacher = create_joinable(client)
    wrong = _join(client, teacher.code, 5)
    with client.websocket_connect(f"/ws/activities/{teacher.code}") as ws:
        ws.send_json({"type": "auth", "token": wrong["deviceToken"]})
        ws.receive_json()
        response = client.delete(
            f"/api/activities/{teacher.code}/groups/5", headers=teacher.headers
        )
        assert response.status_code == 200
        assert ws.receive_json() == {"type": "unauthorized", "reason": "GROUP_DELETED"}
    assert 5 not in _groups(client, teacher)
    again = _join(client, teacher.code, 5)
    assert again["credential"] != wrong["credential"]
    stale = _join(client, teacher.code, 5, wrong["credential"])
    assert stale["error"]["code"] == "BAD_CREDENTIAL"


def test_delete_group_with_submissions_rejected(client):
    """Scenario: US7-AS6

    有提交紀錄的組不能刪除，回 409，資料不變。
    """
    teacher = create_joinable(client)
    _join(client, teacher.code, 1)
    _open_round(client, teacher)
    call(client, service_of(client).mark_group_submitted, teacher.code, 1)
    client.post(
        f"/api/activities/{teacher.code}/rounds/current/close",
        json={},
        headers=teacher.headers,
    )
    before = _groups(client, teacher)
    response = client.delete(
        f"/api/activities/{teacher.code}/groups/1", headers=teacher.headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["message"] == "此組已有作答紀錄，不能刪除。"
    assert _groups(client, teacher) == before


def test_delete_group_is_rejected_during_round(client):
    """Scenario: US7-AS7

    搶答中禁止刪除組別（即使從未提交），回 409，組別與裝置不變。
    """
    teacher = create_joinable(client)
    _join(client, teacher.code, 1)
    _open_round(client, teacher)
    before = _groups(client, teacher)
    response = client.delete(
        f"/api/activities/{teacher.code}/groups/1", headers=teacher.headers
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "GROUP_DELETE_DURING_ROUND"
    assert "搶答進行中不能刪除組別" in error["message"]
    assert _groups(client, teacher) == before


def test_delete_and_mark_submitted_never_orphan_an_answer(client):
    """搶答中不能刪除組別，所以「答案已記錄但組別被刪除」不可能發生。

    刪除與提交標記同時送出 20 次：刪除一律被拒，標記一律成功，組別與提交紀錄都在。
    """
    teacher = create_joinable(client)
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)
    _join(client, teacher.code, 1)
    _open_round(client, teacher)

    async def race():
        return await asyncio.gather(
            service.delete_group(teacher.code, requester, 1),
            service.mark_group_submitted(teacher.code, 1),
        )

    for _ in range(20):
        deleted, marked = call(client, race)
        assert not deleted.ok and marked.ok
    group = service.get(teacher.code).groups[1]
    assert group.has_submissions
