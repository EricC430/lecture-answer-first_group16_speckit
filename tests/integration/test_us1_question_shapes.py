"""US1：快照中的每題格數（學生作答表單依此畫出格子）。"""

from tests.conftest import create_activity, join_group, seed_questions


def _ws(client, code, token):
    with client.websocket_connect(f"/ws/activities/{code}") as ws:
        ws.send_json({"type": "auth", "token": token})
        return ws.receive_json()


def test_question_shapes_in_snapshots(client):
    """Scenario: US1-AS1（學生看到本輪開放題的格數；老師看到全部題的格數）。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    device = join_group(client, teacher.code, 1)
    assert _ws(client, teacher.code, device)["questionShapes"] == {}
    response = client.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": [1, 3]},
        headers=teacher.headers,
    )
    assert response.status_code == 201
    assert _ws(client, teacher.code, device)["questionShapes"] == {"1": 2, "3": 1}
    assert _ws(client, teacher.code, teacher.token)["questionShapes"] == {
        "1": 2,
        "2": 2,
        "3": 1,
        "4": 1,
    }
