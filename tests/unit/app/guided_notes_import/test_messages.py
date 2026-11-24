"""固定訊息對照表（FR-022、SC-005）。"""

import re

import pytest

from lecture_quiz.app.guided_notes_import.messages import MESSAGES, message_for
from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.core.guided_notes_import.hints import ISSUE_HINTS
from lecture_quiz.core.guided_notes_import.models import IssueKind

FORBIDDEN = re.compile(
    r"token|secret|state=|client_|traceback|stack|\.py|[A-Za-z]:\\|/home/|googleapis|"
    r"GOOGLE_|OAUTH_|api[_ ]?key|Exception|Error:",
    re.IGNORECASE,
)


@pytest.mark.parametrize("rejection", list(ImportRejection))
def test_every_rejection_has_a_clean_message(rejection):
    """Edge: 輸入驗證失敗"""
    text = message_for(rejection)
    assert text.strip()
    assert FORBIDDEN.search(text) is None, text


def test_table_has_no_extra_or_missing_codes():
    assert set(MESSAGES) == set(ImportRejection)


@pytest.mark.parametrize("kind", list(IssueKind))
def test_every_issue_kind_has_an_actionable_hint(kind):
    hint = ISSUE_HINTS[kind]
    assert "請" in hint, "修正建議要告訴老師可以怎麼做"
    assert FORBIDDEN.search(hint) is None


def test_google_not_configured_message_does_not_name_variables():
    assert "GOOGLE" not in message_for(ImportRejection.GOOGLE_NOT_CONFIGURED)
