"""`import_sheet` 的順序、原子性與並行（research R6）。"""

import asyncio

from lecture_quiz.app.guided_notes_import.models import ImportRejection, SourceRef
from lecture_quiz.core.activity.models import Stage
from tests.fixtures.guided_notes_layouts import layout_b
from tests.unit.app.guided_notes_import.conftest import CODE, SPREADSHEET
from tests.unit.app.guided_notes_import.fakes import TEACHER, FakeActivityGateway


def run(coro):
    return asyncio.run(coro)


def select(service, sheet_id=0, spreadsheet=SPREADSHEET):
    assert run(
        service.select_source(CODE, TEACHER, SourceRef(spreadsheet, sheet_id))
    ).ok


def test_successful_import_sends_only_question_numbers_to_001(service, activity, store):
    """Scenario: US2-AS1"""
    select(service, 0)
    outcome = run(service.import_sheet(CODE, TEACHER))
    assert outcome.ok and outcome.preview is not None
    assert activity.replace_calls == [(CODE, (1, 2, 3, 4))]  # 只有題號清單
    assert activity.questions[CODE] == (1, 2, 3, 4)
    assert outcome.version == activity.versions[CODE]
    record = store.records[CODE]
    assert record.question_numbers == (1, 2, 3, 4)
    assert len(record.blanks) == 6 and record.sheet_title == "版面A"
    assert outcome.preview.total_questions == 4 and outcome.preview.total_blanks == 6


def test_order_is_stage_then_read_then_parse_then_replace_then_save(
    service, activity, reader, store
):
    """Scenario: US2-AS1"""
    events: list[str] = []
    select(service, 0)
    reader.before_read = lambda: events.append(f"read(records={CODE in store.records})")
    activity.before_replace = lambda: events.append(
        f"replace(records={CODE in store.records})"
    )
    assert run(service.import_sheet(CODE, TEACHER)).ok
    # 讀取與 001 接受之前，002 都還沒保存任何記錄；001 接受後才保存
    assert events == ["read(records=False)", "replace(records=False)"]
    assert CODE in store.records


def test_validation_failure_saves_nothing_and_does_not_call_001(
    service, activity, reader, store
):
    """Scenario: US4-AS5"""
    from tests.fixtures.guided_notes_layouts import defect_cases

    bad = defect_cases()["number_gap"].snapshot
    reader.add("bad", "壞的", [(0, "壞", bad)])
    select(service, 0, "bad")
    outcome = run(service.import_sheet(CODE, TEACHER))
    assert not outcome.ok and outcome.rejection is ImportRejection.VALIDATION_FAILED
    assert outcome.issues
    assert activity.replace_calls == [] and CODE not in store.records


def test_gateway_rejection_saves_nothing(service, activity, store):
    """Edge: 解析後、寫入前階段或身分改變"""
    select(service, 0)
    activity.before_replace = lambda: activity.stages.__setitem__(
        CODE, Stage.ROUND_OPEN
    )
    outcome = run(service.import_sheet(CODE, TEACHER))
    assert outcome.rejection is ImportRejection.GATEWAY_REJECTED
    assert CODE not in store.records and activity.questions[CODE] == ()


def test_reading_happens_once_and_later_edits_do_not_change_the_import(
    service, reader, store
):
    """Edge: 讀取期間老師編輯試算表"""
    select(service, 0)
    assert run(service.import_sheet(CODE, TEACHER)).ok
    before = store.records[CODE]
    # 匯入後老師改了試算表：已匯入的結果不自動更新
    changed, _ = layout_b()
    reader.snapshots[(SPREADSHEET, 0)] = changed
    assert store.records[CODE] == before
    assert reader.calls.count(f"read:{SPREADSHEET}:0") == 1


def test_concurrent_imports_are_serialized_and_the_last_one_wins(
    service, reader, activity, store
):
    """Edge: 連續快速重複匯入"""
    active = 0
    max_active = 0
    original_read = reader.read

    async def slow_read(code, source):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)  # 讓兩個匯入有機會交錯
        try:
            return await original_read(code, source)
        finally:
            active -= 1

    reader.read = slow_read  # type: ignore[method-assign]

    async def scenario():
        await service.select_source(CODE, TEACHER, SourceRef(SPREADSHEET, 0))
        return await asyncio.gather(
            service.import_sheet(CODE, TEACHER), service.import_sheet(CODE, TEACHER)
        )

    first, second = run(scenario())
    assert first.ok and second.ok
    assert max_active == 1  # 匯入鎖讓兩次匯入依序執行，沒有交錯
    assert len(activity.replace_calls) == 2
    assert store.records[CODE].question_numbers == activity.questions[CODE]
    assert activity.versions[CODE] == 3  # 兩次各整份取代一次


def test_multiple_activities_are_independent(auth, reader, store):
    """Scenario: US5-AS1（多個活動同時存在互不影響）"""
    from lecture_quiz.app.guided_notes_import.service import ImportService
    from tests.conftest import FakeClock

    gateway = FakeActivityGateway()
    gateway.add_activity("AAA111")
    gateway.add_activity("BBB222")
    svc = ImportService(auth, reader, gateway, store, FakeClock())
    run(svc.select_source("AAA111", TEACHER, SourceRef(SPREADSHEET, 0)))
    assert run(svc.import_sheet("AAA111", TEACHER)).ok
    assert "BBB222" not in store.records and "BBB222" not in store.selections
    assert gateway.questions["BBB222"] == ()
    outcome = run(svc.import_sheet("BBB222", TEACHER))
    assert outcome.rejection is ImportRejection.SOURCE_NOT_SELECTED


def test_import_without_selected_source(service, activity):
    """Scenario: US1-AS1"""
    outcome = run(service.import_sheet(CODE, TEACHER))
    assert outcome.rejection is ImportRejection.SOURCE_NOT_SELECTED
    assert activity.replace_calls == []


def test_same_idempotency_key_returns_first_result_without_reimporting(
    service, activity
):
    """FR-019（POST /import 的 Idempotency-Key）"""
    select(service, 0)
    first = run(service.import_sheet(CODE, TEACHER, idempotency_key="k1"))
    second = run(service.import_sheet(CODE, TEACHER, idempotency_key="k1"))
    assert first == second
    assert len(activity.replace_calls) == 1
