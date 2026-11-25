"""授權與讀取失敗（US2-AS5）：寫入之前停止，屬明確失敗。"""

import pytest

from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.app.result_export.messages import reason_text
from lecture_quiz.app.result_export.models import (
    AttemptReason,
    AttemptStatus,
    ExportRejection,
)

CASES = [
    (
        ImportRejection.NOT_AUTHORIZED,
        ExportRejection.NOT_AUTHORIZED,
        AttemptReason.NOT_AUTHORIZED,
    ),
    (
        ImportRejection.AUTH_EXPIRED,
        ExportRejection.AUTH_EXPIRED,
        AttemptReason.AUTH_EXPIRED,
    ),
    (
        ImportRejection.PERMISSION_DENIED,
        ExportRejection.PERMISSION_DENIED,
        AttemptReason.PERMISSION_DENIED,
    ),
    (
        ImportRejection.READ_FAILED,
        ExportRejection.READ_FAILED,
        AttemptReason.READ_FAILED,
    ),
    (
        ImportRejection.GOOGLE_NOT_CONFIGURED,
        ExportRejection.GOOGLE_NOT_CONFIGURED,
        AttemptReason.NOT_CONFIGURED,
    ),
]


@pytest.mark.parametrize(("failure", "rejection", "reason"), CASES)
def test_preview_and_confirm_stop_before_any_write(
    make_env, failure, rejection, reason
):
    """Scenario: US2-AS5：預覽回對應錯誤；確認記為 FAILED，寫入呼叫數 0。"""
    env = make_env()
    snapshot_id = env.run(
        env.service.preview, env.code, env.requester()
    ).value.snapshot.snapshot_id
    env.reader.read_failure = failure
    preview = env.run(env.service.preview, env.code, env.requester())
    assert not preview.ok and preview.rejection is rejection
    attempt = env.run(
        env.service.confirm_write, env.code, env.requester(), snapshot_id
    ).value
    assert attempt.status is AttemptStatus.FAILED and attempt.reason is reason
    assert env.writer.write_calls == []
    assert attempt.confirmed_cells == 0 and attempt.pending_cells == 0
    assert "token" not in reason_text(reason)


def test_cell_read_failure_in_preview_is_reported(make_env):
    """預覽讀取目標格失敗（授權失效）也回對應錯誤，不顯示預覽。"""
    env = make_env()
    env.writer.read_failure = ImportRejection.AUTH_EXPIRED
    result = env.run(env.service.preview, env.code, env.requester())
    assert result.rejection is ExportRejection.AUTH_EXPIRED
    assert env.writer.write_calls == []


def test_guidance_mentions_reauthorization_or_permission():
    """Scenario: US2-AS5：訊息指引重新授權或調整權限，不含憑證。"""
    assert "重新授權" in reason_text(AttemptReason.AUTH_EXPIRED)
    assert "權限" in reason_text(AttemptReason.PERMISSION_DENIED)
