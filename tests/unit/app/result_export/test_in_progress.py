"""同一活動一次一個寫入（US4-AS6；FR-020；research R1）。"""

import asyncio

from lecture_quiz.app.result_export.models import AttemptStatus, ExportRejection


def test_concurrent_confirm_writes_once_and_lock_is_free_during_io(make_env):
    """Scenario: US4-AS6：同時送兩次確認，寫入只發生一次；I/O 期間鎖未被持有。"""
    env = make_env()
    svc, code, who = env.service, env.code, env.requester()

    async def scenario():
        sid = (await svc.preview(code, who)).value.snapshot.snapshot_id
        env.writer.gate = asyncio.Event()
        env.writer.started = asyncio.Event()
        first = asyncio.create_task(svc.confirm_write(code, who, sid))
        await env.writer.started.wait()
        assert not env.store.lock(code).locked(), "Google I/O 期間不得持有鎖"
        second = await svc.confirm_write(code, who, sid)
        retry = await svc.retry(code, who, 1)
        recheck = await svc.recheck(code, who, 1)
        preview = await svc.preview(code, who)  # 預覽不被卡住
        env.writer.gate.set()
        done = await first
        return second, retry, recheck, preview, done

    second, retry, recheck, preview, done = env.run(scenario)
    assert len(env.writer.write_calls) == 1
    assert second.ok and second.value.already_in_progress is True
    assert second.value.status is AttemptStatus.IN_PROGRESS
    assert second.value.attempt_id == done.value.attempt_id
    assert retry.rejection is ExportRejection.WRITE_IN_PROGRESS
    assert recheck.rejection is ExportRejection.WRITE_IN_PROGRESS
    assert preview.ok
    assert done.value.status is AttemptStatus.SUCCESS
    assert env.publisher.lock_held and not any(env.publisher.lock_held)
