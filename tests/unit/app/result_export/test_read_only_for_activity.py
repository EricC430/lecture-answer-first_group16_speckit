"""005 對活動唯讀（US4-AS4；SC-005）。"""

from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.result_export.models import OutcomeStatus
from tests.unit.app.result_export.world import SOURCE

KEY = (SOURCE.spreadsheet_id, SOURCE.sheet_id)


def state(env):
    activity = env.client.app.state.activity_service.get(env.code)
    return (
        activity,
        env.world.ranking.rounds,
        env.world.submissions.submissions,
        dict(env.world.winners),
    )


def run_everything(env):
    svc, code, who = env.service, env.code, env.requester()
    sid = env.run(svc.preview, code, who).value.snapshot.snapshot_id
    first = env.run(svc.confirm_write, code, who, sid).value
    env.run(svc.retry, code, who, first.attempt_id)
    env.run(svc.recheck, code, who, first.attempt_id + 1)
    env.run(svc.start_authorization, code, who)
    svc.download_csv(code, who) if hasattr(svc, "download_csv") else None


def test_activity_results_unchanged_for_every_outcome(make_env):
    """Scenario: US4-AS4：各種結果、核對、重試前後，活動與 003／004 資料深度相同。"""
    for result in (
        WriteResult(OutcomeStatus.SUCCESS, None),
        WriteResult(OutcomeStatus.FAILED, None),
        WriteResult(OutcomeStatus.PENDING, None),
    ):
        env = make_env()
        env.writer.next_result = result
        before = state(env)
        run_everything(env)
        assert state(env) == before


def test_no_mutating_calls_on_activity_or_other_features(make_env):
    """Scenario: US4-AS4：不呼叫任何 001～004 會改變狀態的方法。"""
    env = make_env()
    service = env.client.app.state.activity_service
    mutating = [
        n
        for n in dir(service)
        if n.startswith(
            (
                "replace_",
                "open_",
                "close_",
                "end_",
                "cancel",
                "finalize",
                "record_",
                "join",
                "leave",
                "delete_",
                "mark_",
            )
        )
    ]
    assert mutating, "應該找得到會改變狀態的方法"
    called = []
    for name in mutating:
        original = getattr(service, name)

        def spy(*args, __name=name, __orig=original, **kwargs):
            called.append(__name)
            return __orig(*args, **kwargs)

        setattr(service, name, spy)
    run_everything(env)
    assert called == []
