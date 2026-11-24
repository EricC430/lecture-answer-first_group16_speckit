"""ExportRejection 的訊息與狀態碼對照（共用基礎；FR-031）。"""

import pytest

from lecture_quiz.app.result_export.messages import http_status, message_of, reason_text
from lecture_quiz.app.result_export.models import AttemptReason, ExportRejection

FORBIDDEN = ["token", "Bearer", "client_secret", "/", "\\", "Traceback", ".py"]

EXPECTED_STATUS = {
    ExportRejection.INVALID_REQUEST: 400,
    ExportRejection.NOT_TEACHER: 403,
    ExportRejection.ACTIVITY_NOT_FOUND: 404,
    ExportRejection.ACTIVITY_CANCELLED: 409,
    ExportRejection.NO_RESULTS: 409,
    ExportRejection.STALE_SNAPSHOT: 409,
    ExportRejection.ATTEMPT_NOT_FOUND: 404,
    ExportRejection.NOT_LATEST_ATTEMPT: 409,
    ExportRejection.WRITE_IN_PROGRESS: 409,
    ExportRejection.NO_IMPORT_RECORD: 409,
    ExportRejection.NOT_AUTHORIZED: 401,
    ExportRejection.AUTH_EXPIRED: 401,
    ExportRejection.PERMISSION_DENIED: 403,
    ExportRejection.READ_FAILED: 502,
    ExportRejection.GOOGLE_NOT_CONFIGURED: 503,
}


def test_every_rejection_has_status_and_message():
    assert set(ExportRejection) == set(EXPECTED_STATUS)
    for rejection, status in EXPECTED_STATUS.items():
        assert http_status(rejection) == status
        assert message_of(rejection).strip()


@pytest.mark.parametrize("rejection", list(ExportRejection))
def test_messages_have_no_internal_details(rejection):
    text = message_of(rejection)
    for bad in FORBIDDEN:
        assert bad not in text, (rejection, bad)


def test_exact_messages_from_contract():
    assert (
        message_of(ExportRejection.ACTIVITY_CANCELLED)
        == "活動已取消，不提供寫回與 CSV 下載。"
    )
    assert "重新預覽" in message_of(ExportRejection.STALE_SNAPSHOT)
    assert "重新授權" in message_of(ExportRejection.AUTH_EXPIRED)
    assert "變數" not in message_of(ExportRejection.GOOGLE_NOT_CONFIGURED)


@pytest.mark.parametrize("reason", list(AttemptReason))
def test_every_attempt_reason_has_safe_text(reason):
    text = reason_text(reason)
    assert text.strip()
    for bad in FORBIDDEN:
        assert bad not in text
