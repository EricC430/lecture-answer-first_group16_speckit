"""Google 例外 → 拒絕代碼（US1-AS4）。"""

import httplib2
import pytest
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError

from lecture_quiz.adapters.google.errors import map_exception
from lecture_quiz.app.guided_notes_import.messages import message_for
from lecture_quiz.app.guided_notes_import.models import ImportRejection


def http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}", uri="https://x")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (http_error(401), ImportRejection.AUTH_EXPIRED),
        (http_error(403), ImportRejection.PERMISSION_DENIED),
        (http_error(404), ImportRejection.PERMISSION_DENIED),
        (http_error(429), ImportRejection.READ_FAILED),
        (http_error(500), ImportRejection.READ_FAILED),
        (http_error(503), ImportRejection.READ_FAILED),
        (RefreshError("revoked"), ImportRejection.AUTH_EXPIRED),
        (TransportError("down"), ImportRejection.READ_FAILED),
        (TimeoutError(), ImportRejection.READ_FAILED),
        (httplib2.ServerNotFoundError("dns"), ImportRejection.READ_FAILED),
        (ConnectionResetError(), ImportRejection.READ_FAILED),
    ],
)
def test_exception_mapping(exc, expected):
    """Scenario: US1-AS4；Edge: 選檔後檔案消失或失去權限"""
    assert map_exception(exc) is expected


def test_messages_of_mapped_rejections_leak_nothing():
    for exc in (http_error(401), http_error(403), http_error(500), RefreshError("tok")):
        text = message_for(map_exception(exc))
        assert "tok" not in text.lower() and "http" not in text.lower()
