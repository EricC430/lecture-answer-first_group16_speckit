"""第一輪開始後鎖定、身分與階段閘門（US6、FR-020、FR-025）。"""

import asyncio

import pytest

from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from lecture_quiz.core.activity.models import Stage
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import OTHER_TEACHER, STUDENT, TEACHER


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    "stage",
    [Stage.ROUND_OPEN, Stage.RESULT_PENDING, Stage.RESULT_FINAL, Stage.ENDED],
)
def test_after_first_round_selecting_and_importing_are_rejected(
    service, activity, store, stage
):
    """Scenario: US6-AS1"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    assert run(service.import_sheet(CODE, TEACHER)).ok
    record, selection = store.records[CODE], store.selections[CODE]
    questions = activity.questions[CODE]
    activity.stages[CODE] = stage
    calls = len(activity.replace_calls)

    select = run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 7)))
    imported = run(service.import_sheet(CODE, TEACHER))

    assert select.rejection is ImportRejection.ROUND_STARTED
    assert imported.rejection is ImportRejection.ROUND_STARTED
    assert store.records[CODE] == record and store.selections[CODE] == selection
    assert activity.questions[CODE] == questions
    assert len(activity.replace_calls) == calls  # 連 001 都沒被呼叫


def test_001_rejects_changing_question_definition_after_round_started(activity, store):
    """Scenario: US6-AS2"""
    activity.questions[CODE] = (1, 2)
    activity.stages[CODE] = Stage.ROUND_OPEN
    outcome = run(activity.replace_questions(CODE, TEACHER, (1, 2, 3)))
    assert not outcome.ok
    assert activity.questions[CODE] == (1, 2)  # 題目定義不變


def test_cancelled_activity_says_cancelled(service, activity):
    """Edge: 活動不在「準備中」"""
    activity.stages[CODE] = Stage.CANCELLED
    for call in (
        lambda: service.import_sheet(CODE, TEACHER),
        lambda: service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)),
    ):
        result = run(call())
        assert result.rejection is ImportRejection.ACTIVITY_CANCELLED


def test_unrecognised_stage_is_rejected_defensively(service, activity):
    """Edge: 活動不在「準備中」"""
    activity.stages[CODE] = "SOMETHING_NEW"  # type: ignore[assignment]
    result = run(service.import_sheet(CODE, TEACHER))
    assert result.rejection is ImportRejection.STAGE_NOT_PREPARING


@pytest.mark.parametrize("who", [STUDENT, OTHER_TEACHER])
def test_non_teacher_is_rejected_everywhere_without_state_change(
    service, activity, store, who
):
    """Edge: 非老師的請求"""
    calls = (
        lambda: service.start_auth(CODE, who),
        lambda: service.inspect_spreadsheet(CODE, who, SPREADSHEET),
        lambda: service.select_source(CODE, who, SourceRef(SPREADSHEET, 0)),
        lambda: service.import_sheet(CODE, who),
        lambda: service.get_import_summary(CODE, who),
    )
    for call in calls:
        result = run(call())
        assert result.rejection is ImportRejection.NOT_TEACHER
    assert store.selections == {} and store.records == {}
    assert activity.replace_calls == [] and activity.questions[CODE] == ()


def test_unknown_activity_code_is_rejected(service):
    """Edge: 活動代碼不存在"""
    result = run(service.import_sheet("NOPE99", TEACHER))
    assert result.rejection is ImportRejection.ACTIVITY_NOT_FOUND
    assert run(service.start_auth("NOPE99", TEACHER)).rejection is (
        ImportRejection.ACTIVITY_NOT_FOUND
    )
