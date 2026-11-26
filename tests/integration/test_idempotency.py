"""T078：重送去重（SC-004、FR-033）。"""

from tests.conftest import TeacherSession, new_browser, open_joining, service_of


def test_create_join_and_open_round_replayed_20_times(client):
    """建立活動、加入組別、開輪各以相同 Idempotency-Key 重送 20 次，不產生重複。"""
    headers = {"Idempotency-Key": "create-k"}
    created = [
        client.post("/api/activities", json={"maxGroups": 6}, headers=headers).json()
        for _ in range(20)
    ]
    assert all(c == created[0] for c in created)
    assert len(service_of(client).registry.codes()) == 1
    code = created[0]["code"]
    open_joining(client, TeacherSession(code, created[0]["teacherToken"]))

    browser_key = new_browser(client)  # 同一個瀏覽器重送 20 次（007：金鑰須先存在）
    joins = [
        client.post(
            f"/api/activities/{code}/groups/join",
            json={"groupNumber": 1},
            headers={
                "Idempotency-Key": "join-k",
                "Authorization": f"Bearer {browser_key}",
            },
        ).json()
        for _ in range(20)
    ]
    assert all(j == joins[0] for j in joins)
    activity = service_of(client).get(code)
    assert len(activity.groups) == 1
    assert len(activity.devices) == 1

    teacher_headers = {
        "Authorization": f"Bearer {created[0]['teacherToken']}",
        "Idempotency-Key": "open-k",
    }
    service = service_of(client)
    opens = [
        client.post(f"/api/activities/{code}/rounds", json={}, headers=teacher_headers)
        for _ in range(20)
    ]
    assert {r.status_code for r in opens} == {201}
    assert all(r.json() == opens[0].json() for r in opens)
    assert len(service.get(code).rounds) == 1
