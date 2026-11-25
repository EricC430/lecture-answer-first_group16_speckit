"""003 應用層測試共用：建立「已開輪」的活動與服務。"""

from dataclasses import dataclass

from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.secrets_gen import new_browser_key
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.round_submission.service import SubmissionService
from lecture_quiz.app.round_submission.store import SubmissionStore
from tests.conftest import FakeClock, FakeQuestionShapeSource, ManualScheduler


class RecordingPublisher:
    """記錄每次推送的活動。"""

    def __init__(self):
        self.published = []

    async def publish(self, activity):
        self.published.append(activity)

    async def disconnect_device(self, code, token_hash, reason):
        pass


@dataclass
class World:
    """一個已開輪的活動：老師、兩組（各一台裝置）與服務。"""

    activities: ActivityService
    submissions: SubmissionService
    store: SubmissionStore
    shapes: FakeQuestionShapeSource
    clock: FakeClock
    publisher: RecordingPublisher
    code: str
    teacher: object
    devices: dict


async def open_world(
    blanks=(2, 2, 1, 1), countdown=None, groups=(1, 2), devices_per_group=1
) -> World:
    """建立活動、放入題目與格數、開放加入、各組加入、開第 1 輪。"""
    registry = ActivityRegistry()
    clock = FakeClock()
    publisher = RecordingPublisher()
    activities = ActivityService(registry, clock, ManualScheduler(), publisher)
    shapes = FakeQuestionShapeSource()
    store = SubmissionStore()
    submissions = SubmissionService(activities, store, shapes)
    created = (await activities.create(6)).value
    code = created.code
    teacher = activities.resolve_requester(code, created.teacher_token)
    numbers = tuple(range(1, len(blanks) + 1))
    assert (await activities.replace_questions(code, teacher, numbers)).ok
    shapes.set(code, dict(zip(numbers, blanks, strict=True)))
    assert (await activities.open_joining(code, teacher)).ok
    devices: dict[int, list[str]] = {}
    for group in groups:
        first_key = new_browser_key()
        first = (await activities.join(code, group, browser_key=first_key)).value
        tokens = [first_key]
        for _ in range(devices_per_group - 1):
            key = new_browser_key()
            more = await activities.join(code, group, first.credential, browser_key=key)
            assert more.ok, more
            tokens.append(key)
        devices[group] = tokens
    assert (await activities.open_round(code, teacher, None, False, countdown)).ok
    publisher.published.clear()
    return World(
        activities, submissions, store, shapes, clock, publisher, code, teacher, devices
    )
