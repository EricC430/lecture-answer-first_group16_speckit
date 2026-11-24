"""給 003 的介面：每題子空格數（contracts/service-interfaces.md「給 003」、T083）。"""

import asyncio

import pytest

from lecture_quiz.app.guided_notes_import.models import SourceRef
from tests.fixtures.guided_notes_layouts import defect_cases
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import TEACHER


def run(coro):
    return asyncio.run(coro)


def import_sheet(service, sheet_id):
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, sheet_id)))
    return run(service.import_sheet(CODE, TEACHER))


def test_none_before_any_successful_import(service):
    assert service.blanks_per_question(CODE) is None


def test_unknown_activity_gives_none(service):
    assert service.blanks_per_question("NOPE99") is None


def test_mixed_layout_counts_blanks_per_question(service):
    """原始題組範例：4 題 6 格 → 前兩題各 2 格、後兩題各 1 格。"""
    assert import_sheet(service, 0).ok
    assert dict(service.blanks_per_question(CODE)) == {1: 2, 2: 2, 3: 1, 4: 1}


def test_reimport_updates_the_counts(service):
    assert import_sheet(service, 0).ok
    first = dict(service.blanks_per_question(CODE))
    assert import_sheet(service, 7).ok  # 版面 B：4 題 7 格
    second = dict(service.blanks_per_question(CODE))
    assert sum(second.values()) == 7 and second != first


def test_rejected_reimport_keeps_the_previous_counts(service, reader):
    assert import_sheet(service, 0).ok
    before = dict(service.blanks_per_question(CODE))
    reader.snapshots[(SPREADSHEET, 0)] = defect_cases()["number_gap"].snapshot
    assert not run(service.import_sheet(CODE, TEACHER)).ok
    assert dict(service.blanks_per_question(CODE)) == before


def test_returned_mapping_is_a_copy(service):
    assert import_sheet(service, 0).ok
    result = service.blanks_per_question(CODE)
    with pytest.raises(TypeError):
        result[1] = 99  # type: ignore[index]
    assert dict(service.blanks_per_question(CODE)) == {1: 2, 2: 2, 3: 1, 4: 1}
