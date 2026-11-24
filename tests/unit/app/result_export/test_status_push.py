"""寫回狀態推送與快照擴充（US4；FR-021）。"""

from lecture_quiz.app.activity.ports import GroupViewer, TeacherViewer
from tests.conftest import join_group


def confirm(env):
    sid = env.run(
        env.service.preview, env.code, env.requester()
    ).value.snapshot.snapshot_id
    return env.run(env.service.confirm_write, env.code, env.requester(), sid).value


def test_published_when_attempt_starts_and_ends(make_env):
    """每次嘗試進入進行中與結束各推送一次。"""
    env = make_env()
    confirm(env)
    assert env.publisher.published == [env.code, env.code]


def test_teacher_summary_has_no_answers_and_students_have_nothing(make_env):
    """老師快照有摘要（不含答案、原內容、差異清單）；學生永遠沒有。"""
    env = make_env(stage="JOINING")
    attempt = confirm(env)
    activity = env.client.app.state.activity_service.get(env.code)
    teacher = env.service.snapshot_extension(activity, TeacherViewer())
    summary = teacher["export"]
    assert set(summary) == {
        "attemptId",
        "kind",
        "snapshotId",
        "status",
        "reason",
        "totalCells",
        "confirmedCells",
        "notWrittenCells",
        "pendingCells",
        "inProgress",
        "startedAt",
        "finishedAt",
    }
    assert summary["status"] == "SUCCESS" and summary["inProgress"] is False
    assert summary["totalCells"] == attempt.total_cells
    assert summary["startedAt"] == env.clock.now().isoformat(timespec="milliseconds")
    text = str(summary)
    assert all(
        a not in text for _, _, answers in env.world.winners.values() for a in answers
    )
    assert env.service.snapshot_extension(activity, GroupViewer(1)) == {}


def test_http_snapshot_teacher_has_export_student_does_not(make_env):
    """GET snapshot：老師有 export；同活動的學生沒有。"""
    env = make_env(stage="JOINING")
    device = join_group(env.client, env.code, 1)
    before = env.client.get(
        f"/api/activities/{env.code}/snapshot", headers=env.teacher.headers
    ).json()
    assert "export" not in before
    confirm(env)
    teacher = env.client.get(
        f"/api/activities/{env.code}/snapshot", headers=env.teacher.headers
    ).json()
    student = env.client.get(
        f"/api/activities/{env.code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()
    assert teacher["export"]["status"] == "SUCCESS"
    assert "export" not in student
