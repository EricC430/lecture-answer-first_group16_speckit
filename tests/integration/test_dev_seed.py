"""T050：開發用 seed API（研究 R8；002 合併後移除）。"""

from fastapi.testclient import TestClient

from tests.conftest import (
    FakeClock,
    ManualScheduler,
    create_activity,
    join_group,
    make_app,
)


def test_seed_endpoint_absent_by_default(client, teacher):
    response = client.post(
        f"/api/dev/activities/{teacher.code}/seed-questions",
        json={"count": 4},
        headers=teacher.headers,
    )
    assert response.status_code == 404
    assert client.get("/api/dev/status").status_code == 404


def test_seed_endpoint_enabled_teacher_only():
    with TestClient(make_app(FakeClock(), ManualScheduler(), dev_seed=True)) as client:
        assert client.get("/api/dev/status").json() == {"enabled": True}
        teacher = create_activity(client)
        # 開放加入前學生不能加入；先以 seed API 放入題目並開放加入
        ok = client.post(
            f"/api/dev/activities/{teacher.code}/seed-questions",
            json={"count": 4},
            headers=teacher.headers,
        )
        assert ok.status_code == 200
        opened = client.post(
            f"/api/activities/{teacher.code}/open-joining",
            json={},
            headers=teacher.headers,
        )
        assert opened.status_code == 200
        device = join_group(client, teacher.code, 1)
        student = client.post(
            f"/api/dev/activities/{teacher.code}/seed-questions",
            json={"count": 4},
            headers={"Authorization": f"Bearer {device}"},
        )
        assert student.status_code == 403
        ok = client.post(
            f"/api/dev/activities/{teacher.code}/seed-questions",
            json={"count": 4},
            headers=teacher.headers,
        )
        assert ok.status_code == 200
        snap = client.get(
            f"/api/activities/{teacher.code}/snapshot", headers=teacher.headers
        ).json()
        assert snap["questionNumbers"] == [1, 2, 3, 4]
        assert ok.json() == {"version": snap["version"]}
        bad = client.post(
            f"/api/dev/activities/{teacher.code}/seed-questions",
            json={"count": 0},
            headers=teacher.headers,
        )
        assert bad.status_code == 400


def _seed(client, teacher, body):
    return client.post(
        f"/api/dev/activities/{teacher.code}/seed-questions",
        json=body,
        headers=teacher.headers,
    )


def test_seed_blanks_sets_question_shapes():
    """003 研究 R6：seed 的 blanks 指定每題格數；沒給時每題 1 格。"""
    with TestClient(make_app(FakeClock(), ManualScheduler(), dev_seed=True)) as client:
        shapes = client.app.state.question_shape_source
        teacher = create_activity(client)
        assert shapes.blanks_per_question(teacher.code) is None
        assert _seed(client, teacher, {"count": 4}).status_code == 200
        assert dict(shapes.blanks_per_question(teacher.code)) == {
            1: 1,
            2: 1,
            3: 1,
            4: 1,
        }
        body = {"count": 4, "blanks": [2, 2, 1, 1]}
        assert _seed(client, teacher, body).status_code == 200
        assert dict(shapes.blanks_per_question(teacher.code)) == {
            1: 2,
            2: 2,
            3: 1,
            4: 1,
        }


def test_seed_blanks_validation():
    """blanks 長度不等於 count、或任一格數不在 1～10：400，格數不變。"""
    with TestClient(make_app(FakeClock(), ManualScheduler(), dev_seed=True)) as client:
        shapes = client.app.state.question_shape_source
        teacher = create_activity(client)
        assert _seed(client, teacher, {"count": 2, "blanks": [1, 3]}).status_code == 200
        for blanks in ([1], [1, 2, 3], [0, 1], [1, 11], ["2", 1], [True, 1]):
            response = _seed(client, teacher, {"count": 2, "blanks": blanks})
            assert response.status_code == 400, blanks
            assert response.json()["error"]["code"] == "INVALID_REQUEST"
        assert dict(shapes.blanks_per_question(teacher.code)) == {1: 1, 2: 3}
