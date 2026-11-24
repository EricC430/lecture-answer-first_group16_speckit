"""建立 ExportService 時向 001 註冊快照擴充（共用基礎）。"""

from lecture_quiz.app.activity.ports import GroupViewer, TeacherViewer


def test_registers_one_extension_and_is_empty_without_attempts(make_env):
    env = make_env(stage="JOINING")
    activity_service = env.client.app.state.activity_service
    activity = activity_service.get(env.code)
    assert env.service.snapshot_extension(activity, TeacherViewer()) == {}
    assert env.service.snapshot_extension(activity, GroupViewer(1)) == {}
    teacher_snapshot = env.client.get(
        f"/api/activities/{env.code}/snapshot", headers=env.teacher.headers
    ).json()
    assert "export" not in teacher_snapshot
