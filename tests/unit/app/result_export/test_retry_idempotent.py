"""重試（US4）：同一快照、冪等、每次重新檢查結構。"""

from lecture_quiz.app.result_export.models import (
    AttemptKind,
    AttemptReason,
    AttemptStatus,
    ExportRejection,
)
from tests.unit.app.result_export.world import SOURCE
from tests.unit.core.result_export.helpers import insert_row

KEY = (SOURCE.spreadsheet_id, SOURCE.sheet_id)


def confirm(env):
    sid = env.run(
        env.service.preview, env.code, env.requester()
    ).value.snapshot.snapshot_id
    return env.run(env.service.confirm_write, env.code, env.requester(), sid).value


def retry(env, attempt_id):
    return env.run(env.service.retry, env.code, env.requester(), attempt_id)


def test_five_retries_are_identical_and_idempotent(make_env):
    """Scenario: US4-AS3（重複寫回；SC-005）：N≥5 次重試，內容與第一次相同。"""
    env = make_env()
    first = confirm(env)
    grid = dict(env.reader.snapshots[KEY].cells)
    last = first
    for _ in range(5):
        last = retry(env, last.attempt_id).value
        assert last.status is AttemptStatus.SUCCESS and last.kind is AttemptKind.RETRY
        assert last.snapshot_id == first.snapshot_id and last.items == first.items
    assert len(env.writer.write_calls) == 6
    assert all(call == env.writer.write_calls[0] for call in env.writer.write_calls)
    assert dict(env.reader.snapshots[KEY].cells) == grid, "沒有附加重複文字"
    assert [a.attempt_id for a in env.store.attempts[env.code]] == [1, 2, 3, 4, 5, 6]


def test_retry_rechecks_structure_every_time(make_env):
    """Scenario: US4-AS5：重試前結構被改 → 整次停止、零寫入（重試不略過檢查）。"""
    env = make_env()
    first = confirm(env)
    writes = len(env.writer.write_calls)
    env.reader.snapshots[KEY] = insert_row(env.reader.snapshots[KEY], 0)
    result = retry(env, first.attempt_id).value
    assert (
        result.status is AttemptStatus.FAILED
        and result.reason is AttemptReason.STRUCTURE_CHANGED
    )
    assert len(env.writer.write_calls) == writes


def test_only_latest_attempt_and_unknown_attempt(make_env):
    """重試與核對只作用在最新一次嘗試；嘗試不存在 → ATTEMPT_NOT_FOUND。"""
    env = make_env()
    first = confirm(env)
    retry(env, first.attempt_id)
    old = retry(env, first.attempt_id)
    assert old.rejection is ExportRejection.NOT_LATEST_ATTEMPT
    assert retry(env, 99).rejection is ExportRejection.ATTEMPT_NOT_FOUND
    stale = env.run(env.service.recheck, env.code, env.requester(), first.attempt_id)
    assert stale.rejection is ExportRejection.NOT_LATEST_ATTEMPT


def test_retry_after_failure_can_succeed(make_env):
    """FAILED 的嘗試在問題排除後可重試成功。"""
    env = make_env()
    env.reader.snapshots[KEY] = insert_row(env.reader.snapshots[KEY], 0)
    sid = "1.2"
    failed = env.run(env.service.confirm_write, env.code, env.requester(), sid).value
    assert failed.status is AttemptStatus.FAILED
    # 還原學習單後重試
    from tests.unit.core.result_export.helpers import reparse  # noqa: F401

    env.reader.snapshots[KEY] = env.world.parsed.snapshot
    again = retry(env, failed.attempt_id).value
    assert again.status is AttemptStatus.SUCCESS
