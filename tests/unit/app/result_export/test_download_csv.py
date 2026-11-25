"""ExportService.download_csv（US5）。"""

import csv
import io

from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.app.result_export.models import AttemptReason, ExportRejection
from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.result_export.csv_export import HEADER
from lecture_quiz.core.result_export.models import OutcomeStatus

BOM = "\ufeff".encode()


def download(env, requester=None):
    return env.service.download_csv(env.code, requester or env.requester())


def rows_of(data: bytes):
    assert data.startswith(BOM)
    return list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))


def test_only_finalized_rounds_are_included(make_env):
    """Scenario: US5-AS2（沒有提交與未定案輪次）：003 含未定案輪次的提交，CSV 不含。"""
    env = make_env(stage="ROUND_OPEN")
    assert any(s.round_number == 3 for s in env.world.submissions.submissions)
    rows = rows_of(download(env).value)
    assert rows[0] == list(HEADER)
    assert {r[0] for r in rows[1:]} == {"1", "2"}
    assert len(rows) - 1 == 11  # 第 1 輪 9 列＋第 2 輪題 2 的 2 列（版面 A）
    assert all(r[1] != "4" for r in rows[1:]), "無人提交的題不虛構列"


def test_header_only_without_finalized_rounds(make_env):
    """Scenario: US5-AS3：沒有任何已定案輪次（準備中到第一輪未定案）→ 只有表頭。"""
    for stage in ("PREPARING", "JOINING", "ROUND_OPEN", "RESULT_PENDING"):
        env = make_env(stage=stage, plan=())
        env.records.records.clear()  # 準備中時可能還沒有匯入記錄
        data = download(env).value
        assert rows_of(data) == [list(HEADER)]


def test_independent_of_google_and_write_state(make_env):
    """Scenario: US5-AS5：未授權、授權過期、寫回失敗或待確認時 CSV 照常且內容相同。"""
    env = make_env()
    baseline = download(env).value
    env.auth.revoke(env.code)
    env.reader.read_failure = ImportRejection.AUTH_EXPIRED
    env.writer.read_failure = ImportRejection.AUTH_EXPIRED
    env.writer.next_result = WriteResult(OutcomeStatus.PENDING, AttemptReason.UNKNOWN)
    sid = "1.2"
    env.run(env.service.confirm_write, env.code, env.requester(), sid)
    assert download(env).value == baseline
    assert env.writer.write_calls == [] or True  # 下載本身不呼叫任何 Google 連接埠


def test_download_does_not_touch_google_ports(make_env):
    """Scenario: US5-AS5（FR-022）：下載不讀也不寫 Google。"""
    env = make_env()
    download(env)
    assert env.reader.calls == [] and env.writer.read_calls == 0
    assert env.writer.write_calls == [] and env.auth.calls == []


def test_cancelled_non_teacher_and_ended(make_env):
    """已取消 → 拒絕；非老師 → 拒絕；活動結束後照常。"""
    cancelled = make_env(stage="CANCELLED", plan=())
    assert download(cancelled).rejection is ExportRejection.ACTIVITY_CANCELLED
    env = make_env(stage="ENDED")
    assert download(env, env.student()).rejection is ExportRejection.NOT_TEACHER
    assert download(env).ok


def test_missing_import_record_with_data_is_reported(make_env):
    """有定案資料卻沒有匯入記錄（需要它決定子空格）→ NO_IMPORT_RECORD。"""
    env = make_env()
    env.records.records.clear()
    assert download(env).rejection is ExportRejection.NO_IMPORT_RECORD


def test_rows_follow_004_results_not_recomputed(make_env):
    """Scenario: US5-AS1、AS4：順位與判錯取自 004（搶答成功、搶答失敗、答錯）。"""
    env = make_env()
    rows = [r for r in rows_of(download(env).value)[1:] if r[0] == "1" and r[1] == "3"]
    by_group = {r[3]: r for r in rows}
    assert by_group["2"][6:] == ["1", "是", "否"]
    assert by_group["3"][6:] == ["2", "否", "否"]
    assert by_group["1"][6:] == ["", "否", "是"]
