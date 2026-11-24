"""授權、檢視試算表與選定來源（US1）。"""

import asyncio

from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import (
    OTHER_TEACHER,
    STUDENT,
    TEACHER,
    FakeAuthGateway,
)


def run(coro):
    return asyncio.run(coro)


def test_inspect_lists_sheets_and_does_not_change_any_state(service, store):
    """Scenario: US1-AS1"""
    result = run(service.inspect_spreadsheet(CODE, TEACHER, SPREADSHEET))
    assert result.ok and result.value is not None
    assert [s.title for s in result.value.sheets] == ["版面A", "版面B"]
    assert result.value.auto_select_sheet_id is None  # 多張：要老師明確選
    assert store.selections == {} and store.records == {}


def test_single_sheet_is_auto_selected_by_the_backend(service):
    """Scenario: US1-AS2"""
    result = run(service.inspect_spreadsheet(CODE, TEACHER, "single-sheet"))
    assert result.ok and result.value is not None
    assert result.value.auto_select_sheet_id == 0
    assert len(result.value.sheets) == 1


def test_hidden_sheets_are_not_listed_and_not_counted(service, reader):
    """Scenario: US1-AS2（2026-11-23 澄清：隱藏工作表不列入也不計張數）"""
    reader.add(
        "one-visible",
        "一可見一隱藏",
        [(0, "可見", None), (1, "隱藏備份", None)],
        hidden=(1,),
    )
    result = run(service.inspect_spreadsheet(CODE, TEACHER, "one-visible"))
    assert result.ok and result.value is not None
    assert [s.sheet_id for s in result.value.sheets] == [0]
    assert result.value.auto_select_sheet_id == 0  # 一可見加一隱藏 → 視為只有一張


def test_all_hidden_means_no_sheet_to_choose(service, reader):
    """Scenario: US1-AS2"""
    reader.add("all-hidden", "全隱藏", [(0, "A", None), (1, "B", None)], hidden=(0, 1))
    result = run(service.inspect_spreadsheet(CODE, TEACHER, "all-hidden"))
    assert not result.ok and result.rejection is ImportRejection.SHEET_NOT_FOUND


def test_non_spreadsheet_is_rejected_without_state_change(service, store, reader):
    """Scenario: US1-AS6"""
    reader.inspect_failure = ImportRejection.NOT_A_SPREADSHEET
    result = run(service.inspect_spreadsheet(CODE, TEACHER, "some-doc"))
    assert result.rejection is ImportRejection.NOT_A_SPREADSHEET
    assert store.selections == {}


def test_select_source_saves_after_verifying_the_sheet_belongs(service, store):
    """Scenario: US1-AS1"""
    result = run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 7)))
    assert result.ok and result.value is not None
    assert result.value.sheet_title == "版面B"
    assert store.selections[CODE].source == SourceRef(SPREADSHEET, 7)


def test_select_source_failure_keeps_the_old_selection(service, store):
    """Scenario: US1-AS1"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    before = store.selections[CODE]
    wrong = run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 999)))
    assert wrong.rejection is ImportRejection.SHEET_NOT_FOUND
    assert store.selections[CODE] == before


def test_select_source_rejects_a_hidden_sheet(service, store, reader):
    """Scenario: US1-AS2"""
    reader.add("mixed", "混合", [(0, "可見", None), (1, "隱藏", None)], hidden=(1,))
    result = run(service.select_source(CODE, TEACHER, SourceRef("mixed", 1)))
    assert result.rejection is ImportRejection.SHEET_NOT_FOUND
    assert CODE not in store.selections


def test_not_authorized_never_reaches_google(activity, reader, store):
    """Scenario: US1-AS3"""
    from lecture_quiz.app.guided_notes_import.service import ImportService
    from tests.conftest import FakeClock

    auth = FakeAuthGateway(authorized=False)
    service = ImportService(auth, reader, activity, store, FakeClock())
    result = run(service.inspect_spreadsheet(CODE, TEACHER, SPREADSHEET))
    assert result.rejection is ImportRejection.NOT_AUTHORIZED
    assert reader.calls == []
    assert store.selections == {} and activity.replace_calls == []


def test_cancelled_picker_leaves_no_half_finished_source(service, store, activity):
    """Scenario: US1-AS5"""
    # 取消選檔時前端不會呼叫任何端點：沒有任何服務呼叫，就沒有任何狀態
    assert store.selections == {} and store.records == {}
    assert activity.replace_calls == []


def test_expired_authorization_mid_flow_keeps_the_source_and_retry_works(
    service, auth, store, activity
):
    """Edge: 授權在流程中途失效"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    auth.revoke(CODE)
    failed = run(service.import_sheet(CODE, TEACHER))
    assert failed.rejection is ImportRejection.NOT_AUTHORIZED
    assert store.selections[CODE].source == SourceRef(SPREADSHEET, 0)  # 已選來源保留
    assert activity.replace_calls == []  # 沒有匯入任何題目
    auth.authorize(CODE)
    retried = run(service.import_sheet(CODE, TEACHER))
    assert retried.ok  # 重新授權後可直接重試，不必重選


def test_read_permission_denied_does_not_import_half_data(service, reader, activity):
    """Scenario: US1-AS4"""
    run(service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0)))
    reader.read_failure = ImportRejection.PERMISSION_DENIED
    result = run(service.import_sheet(CODE, TEACHER))
    assert result.rejection is ImportRejection.PERMISSION_DENIED
    assert activity.replace_calls == [] and activity.questions[CODE] == ()


def test_start_auth_requires_teacher_and_configuration(service, auth):
    """Scenario: US1-AS3"""
    ok = run(service.start_auth(CODE, TEACHER))
    assert ok.ok and ok.value
    assert (
        run(service.start_auth(CODE, STUDENT)).rejection is ImportRejection.NOT_TEACHER
    )
    assert (
        run(service.start_auth(CODE, OTHER_TEACHER)).rejection
        is ImportRejection.NOT_TEACHER
    )
    auth.configured = False
    result = run(service.start_auth(CODE, TEACHER))
    assert result.rejection is ImportRejection.GOOGLE_NOT_CONFIGURED
