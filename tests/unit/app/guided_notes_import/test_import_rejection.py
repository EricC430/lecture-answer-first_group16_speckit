"""有缺陷的學習單被拒絕時，既有資料完全不變（US4-AS5）。"""

import asyncio

import pytest

from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from tests.fixtures.guided_notes_layouts import defect_cases
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import TEACHER

CASES = defect_cases()


@pytest.mark.parametrize("name", sorted(CASES))
def test_defect_is_rejected_and_previous_import_is_untouched(
    name, service, reader, activity, store
):
    """Scenario: US4-AS5"""
    asyncio.run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    assert asyncio.run(service.import_sheet(CODE, TEACHER)).ok
    record_before = store.records[CODE]
    questions_before = activity.questions[CODE]
    calls_before = list(activity.replace_calls)

    reader.add("bad", "壞的", [(0, "壞", CASES[name].snapshot)])
    asyncio.run(service.select_source(CODE, TEACHER, SourceRef("bad", 0)))
    outcome = asyncio.run(service.import_sheet(CODE, TEACHER))

    assert outcome.rejection is ImportRejection.VALIDATION_FAILED
    assert activity.replace_calls == calls_before  # 001 沒有被呼叫
    assert activity.questions[CODE] == questions_before
    assert store.records[CODE] == record_before
