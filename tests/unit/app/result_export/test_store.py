"""ExportStore（共用基礎）。"""

import asyncio
import dataclasses
from datetime import UTC, datetime

from lecture_quiz.app.result_export.models import (
    AttemptKind,
    AttemptStatus,
    WriteAttempt,
)
from lecture_quiz.app.result_export.store import ExportStore

NOW = datetime(2026, 11, 24, tzinfo=UTC)


def attempt(n: int, status: AttemptStatus = AttemptStatus.SUCCESS) -> WriteAttempt:
    return WriteAttempt(
        attempt_id=n,
        kind=AttemptKind.WRITE,
        snapshot_id="1",
        items=(),
        status=status,
        reason=None,
        started_at=NOW,
    )


def test_unknown_activity_has_no_attempts():
    store = ExportStore()
    assert store.latest("ABC") is None and store.next_id("ABC") == 1


def test_add_and_latest_in_order_with_incrementing_ids():
    store = ExportStore()
    store.add_attempt("ABC", attempt(1))
    assert store.next_id("ABC") == 2
    store.add_attempt("ABC", attempt(2))
    assert store.latest("ABC").attempt_id == 2
    assert store.get("ABC", 1).attempt_id == 1 and store.get("ABC", 9) is None


def test_replace_updates_same_attempt_only():
    store = ExportStore()
    store.add_attempt("ABC", attempt(1, AttemptStatus.IN_PROGRESS))
    store.replace("ABC", dataclasses.replace(attempt(1), status=AttemptStatus.FAILED))
    assert store.latest("ABC").status is AttemptStatus.FAILED


def test_activities_are_independent_and_locks_are_per_activity():
    store = ExportStore()
    store.add_attempt("A", attempt(1))
    assert store.latest("B") is None
    assert store.lock("A") is store.lock("A")
    assert store.lock("A") is not store.lock("B")
    assert isinstance(store.lock("A"), asyncio.Lock)
