"""001 為 003 新增的快照擴充機制（003 研究 R4）。"""

from lecture_quiz.app.activity.ports import GroupViewer, TeacherViewer
from lecture_quiz.core.activity.commands import Anonymous
from tests.conftest import create_joinable, join_group, service_of


def _snapshot(client, code, token):
    with client.websocket_connect(f"/ws/activities/{code}") as ws:
        ws.send_json({"type": "auth", "token": token})
        return ws.receive_json()


def test_without_extension_snapshot_is_unchanged(client):
    teacher = create_joinable(client)
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)
    activity = service.get(teacher.code)
    from lecture_quiz.core.activity.snapshot_view import SnapshotView

    assert service.snapshot_for(activity, requester) == SnapshotView.for_teacher(
        activity
    )


def test_extension_fields_are_merged_for_teacher_and_student(client):
    teacher = create_joinable(client)
    device = join_group(client, teacher.code, 3)
    service = service_of(client)
    seen = []

    def extension(activity, viewer):
        seen.append(viewer)
        if isinstance(viewer, TeacherViewer):
            return {"extTeacher": True}
        return {"extGroup": viewer.group_number}

    service.add_snapshot_extension(extension)
    teacher_snap = _snapshot(client, teacher.code, teacher.token)
    student_snap = _snapshot(client, teacher.code, device)
    assert teacher_snap["extTeacher"] is True
    assert student_snap["extGroup"] == 3
    assert "extTeacher" not in student_snap
    assert TeacherViewer() in seen and GroupViewer(3) in seen

    http = client.get(
        f"/api/activities/{teacher.code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()
    assert http["extGroup"] == 3


def test_extension_can_override_001_fields(client):
    teacher = create_joinable(client)
    device = join_group(client, teacher.code, 1)
    service = service_of(client)
    service.add_snapshot_extension(
        lambda activity, viewer: (
            {"ownGroup": None} if isinstance(viewer, GroupViewer) else {}
        )
    )
    assert _snapshot(client, teacher.code, device)["ownGroup"] is None


def test_invalid_identity_returns_none_without_calling_extension(client):
    teacher = create_joinable(client)
    service = service_of(client)
    calls = []
    service.add_snapshot_extension(lambda a, v: calls.append(v) or {})
    activity = service.get(teacher.code)
    assert service.snapshot_for(activity, Anonymous()) is None
    assert calls == []
