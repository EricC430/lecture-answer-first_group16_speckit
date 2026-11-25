"""ExportService.confirm_write 的閘門（US1）。"""

from lecture_quiz.app.ranking_review.ports import FinalizedRound  # noqa: F401
from lecture_quiz.app.result_export.models import AttemptStatus, ExportRejection
from tests.conftest import create_activity
from tests.unit.app.result_export.world import DEFAULT_PLAN, build_world


def preview_id(env):
    result = env.run(env.service.preview, env.code, env.requester())
    assert result.ok, result
    return result.value.snapshot.snapshot_id


def confirm(env, snapshot_id, requester=None):
    return env.run(
        env.service.confirm_write, env.code, requester or env.requester(), snapshot_id
    )


def test_confirm_with_current_snapshot_writes_winners_only(make_env):
    """Scenario: US1-AS1：確認後只寫入已定案搶答成功者的答案。"""
    env = make_env(stage="ROUND_OPEN")
    result = confirm(env, preview_id(env))
    assert result.ok and result.value.status is AttemptStatus.SUCCESS
    assert len(env.writer.write_calls) == 1
    written = {text for _, text in env.writer.write_calls[0]}
    expected = {a for _, _, answers in env.world.winners.values() for a in answers}
    assert written == expected


def test_stale_snapshot_is_rejected_and_nothing_written(make_env):
    """Scenario: US1-AS3 ↔ OpenSpec「預覽後新增定案結果」：舊預覽的確認被拒絕。"""
    env = make_env()
    old_id = preview_id(env)
    bigger = build_world(
        "a", DEFAULT_PLAN + ((3, 4, 1, 1, False),), unfinalized=(), code=env.code
    )
    env.world.ranking.rounds = bigger.ranking.rounds
    env.world.submissions.submissions = bigger.submissions.submissions
    result = confirm(env, old_id)
    assert not result.ok and result.rejection is ExportRejection.STALE_SNAPSHOT
    assert env.writer.write_calls == []
    assert preview_id(env) != old_id


def test_non_teacher_cannot_confirm(make_env):
    """Scenario: US1-AS5：非老師確認被拒絕，寫入呼叫數 0。"""
    env = make_env()
    snapshot_id = preview_id(env)
    other = create_activity(env.client)
    outsider = env.client.app.state.activity_service.resolve_requester(
        env.code, other.token
    )
    assert confirm(env, snapshot_id, outsider).rejection is ExportRejection.NOT_TEACHER
    assert (
        confirm(env, snapshot_id, env.student()).rejection
        is ExportRejection.NOT_TEACHER
    )
    assert env.writer.write_calls == []


def test_cancelled_activity_cannot_confirm(make_env):
    """Scenario: US1-AS7：已取消的活動不能確認寫回。"""
    env = make_env(stage="CANCELLED", plan=())
    result = confirm(env, "")
    assert result.rejection is ExportRejection.ACTIVITY_CANCELLED
    assert env.writer.write_calls == []


def test_ended_activity_still_works_and_nothing_is_written_automatically(make_env):
    """Scenario: US1-AS6：結束後照常預覽與確認；定案與結束當下不會自動寫回。"""
    env = make_env(stage="ENDED")
    assert env.writer.write_calls == [], "定案與結束都不得自動寫回"
    result = confirm(env, preview_id(env))
    assert result.ok and result.value.status is AttemptStatus.SUCCESS
    assert len(env.writer.write_calls) == 1


def test_no_results_cannot_confirm(make_env):
    """Scenario: US1-AS4：沒有可寫回的結果時確認也不送出寫入。"""
    env = make_env(plan=())
    assert confirm(env, "").rejection is ExportRejection.NO_RESULTS
    assert env.writer.write_calls == []
