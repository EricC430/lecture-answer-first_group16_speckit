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
