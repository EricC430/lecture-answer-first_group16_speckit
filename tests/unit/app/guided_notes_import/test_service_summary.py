"""匯入預覽與恢復（US5-AS1、AS3）。"""

import asyncio

from lecture_quiz.app.guided_notes_import.models import SourceRef
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import OTHER_TEACHER, STUDENT, TEACHER


def run(coro):
    return asyncio.run(coro)


def test_preview_shows_numbers_per_question_and_totals(service):
    """Scenario: US5-AS1"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    outcome = run(service.import_sheet(CODE, TEACHER))
    assert outcome.ok and outcome.preview is not None
    preview = outcome.preview
    assert preview.question_numbers == (1, 2, 3, 4)
    assert dict(preview.blanks_per_question) == {1: 2, 2: 2, 3: 1, 4: 1}
    assert (preview.total_questions, preview.total_blanks) == (4, 6)


def test_group_counts_as_one_question_but_blanks_accumulate(service):
    """Scenario: US5-AS3"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 7)))
    preview = run(service.import_sheet(CODE, TEACHER)).preview
    assert preview is not None
    assert preview.total_questions == 4  # 題組不按子空格增加題數
    assert preview.total_blanks == 7


def test_summary_is_restored_after_refresh_and_none_before_import(service):
    """Scenario: US5-AS1"""
    assert run(service.get_import_summary(CODE, TEACHER)).value is None
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    run(service.import_sheet(CODE, TEACHER))
    restored = run(service.get_import_summary(CODE, TEACHER))
    assert restored.ok and restored.value is not None
    assert restored.value.total_blanks == 6


def test_summary_is_for_the_activity_teacher_only(service):
    """FR-025"""
    for who in (STUDENT, OTHER_TEACHER):
        result = run(service.get_import_summary(CODE, who))
        assert result.rejection is not None and not result.ok


def test_get_import_record_is_read_only_data_for_005(service):
    """FR-024"""
    assert service.get_import_record(CODE) is None
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    run(service.import_sheet(CODE, TEACHER))
    record = service.get_import_record(CODE)
    assert record is not None
    assert record.source == SourceRef(SPREADSHEET, 0)
    assert len(record.blanks) == 6 and record.structure.data_start_row == 4


def test_import_record_is_immutable_so_005_cannot_change_it(service, store):
    """FR-024（005 只能讀 ImportRecord，不得修改）"""
    import dataclasses

    import pytest

    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    run(service.import_sheet(CODE, TEACHER))
    record = service.get_import_record(CODE)
    assert record is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.question_numbers = (9,)  # type: ignore[misc]
    assert isinstance(record.blanks, tuple)  # 沒有可就地修改的容器
    assert store.records[CODE].question_numbers == (1, 2, 3, 4)
