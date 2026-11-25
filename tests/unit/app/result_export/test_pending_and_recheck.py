"""待確認與重新讀取核對（US4）。"""

from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.app.result_export.models import (
    AttemptReason,
    AttemptStatus,
    ExportRejection,
)
from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.result_export.models import OutcomeStatus
from tests.unit.app.result_export.world import SOURCE

PENDING = WriteResult(OutcomeStatus.PENDING, AttemptReason.UNKNOWN)


def confirm(env):
    sid = env.run(
        env.service.preview, env.code, env.requester()
    ).value.snapshot.snapshot_id
    return env.run(env.service.confirm_write, env.code, env.requester(), sid).value


def recheck(env, attempt_id):
    return env.run(env.service.recheck, env.code, env.requester(), attempt_id)


def test_lost_response_is_pending_not_success_nor_unwritten(make_env):
    """Scenario: US4-AS1（外部寫入後回應遺失）：待確認，不宣稱成功也不宣稱未寫入。"""
    env = make_env()
    env.writer.next_result = PENDING
    attempt = confirm(env)
    assert (
        attempt.status is AttemptStatus.PENDING
        and attempt.reason is AttemptReason.UNKNOWN
    )
    assert attempt.pending_cells == attempt.total_cells > 0
    assert attempt.confirmed_cells == 0 and attempt.not_written_cells == 0
    # 活動中任何定案結果都沒有被回滾
    assert env.world.ranking.rounds and env.world.winners


def test_recheck_actually_written_becomes_success_without_reading_structure(make_env):
    """Scenario: US4-AS2：外部其實已寫入 → 核對為 SUCCESS；只讀取、不做結構檢查。"""
    env = make_env()
    env.writer.next_result = PENDING
    env.writer.apply_on_pending = True
    attempt = confirm(env)
    reads, writes = len(env.reader.calls), len(env.writer.write_calls)
    result = recheck(env, attempt.attempt_id).value
    assert result.status is AttemptStatus.SUCCESS and result.reason is None
    assert result.confirmed_cells == result.total_cells and result.pending_cells == 0
    assert len(env.reader.calls) == reads, "核對不做結構檢查（clarify Q2）"
    assert len(env.writer.write_calls) == writes
    assert len(result.cell_checks) == result.total_cells and all(
        c.matches for c in result.cell_checks
    )


def test_recheck_nothing_written_becomes_failed_not_written(make_env):
    """Scenario: US4-AS2：外部其實沒寫入 → FAILED(NOT_WRITTEN)，可重試。"""
    env = make_env()
    env.writer.next_result = PENDING
    attempt = confirm(env)
    result = recheck(env, attempt.attempt_id).value
    assert (
        result.status is AttemptStatus.FAILED
        and result.reason is AttemptReason.NOT_WRITTEN
    )
    assert (
        result.not_written_cells == result.total_cells and result.confirmed_cells == 0
    )


def test_recheck_partial_stays_pending_and_lists_mismatches(make_env):
    """Scenario: US4-AS2：只寫入一部分 → 維持待確認並列出不符的格。"""
    env = make_env()
    env.writer.next_result = PENDING
    attempt = confirm(env)
    env.writer.apply(SOURCE, env.writer.write_calls[0][:1])
    result = recheck(env, attempt.attempt_id).value
    assert result.status is AttemptStatus.PENDING
    assert (
        result.confirmed_cells == 1 and result.pending_cells == result.total_cells - 1
    )
    assert sum(1 for c in result.cell_checks if not c.matches) == result.pending_cells


def test_recheck_read_failure_keeps_attempt_unchanged(make_env):
    """U1：核對時讀取失敗只回錯誤，該嘗試的狀態與格數不變。"""
    env = make_env()
    env.writer.next_result = PENDING
    attempt = confirm(env)
    env.writer.read_failure = ImportRejection.AUTH_EXPIRED
    result = recheck(env, attempt.attempt_id)
    assert not result.ok and result.rejection is ExportRejection.AUTH_EXPIRED
    kept = env.store.latest(env.code)
    assert (
        kept.status is AttemptStatus.PENDING
        and kept.pending_cells == attempt.pending_cells
    )
