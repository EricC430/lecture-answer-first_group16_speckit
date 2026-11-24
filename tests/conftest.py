"""全專案共用的測試工具（研究 R4）。

- `FakeClock`：可手動前進的時鐘，取代系統時鐘。
- `ManualScheduler`：手動觸發的倒數排程（001）。
- `make_app`：以指定時鐘、排程建立 app 的工廠。
- fixture：`fake_clock`、`manual_scheduler`、`client`、`teacher`（001）。
- `FakeQuestionShapeSource`：每題子空格數的假來源（003；`make_app` 預設使用）。
- `seed_questions(..., blanks=...)`：放入題目時一併設定每題格數（003）。
- `submit(...)`：以 HTTP 送出答案（003）。

子功能專屬的工具請追加在本檔最後，或放在各自測試目錄的 conftest.py。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lecture_quiz.main import create_app

TAIPEI = timezone(timedelta(hours=8))
FAKE_CLOCK_START = datetime(2026, 11, 21, 9, 0, 0, tzinfo=TAIPEI)


class FakeClock:
    """測試用時鐘：`now()` 回傳固定時間，只有呼叫 `advance` 才會前進。"""

    def __init__(self, start: datetime = FAKE_CLOCK_START) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock 的起點必須有時區")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> datetime:
        self._now += timedelta(seconds=seconds)
        return self._now


class ManualScheduler:
    """測試用倒數排程：只記錄排程，`fire(code)` 時才以截止時間呼叫回呼。

    即使排程已被取消，`fire` 仍會以最後一次排程的截止時間觸發，
    用來模擬「取消來不及、計時器仍然觸發」的競爭情況（SC-003）。
    """

    def __init__(self) -> None:
        self.scheduled: dict[str, datetime] = {}
        self.last_deadline: dict[str, datetime] = {}
        self.cancelled: list[str] = []
        self._callback = None

    def set_callback(self, callback) -> None:
        self._callback = callback

    def schedule(self, code: str, deadline: datetime) -> None:
        self.scheduled[code] = deadline
        self.last_deadline[code] = deadline

    def cancel(self, code: str) -> None:
        self.scheduled.pop(code, None)
        self.cancelled.append(code)

    async def fire(self, code: str) -> None:
        assert self._callback is not None
        await self._callback(code, self.last_deadline[code])


class FakeQuestionShapeSource:
    """測試用的每題子空格數來源（003 的 `QuestionShapeSource`）。"""

    def __init__(self) -> None:
        self.shapes: dict[str, dict[int, int]] = {}

    def set(self, code: str, blanks: dict[int, int]) -> None:
        self.shapes[code] = dict(blanks)

    def blanks_per_question(self, code: str):
        return self.shapes.get(code)


def make_app(
    clock: FakeClock | None = None,
    scheduler: ManualScheduler | None = None,
    **kwargs: Any,
) -> FastAPI:
    """以 FakeClock、ManualScheduler 建立 app。

    沒有指定 `question_shape_source`、也沒有注入 002 的 `import_sheets_reader` 時，
    預設用 `FakeQuestionShapeSource`（003 測試自己設定格數）；注入了 002 的讀取器，
    就走真實的 `ImportService`，格數來自真正的匯入結果。
    """
    if "import_sheets_reader" not in kwargs:
        kwargs.setdefault("question_shape_source", FakeQuestionShapeSource())
    return create_app(
        clock=clock if clock is not None else FakeClock(),
        scheduler=scheduler if scheduler is not None else ManualScheduler(),
        **kwargs,
    )


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def manual_scheduler() -> ManualScheduler:
    return ManualScheduler()


@pytest.fixture
def client(
    fake_clock: FakeClock, manual_scheduler: ManualScheduler
) -> Iterator[TestClient]:
    with TestClient(make_app(fake_clock, manual_scheduler)) as test_client:
        yield test_client


@dataclass
class TeacherSession:
    """建立活動後的老師身分。"""

    code: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def create_activity(client: TestClient, max_groups: int = 6) -> TeacherSession:
    response = client.post("/api/activities", json={"maxGroups": max_groups})
    assert response.status_code == 201, response.text
    body = response.json()
    return TeacherSession(body["code"], body["teacherToken"])


def create_joinable(client: TestClient, max_groups: int = 6) -> TeacherSession:
    """建立活動、放入題目並開放加入；回傳老師身分（學生之後才能加入）。"""
    session = create_activity(client, max_groups)
    open_joining(client, session)
    return session


@pytest.fixture
def teacher(client: TestClient) -> TeacherSession:
    return create_activity(client)


def service_of(client: TestClient):
    """取得 app 內的 ActivityService。"""
    return client.app.state.activity_service


def call(client: TestClient, fn, *args, **kwargs):
    """在 TestClient 的事件迴圈中呼叫非同步函式（與 HTTP、WebSocket 共用）。"""

    async def runner():
        return await fn(*args, **kwargs)

    return client.portal.call(runner)


def seed_questions(
    client: TestClient,
    teacher: TeacherSession,
    count: int = 4,
    blanks: list[int] | None = None,
) -> None:
    """以 replace_questions 放入題號 1..count（研究 R8：自動化測試直接呼叫服務）.

    `blanks` 為各題子空格數（003）；省略時不設定格數（001 的測試不受 003 快照欄位
    影響）。只有 app 使用 `FakeQuestionShapeSource` 時才會設定。
    """
    if blanks is not None:
        assert len(blanks) == count
    shapes = client.app.state.question_shape_source
    if blanks is not None and isinstance(shapes, FakeQuestionShapeSource):
        shapes.set(teacher.code, {n: blanks[n - 1] for n in range(1, count + 1)})
    service = service_of(client)
    requester = service.resolve_requester(teacher.code, teacher.token)
    outcome = call(
        client,
        service.replace_questions,
        teacher.code,
        requester,
        tuple(range(1, count + 1)),
    )
    assert outcome.ok, outcome


def open_joining(
    client: TestClient, teacher: TeacherSession, question_count: int = 4
) -> None:
    """放入題目並開放加入（準備中 → 開放加入），之後學生才能加入。"""
    seed_questions(client, teacher, question_count)
    response = client.post(
        f"/api/activities/{teacher.code}/open-joining",
        json={},
        headers=teacher.headers,
    )
    assert response.status_code == 200, response.text


def join_group(
    client: TestClient, code: str, number: int, credential: str | None = None
) -> str:
    """以 HTTP 加入組別並回傳裝置 token（US2）。"""
    response = client.post(
        f"/api/activities/{code}/groups/join",
        json={"groupNumber": number, "credential": credential},
    )
    assert response.status_code == 200, response.text
    return response.json()["deviceToken"]


# ── 002-guided-notes-import：只追加，不改 001 既有 fixture 的預設行為 ──


@pytest.fixture
def fake_auth_gateway():
    """002 的測試替身：授權連接埠（預設已授權；不連 Google）。"""
    from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway

    return FakeAuthGateway(authorized=True)


@pytest.fixture
def fake_sheets_reader():
    """002 的測試替身：Sheets 讀取連接埠，含版面 A、版面 B 與單一工作表試算表。"""
    from tests.fixtures.guided_notes_layouts import layout_a, layout_b
    from tests.unit.app.guided_notes_import.fakes import FakeSheetsReader

    reader = FakeSheetsReader()
    snapshot_a, _ = layout_a()
    snapshot_b, _ = layout_b()
    reader.add(
        "sheet-1", "學習單", [(0, "版面A", snapshot_a), (7, "版面B", snapshot_b)]
    )
    reader.add("single-sheet", "只有一張", [(0, "唯一", snapshot_a)])
    return reader


@pytest.fixture
def import_client(
    fake_clock: FakeClock,
    manual_scheduler: ManualScheduler,
    fake_auth_gateway,
    fake_sheets_reader,
) -> Iterator[TestClient]:
    """使用 001 真實 ActivityService、只把 Google 連接埠換成 Fake 的 TestClient。"""
    app = make_app(
        fake_clock,
        manual_scheduler,
        import_auth_gateway=fake_auth_gateway,
        import_sheets_reader=fake_sheets_reader,
    )
    with TestClient(app) as test_client:
        yield test_client


def submit(
    client: TestClient,
    code: str,
    device_token: str,
    round_number: object,
    question_number: object,
    answers: object,
    **extra: Any,
):
    """以 HTTP 送出答案（003）；回傳 response。"""
    body = {
        "roundNumber": round_number,
        "questionNumber": question_number,
        "answers": answers,
        **extra,
    }
    return client.post(
        f"/api/activities/{code}/submissions",
        json=body,
        headers={"Authorization": f"Bearer {device_token}"},
    )
