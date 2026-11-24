"""`SubmissionStore`：記憶體存放區（003 研究 R1）。"""

from lecture_quiz.app.round_submission.store import SubmissionStore
from lecture_quiz.core.round_submission.models import SubmissionLedger
from tests.unit.core.round_submission.helpers import make_submission


def test_unknown_code_returns_empty_ledger():
    ledger = SubmissionStore().get("NOPE00")
    assert ledger == SubmissionLedger()


def test_put_then_get_returns_same_object():
    store = SubmissionStore()
    ledger = SubmissionLedger().with_added(make_submission())
    store.put("K7QH2M", ledger)
    assert store.get("K7QH2M") is ledger


def test_activities_are_isolated():
    store = SubmissionStore()
    store.put("AAAAAA", SubmissionLedger().with_added(make_submission()))
    assert store.get("BBBBBB") == SubmissionLedger()
