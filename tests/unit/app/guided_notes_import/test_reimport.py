"""準備中與開放加入都可重新匯入，整份取代（US5）。"""

import asyncio

import pytest

from lecture_quiz.app.guided_notes_import.models import SourceRef
from lecture_quiz.core.activity.models import Stage
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import TEACHER


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("stage", [Stage.PREPARING, Stage.JOINING])
def test_reimport_replaces_the_whole_previous_result(service, activity, store, stage):
    """Scenario: US5-AS2"""
    activity.stages[CODE] = stage
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    assert run(service.import_sheet(CODE, TEACHER)).ok
    first = store.records[CODE]
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 7)))
    second_outcome = run(service.import_sheet(CODE, TEACHER))
    assert second_outcome.ok
    second = store.records[CODE]
    assert second != first
    assert second.sheet_title == "版面B"
    assert second.question_numbers == (1, 2, 3, 4) and len(second.blanks) == 7
    assert activity.questions[CODE] == (1, 2, 3, 4)
    # 沒有舊題目的殘餘：每個來源映射都屬於新來源
    assert all(b.target.col >= 4 for b in second.blanks)


def test_reimporting_the_same_sheet_after_fixing_it_updates_the_result(
    service, reader, store
):
    """Scenario: US5-AS4"""
    from tests.fixtures.guided_notes_layouts import layout_a

    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    assert run(service.import_sheet(CODE, TEACHER)).ok
    before = store.records[CODE]
    shifted, _ = layout_a(origin=(3, 2))
    reader.snapshots[(SPREADSHEET, 0)] = (
        shifted  # 老師修正（這裡以整體移位代表內容更新）
    )
    assert run(service.import_sheet(CODE, TEACHER)).ok
    after = store.records[CODE]
    assert after != before
    assert [(b.target.row, b.target.col) for b in after.blanks] != [
        (b.target.row, b.target.col) for b in before.blanks
    ]
