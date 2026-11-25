"""結構檢查的服務層行為（US2）：不符就整次停止、零寫入。"""

import pytest

from lecture_quiz.app.result_export.models import AttemptReason, AttemptStatus
from lecture_quiz.app.result_export.views import MAX_DIFFERENCES, structure_json
from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import (
    DiffKind,
    StructureCheck,
    StructureDifference,
)
from tests.unit.app.result_export.world import SOURCE
from tests.unit.core.result_export.helpers import insert_row, renamed, with_text

KEY = (SOURCE.spreadsheet_id, SOURCE.sheet_id)


def preview(env):
    return env.run(env.service.preview, env.code, env.requester())


def confirm(env):
    snapshot_id = preview(env).value.snapshot.snapshot_id
    return env.run(env.service.confirm_write, env.code, env.requester(), snapshot_id)


def header_row(env):
    s = env.world.parsed.structure
    return min(s.header_number.row, s.header_answer.row)


@pytest.mark.parametrize("layout", ["a", "b"])
def test_inserted_row_stops_the_whole_write(make_env, layout):
    """Scenario: US2-AS1（表頭不變但答案列移動）：停止寫回、不向舊座標寫入。"""
    env = make_env(layout=layout)
    env.reader.snapshots[KEY] = insert_row(
        env.reader.snapshots[KEY], header_row(env) + 1
    )
    before = dict(env.reader.snapshots[KEY].cells)
    attempt = confirm(env).value
    assert attempt.status is AttemptStatus.FAILED
    assert attempt.reason is AttemptReason.STRUCTURE_CHANGED
    assert attempt.differences and attempt.differences[0].kind is not DiffKind.IDENTITY
    assert env.writer.write_calls == []
    assert dict(env.reader.snapshots[KEY].cells) == before
    assert (
        attempt.not_written_cells == attempt.total_cells
        and attempt.confirmed_cells == 0
    )


@pytest.mark.parametrize("layout", ["a", "b"])
def test_sheet_replaced_or_deleted_is_identity_difference(make_env, layout):
    """Scenario: US2-AS2：工作表已不存在（被刪或換掉）→ IDENTITY、零寫入。"""
    env = make_env(layout=layout)
    snapshot_id = preview(env).value.snapshot.snapshot_id
    del env.reader.snapshots[KEY]
    attempt = env.run(
        env.service.confirm_write, env.code, env.requester(), snapshot_id
    ).value
    assert attempt.status is AttemptStatus.FAILED
    assert [d.kind for d in attempt.differences] == [DiffKind.IDENTITY]
    assert env.writer.write_calls == []
    view = preview(env).value
    assert (
        not view.can_confirm and view.structure.differences[0].kind is DiffKind.IDENTITY
    )


def test_deleted_header_is_unrecognized(make_env):
    """Scenario: US2-AS2：表頭被刪 → UNRECOGNIZED，零寫入。"""
    env = make_env()
    snap = env.reader.snapshots[KEY]
    cells = dict(snap.cells)
    cells.pop(env.world.parsed.structure.header_answer)
    env.reader.snapshots[KEY] = type(snap)(
        snap.spreadsheet_id,
        snap.sheet_id,
        snap.sheet_name,
        snap.row_count,
        snap.col_count,
        cells,
        snap.merges,
    )
    attempt = confirm_with_id(env)
    assert [d.kind for d in attempt.differences] == [DiffKind.UNRECOGNIZED]
    assert env.writer.write_calls == []


def confirm_with_id(env):
    return env.run(env.service.confirm_write, env.code, env.requester(), "1.2").value


@pytest.mark.parametrize("layout", ["a", "b"])
def test_answer_text_and_rename_do_not_block_writing(make_env, layout):
    """Scenario: US2-AS3：作答格已有其他文字、工作表改名都照常寫入。"""
    env = make_env(layout=layout)
    snap = env.reader.snapshots[KEY]
    for blank in env.world.parsed.blanks:
        snap = with_text(snap, blank.target, "老師先填的內容")
    env.reader.snapshots[KEY] = renamed(snap, "新名字")
    result = preview(env).value
    assert result.structure.ok
    assert any(i.current_display == "老師先填的內容" for i in result.snapshot.items)
    attempt = confirm(env).value
    assert attempt.status is AttemptStatus.SUCCESS
    assert len(env.writer.write_calls) == 1


def test_whole_check_completes_before_any_write(make_env):
    """Scenario: US2-AS4：寫入前先完成對全部目標的檢查，沒有「先寫一部分」。"""
    env = make_env()
    snapshot_id = preview(env).value.snapshot.snapshot_id
    reads_before = len(env.reader.calls)
    seen = {}

    def before_write():
        seen["reads"] = len(env.reader.calls) - reads_before
        seen["writes"] = len(env.writer.write_calls)

    env.writer.before_write = before_write
    attempt = env.run(
        env.service.confirm_write, env.code, env.requester(), snapshot_id
    ).value
    assert attempt.status is AttemptStatus.SUCCESS
    assert seen == {"reads": 1, "writes": 1}  # 寫入前已重新讀取一次；寫入是單一次呼叫
    assert len(env.writer.write_calls) == 1


def test_preview_marks_unconfirmable_but_still_lists_items(make_env):
    """FR-007：預覽時結構不符 → 不可確認，項目仍以匯入時位置顯示。"""
    env = make_env()
    env.reader.snapshots[KEY] = insert_row(env.reader.snapshots[KEY], 0)
    view = preview(env).value
    assert not view.structure.ok and not view.can_confirm and view.snapshot.items


def test_differences_are_capped_in_json():
    """預覽與回應的差異最多 20 筆並附其餘筆數。"""
    diffs = tuple(
        StructureDifference(DiffKind.QUESTION_NUMBER, CellRef(i, 0), "x")
        for i in range(MAX_DIFFERENCES + 5)
    )
    body = structure_json(StructureCheck(False, diffs))
    assert len(body["differences"]) == MAX_DIFFERENCES and body["moreDifferences"] == 5
    assert body["differences"][0] == {
        "kind": "QUESTION_NUMBER",
        "row": 1,
        "col": "A",
        "detail": "x",
    }
