"""ExportService.preview（US1）。"""

import dataclasses

from lecture_quiz.app.result_export.models import ExportRejection
from lecture_quiz.core.result_export.models import OverwriteImpact
from tests.conftest import create_activity
from tests.unit.app.result_export.world import DEFAULT_PLAN


def preview(env, requester=None):
    return env.run(env.service.preview, env.code, requester or env.requester())


def test_round_in_progress_preview_has_only_finalized_history(make_env):
    """Scenario: US1-AS1：第二輪仍在搶答時，預覽只含已定案成果，不含暫時提交。"""
    env = make_env(stage="ROUND_OPEN")
    result = preview(env)
    assert result.ok
    snapshot = result.value.snapshot
    winners = env.world.winners
    assert {i.question_number for i in snapshot.items} == set(winners)
    assert 4 in snapshot.unwritten_questions  # 未定案輪次的暫時提交不算
    assert all(i.round_number in (1, 2) for i in snapshot.items)


def test_preview_fields_and_plain_text_answers(make_env):
    """Scenario: US1-AS2：欄位完整；含 HTML 標記的答案原樣保留（前端 textContent）。"""
    env = make_env()
    q = 3
    rnd, group, answers = env.world.winners[q]
    html = "<script>alert(1)</script>"
    env.world.submissions.submissions = tuple(
        dataclasses.replace(s, answers=(html, *s.answers[1:]))
        if (s.round_number, s.question_number, s.group_number) == (rnd, q, group)
        else s
        for s in env.world.submissions.submissions
    )
    result = preview(env)
    item = next(i for i in result.value.snapshot.items if i.question_number == q)
    assert item.answer == html and item.group_number == group
    assert item.impact is OverwriteImpact.EMPTY
    assert result.value.structure.ok and result.value.sheet_title
    assert result.value.snapshot.unwritten_questions == (4,)


def test_preview_does_not_write_or_change_anything(make_env):
    """預覽只讀取：不寫 Google、不新增嘗試。"""
    env = make_env()
    preview(env)
    assert env.writer.write_calls == [] and env.store.latest(env.code) is None


def test_no_winners_means_no_results_and_no_write(make_env):
    """Scenario: US1-AS4（沒有可寫回答案）：回 NO_RESULTS，不送出外部寫入。"""
    env = make_env(plan=())
    result = preview(env)
    assert not result.ok and result.rejection is ExportRejection.NO_RESULTS
    assert env.writer.write_calls == []


def test_all_unsolved_finalized_round_is_no_results(make_env):
    """Scenario: US1-AS4：已定案但全是無人成功也回 NO_RESULTS。"""
    env = make_env(plan=((1, 2, 2, None, True),))
    assert preview(env).rejection is ExportRejection.NO_RESULTS


def test_preparing_and_joining_have_no_results(make_env):
    """準備中與開放加入尚無定案成果 → NO_RESULTS（C2：不需要匯入記錄）。"""
    for stage in ("PREPARING", "JOINING"):
        env = make_env(stage=stage, plan=())
        env.records.records.clear()  # 這時可能還沒有匯入記錄
        assert preview(env).rejection is ExportRejection.NO_RESULTS


def test_missing_import_record_with_results_is_reported(make_env):
    """有定案成果卻取不到匯入記錄 → NO_IMPORT_RECORD。"""
    env = make_env()
    env.records.records.clear()
    assert preview(env).rejection is ExportRejection.NO_IMPORT_RECORD


def test_non_teacher_is_rejected_without_teacher_data(make_env):
    """Scenario: US1-AS5：學生、其他活動的老師、匿名都被拒絕，回傳不含老師專用資料。"""
    env = make_env()
    other = create_activity(env.client)
    service = env.client.app.state.activity_service
    for requester in (
        env.student(),
        service.resolve_requester(env.code, other.token),
        service.resolve_requester(env.code, None),
    ):
        result = preview(env, requester)
        assert not result.ok and result.rejection is ExportRejection.NOT_TEACHER
        assert result.value is None
    assert env.reader.calls == []


def test_cancelled_activity_is_rejected_without_external_calls(make_env):
    """Scenario: US1-AS7：已取消的活動拒絕，不送出任何外部請求。"""
    env = make_env(stage="CANCELLED", plan=())
    result = preview(env)
    assert result.rejection is ExportRejection.ACTIVITY_CANCELLED
    assert env.reader.calls == [] and env.writer.read_calls == 0
    assert env.writer.write_calls == []


def test_default_plan_is_what_we_think():
    assert len(DEFAULT_PLAN) == 7
