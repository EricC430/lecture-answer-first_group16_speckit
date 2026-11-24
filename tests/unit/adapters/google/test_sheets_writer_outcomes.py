"""GoogleSheetsWriter 的回應分類（US4；research R6；手寫 mock）。"""

import asyncio
import logging
import socket

import httplib2
import pytest
from googleapiclient.http import HttpMockSequence

from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.app.result_export.models import AttemptReason
from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import OutcomeStatus
from tests.unit.adapters.google.mock_google import FakeCredentials, ok, status
from tests.unit.adapters.google.writer_helpers import SOURCE, make_writer, sequence

CELLS = [(CellRef(4, 7), "答")]
F, P = OutcomeStatus.FAILED, OutcomeStatus.PENDING


class RaisingHttp:
    """每次請求都丟出指定例外。"""

    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def request(self, *args, **kwargs):
        self.calls += 1
        raise self.exc


def write(http, credentials=None):
    writer = make_writer(http, credentials)
    return asyncio.run(writer.write_text_cells("ABC", SOURCE, CELLS))


def test_200_is_success():
    """200 → SUCCESS。"""
    result = write(sequence(ok({"replies": [{}]})))
    assert (result.outcome, result.reason) == (OutcomeStatus.SUCCESS, None)


@pytest.mark.parametrize(
    ("code", "outcome", "reason"),
    [
        (401, F, AttemptReason.AUTH_EXPIRED),
        (403, F, AttemptReason.PERMISSION_DENIED),
        (404, F, AttemptReason.PERMISSION_DENIED),
        (400, F, AttemptReason.REJECTED),
        (409, F, AttemptReason.REJECTED),
        (429, F, AttemptReason.RATE_LIMITED),
        (500, P, AttemptReason.UNKNOWN),
        (503, P, AttemptReason.UNKNOWN),
    ],
)
def test_http_status_classification(code, outcome, reason):
    """Scenario: US4-AS1：4xx 是明確失敗（原子，沒有格被改）；5xx 無法證實 → 待確認。"""
    result = write(sequence(status(code)))
    assert (result.outcome, result.reason) == (outcome, reason)


@pytest.mark.parametrize(
    "exc",
    [
        TimeoutError("timeout"),
        socket.gaierror(),
        TimeoutError(),
        httplib2.HttpLib2Error(),
        ConnectionResetError(),
        OSError("boom"),
    ],
)
def test_timeouts_and_network_errors_are_pending(exc):
    """Scenario: US4-AS1：逾時、連線中斷、其他網路例外 → 待確認，且不自動重試。"""
    http = RaisingHttp(exc)
    result = write(http)
    assert (result.outcome, result.reason) == (P, AttemptReason.UNKNOWN)
    assert http.calls == 1, "不得自動重試（重試由老師手動、結果才可解釋）"


@pytest.mark.parametrize(
    ("rejection", "reason"),
    [
        (ImportRejection.NOT_AUTHORIZED, AttemptReason.NOT_AUTHORIZED),
        (ImportRejection.AUTH_EXPIRED, AttemptReason.AUTH_EXPIRED),
        (ImportRejection.PERMISSION_DENIED, AttemptReason.PERMISSION_DENIED),
        (ImportRejection.READ_FAILED, AttemptReason.READ_FAILED),
    ],
)
def test_credential_failure_fails_before_any_request(rejection, reason):
    """憑證取得失敗 → 明確失敗，尚未送出任何請求。"""
    http = HttpMockSequence([])
    result = write(http, FakeCredentials(rejection))
    assert (result.outcome, result.reason) == (F, reason)
    assert http.request_sequence == []


def test_programming_errors_propagate():
    """程式錯誤照常往上拋，不被當成網路問題吞掉。"""
    with pytest.raises(KeyError):
        write(RaisingHttp(KeyError("bug")))


def test_log_has_status_only(caplog):
    """日誌只記狀態碼與原因，不含 Google 回應訊息本文、答案、儲存格內容。"""
    body = '{"error": {"message": "SECRET-MESSAGE", "status": "PERMISSION_DENIED"}}'
    http = HttpMockSequence(
        [({"status": "403", "content-type": "application/json"}, body)]
    )
    with caplog.at_level(logging.INFO):
        write(http)
    assert "SECRET-MESSAGE" not in caplog.text and "答" not in caplog.text
    assert "403" in caplog.text
