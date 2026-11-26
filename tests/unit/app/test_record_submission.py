"""001 為 003 新增的 `ActivityService.record_submission`（003 研究 R2）。

鎖內順序：找裝置 → 取一次 now → 組 SubmissionWindow → handler.decide →
（accept 時）套用 RecordSubmission → handler.commit；鎖外推送。
"""

import asyncio
import dataclasses
from datetime import timedelta

from lecture_quiz.app.activity.ports import HandlerStep, SubmissionWindow
from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.secrets_gen import new_browser_key
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import RejectionReason
from tests.conftest import FakeClock, ManualScheduler


class RecordingPublisher:
    def __init__(self, registry: ActivityRegistry):
        self.registry = registry
        self.published = []
        self.locked_during_publish = []

    async def publish(self, activity):
        self.locked_during_publish.append(self.registry.lock(activity.code).locked())
        self.published.append(activity)

    async def disconnect_device(self, code, token_hash, reason):
        pass


class CountingClock(FakeClock):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def now(self):
        self.calls += 1
        return super().now()


class Handler:
    """可設定回應的 handler；記錄被呼叫的參數與 commit 時的鎖狀態。"""

    def __init__(self, registry, code, kind="accept"):
        self.registry = registry
        self.code = code
        self.kind = kind
        self.decided = []
        self.committed = []

    def decide(self, window, now):
        self.decided.append((window, now))
        if self.kind == "accept":
            return HandlerStep.accept("value")
        return HandlerStep.no_change("value")

    def commit(self):
        self.committed.append(self.registry.lock(self.code).locked())


async def _setup(countdown=60):
    registry = ActivityRegistry()
    clock = CountingClock()
    publisher = RecordingPublisher(registry)
    service = ActivityService(registry, clock, ManualScheduler(), publisher)
    created = (await service.create(4)).value
    code = created.code
    teacher = service.resolve_requester(code, created.teacher_token)
    assert (await service.replace_questions(code, teacher, (1, 2, 3))).ok
    assert (await service.open_joining(code, teacher)).ok
    device = new_browser_key()
    assert (await service.join(code, 2, browser_key=device)).ok
    assert (await service.open_round(code, teacher, None, False, countdown)).ok
    publisher.published.clear()
    publisher.locked_during_publish.clear()
    return service, registry, clock, publisher, code, teacher, device


def test_gone_and_not_in_group_do_not_call_handler():
    async def scenario():
        service, registry, _, _, code, _, token = await _setup()
        handler = Handler(registry, code)
        gone = await service.record_submission("ZZZZZZ", token, handler)
        stranger = await service.record_submission(code, "not-a-token", handler)
        return gone, stranger, handler

    gone, stranger, handler = asyncio.run(scenario())
    assert gone.rejection is RejectionReason.ACTIVITY_GONE
    assert stranger.rejection is RejectionReason.NOT_IN_GROUP
    assert handler.decided == [] and handler.committed == []


def test_window_and_single_now():
    async def scenario():
        service, registry, clock, _, code, _, token = await _setup(countdown=60)
        clock.advance(10)
        handler = Handler(registry, code, kind="no_change")
        clock.calls = 0
        outcome = await service.record_submission(code, token, handler)
        return outcome, handler, clock

    outcome, handler, clock = asyncio.run(scenario())
    assert clock.calls == 1
    ((window, now),) = handler.decided
    assert now == clock.now()
    assert isinstance(window, SubmissionWindow)
    assert window.group_number == 2
    assert window.stage is Stage.ROUND_OPEN
    assert window.round_number == 1
    assert window.open_questions == (1, 2, 3)
    assert window.deadline == clock.now() - timedelta(seconds=10) + timedelta(
        seconds=60
    )
    assert window.accepting is True
    assert outcome.ok and outcome.value == "value"


def test_window_not_accepting_after_deadline_or_close():
    async def scenario():
        service, registry, clock, _, code, teacher, token = await _setup(countdown=60)
        clock.advance(60)
        at_deadline = Handler(registry, code, kind="no_change")
        await service.record_submission(code, token, at_deadline)
        service2, registry2, _, _, code2, teacher2, token2 = await _setup(None)
        await service2.close_round(code2, teacher2)
        closed = Handler(registry2, code2, kind="no_change")
        await service2.record_submission(code2, token2, closed)
        return at_deadline, closed

    at_deadline, closed = asyncio.run(scenario())
    assert at_deadline.decided[0][0].accepting is False
    window = closed.decided[0][0]
    assert window.accepting is False
    assert window.stage is Stage.RESULT_PENDING
    assert window.round_number == 1
    assert window.open_questions == ()


def test_accept_marks_then_commits_inside_lock_and_publishes_once():
    async def scenario():
        service, registry, _, publisher, code, _, token = await _setup()
        before = registry.get(code)
        handler = Handler(registry, code)
        outcome = await service.record_submission(code, token, handler)
        return before, registry.get(code), handler, publisher, outcome

    before, after, handler, publisher, outcome = asyncio.run(scenario())
    assert outcome.ok and outcome.value == "value"
    assert handler.committed == [True]
    assert after.groups[2].has_submissions
    assert after.revision == before.revision + 1
    assert after.version == before.version
    assert len(publisher.published) == 1
    assert publisher.locked_during_publish == [False]


def test_no_change_does_not_commit_or_publish():
    async def scenario():
        service, registry, _, publisher, code, _, token = await _setup()
        before = registry.get(code)
        handler = Handler(registry, code, kind="no_change")
        outcome = await service.record_submission(code, token, handler)
        return before, registry.get(code), handler, publisher, outcome

    before, after, handler, publisher, outcome = asyncio.run(scenario())
    assert outcome.ok and outcome.value == "value"
    assert handler.committed == []
    assert after == before
    assert publisher.published == []


def test_rejected_record_does_not_commit():
    """handler 強制 accept，但截止已過：RecordSubmission 被拒，不 commit、不推送。"""

    async def scenario():
        service, registry, clock, publisher, code, _, token = await _setup(60)
        activity = registry.get(code)
        expired = dataclasses.replace(
            activity.current_round.rules,
            deadline=clock.now() - timedelta(seconds=1),
        )
        rounds = activity.rounds[:-1] + (
            dataclasses.replace(activity.current_round, rules=expired),
        )
        registry.put(dataclasses.replace(activity, rounds=rounds))
        handler = Handler(registry, code)
        outcome = await service.record_submission(code, token, handler)
        return handler, publisher, outcome

    handler, publisher, outcome = asyncio.run(scenario())
    assert not outcome.ok
    assert outcome.rejection is RejectionReason.STAGE_NOT_ALLOWED
    assert handler.committed == []
    assert publisher.published == []
