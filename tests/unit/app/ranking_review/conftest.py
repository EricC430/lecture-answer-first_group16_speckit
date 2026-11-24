"""004 應用層測試共用：真 `ActivityService` + `FakeClock` + 假的 `SubmissionReader`。

- `FakeSubmissionReader`：實作 003 的 `SubmissionReader`，回傳預先設定的提交。
- `RecordingPublisher`：記錄推送次數，並記錄呼叫當下該活動的 004 鎖是否被持有。
- `ranking_world()`：建立活動、題號、開放加入、各組加入、開輪（可指定公平模式），
  `world.close()` 關輪進入「結果未定案」。
"""

from dataclasses import dataclass, field
from datetime import timedelta

from lecture_quiz.app.activity.registry import ActivityRegistry
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.app.ranking_review.service import RankingService
from lecture_quiz.app.ranking_review.store import ReviewStore
from lecture_quiz.core.round_submission.models import Submission
from tests.conftest import FAKE_CLOCK_START, FakeClock, ManualScheduler


class FakeSubmissionReader:
    """假的 `SubmissionReader`：依（活動代碼, 輪次）回傳預先設定的提交。"""

    def __init__(self) -> None:
        self._rounds: dict[tuple[str, int], tuple[Submission, ...]] = {}

    def set(self, code: str, round_number: int, subs: list[Submission]) -> None:
        """設定某輪的提交（會依（接收時間, 序號）排序）。"""
        ordered = sorted(subs, key=lambda s: (s.received_at, s.sequence))
        self._rounds[(code, round_number)] = tuple(ordered)

    def round_submissions(self, code: str, round_number: int) -> tuple[Submission, ...]:
        """某一輪的全部有效提交。"""
        return self._rounds.get((code, round_number), ())

    def all_submissions(self, code: str) -> tuple[Submission, ...]:
        """全部輪次的有效提交。"""
        out: list[Submission] = []
        for (c, _), subs in sorted(self._rounds.items()):
            if c == code:
                out.extend(subs)
        return tuple(out)


def make_sub(
    code: str,
    group: int,
    question: int,
    second: float,
    seq: int,
    *,
    round_number: int = 1,
    answers: tuple[str, ...] = ("答案",),
) -> Submission:
    """一筆 003 的 `Submission`：接收時間為固定起點加 `second` 秒。"""
    return Submission(
        activity_code=code,
        round_number=round_number,
        question_number=question,
        group_number=group,
        answers=answers,
        received_at=FAKE_CLOCK_START + timedelta(seconds=second),
        sequence=seq,
    )


class RecordingPublisher:
    """記錄每次推送的活動，以及呼叫當下 004 的鎖是否被持有。"""

    def __init__(self) -> None:
        self.published: list[object] = []
        self.lock_held_during_publish: list[bool] = []
        self.store: ReviewStore | None = None
        self.fail = False

    async def publish(self, activity) -> None:
        """記錄推送；`fail=True` 時拋例外（測試推送失敗不影響狀態）。"""
        if self.store is not None:
            self.lock_held_during_publish.append(
                self.store.lock(activity.code).locked()
            )
        self.published.append(activity)
        if self.fail:
            raise RuntimeError("push failed")

    async def disconnect_device(self, code, token_hash, reason) -> None:
        """不使用。"""


@dataclass
class RankingWorld:
    """一個活動：老師、各組、001 服務、004 服務與假的提交來源。"""

    activities: ActivityService
    ranking: RankingService
    reader: FakeSubmissionReader
    store: ReviewStore
    publisher: RecordingPublisher
    clock: FakeClock
    code: str
    teacher: object
    groups: tuple[int, ...]
    devices: dict[int, str] = field(default_factory=dict)

    async def close(self) -> None:
        """老師關輪（目前輪次進入「結果未定案」）。"""
        assert (await self.activities.close_round(self.code, self.teacher)).ok
        self.publisher.published.clear()
        self.publisher.lock_held_during_publish.clear()

    def student(self, group: int):
        """某組學生裝置的身分。"""
        return self.activities.resolve_requester(self.code, self.devices[group])


async def ranking_world(
    *, questions: int = 4, groups: tuple[int, ...] = (1, 2, 3), fair: bool = False
) -> RankingWorld:
    """建立活動、題號、開放加入、各組加入並開第 1 輪（尚未關輪）。"""
    registry = ActivityRegistry()
    clock = FakeClock()
    publisher = RecordingPublisher()
    activities = ActivityService(registry, clock, ManualScheduler(), publisher)
    reader = FakeSubmissionReader()
    store = ReviewStore()
    publisher.store = store
    ranking = RankingService(activities, reader, store, publisher)
    created = (await activities.create(6)).value
    code = created.code
    teacher = activities.resolve_requester(code, created.teacher_token)
    numbers = tuple(range(1, questions + 1))
    assert (await activities.replace_questions(code, teacher, numbers)).ok
    assert (await activities.open_joining(code, teacher)).ok
    devices: dict[int, str] = {}
    for group in groups:
        joined = (await activities.join(code, group)).value
        devices[group] = joined.device_token
    assert (await activities.open_round(code, teacher, None, fair, None)).ok
    publisher.published.clear()
    return RankingWorld(
        activities,
        ranking,
        reader,
        store,
        publisher,
        clock,
        code,
        teacher,
        groups,
        devices,
    )
