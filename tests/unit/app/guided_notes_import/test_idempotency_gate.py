"""POST /import 的 Idempotency-Key：先確認身分，只快取成功與驗證失敗（PR #17）。"""

import asyncio

from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from tests.fixtures.guided_notes_layouts import defect_cases
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import OTHER_TEACHER, STUDENT, TEACHER


def run(coro):
    return asyncio.run(coro)


def select(service):
    assert run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0))).ok


def test_a_cached_success_is_not_replayed_to_a_non_teacher(service, activity):
    select(service)
    assert run(service.import_sheet(CODE, TEACHER, idempotency_key="k")).ok
    for who in (STUDENT, OTHER_TEACHER):
        outcome = run(service.import_sheet(CODE, who, idempotency_key="k"))
        assert not outcome.ok and outcome.rejection is ImportRejection.NOT_TEACHER
        assert outcome.preview is None


def test_a_non_teacher_failure_does_not_poison_the_teachers_retry(service, activity):
    select(service)
    denied = run(service.import_sheet(CODE, STUDENT, idempotency_key="k"))
    assert denied.rejection is ImportRejection.NOT_TEACHER
    assert run(service.import_sheet(CODE, TEACHER, idempotency_key="k")).ok


def test_transient_read_failure_is_not_cached(service, reader):
    select(service)
    reader.read_failure = ImportRejection.READ_FAILED
    first = run(service.import_sheet(CODE, TEACHER, idempotency_key="k"))
    assert first.rejection is ImportRejection.READ_FAILED
    reader.read_failure = None
    assert run(service.import_sheet(CODE, TEACHER, idempotency_key="k")).ok


def test_validation_failure_is_replayed_without_rereading(service, reader):
    select(service)
    reader.snapshots[(SPREADSHEET, 0)] = defect_cases()["number_gap"].snapshot
    first = run(service.import_sheet(CODE, TEACHER, idempotency_key="k"))
    reads = len([c for c in reader.calls if c.startswith("read:")])
    second = run(service.import_sheet(CODE, TEACHER, idempotency_key="k"))
    assert first == second and first.rejection is ImportRejection.VALIDATION_FAILED
    assert len([c for c in reader.calls if c.startswith("read:")]) == reads


def test_success_replay_still_works_for_the_teacher(service, activity):
    select(service)
    first = run(service.import_sheet(CODE, TEACHER, idempotency_key="k"))
    second = run(service.import_sheet(CODE, TEACHER, idempotency_key="k"))
    assert first == second and len(activity.replace_calls) == 1
