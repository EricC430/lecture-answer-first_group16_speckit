"""005 服務層測試工具：真 ActivityService（閘門）＋假的 002／003／004／Google。"""

from collections.abc import Callable
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from lecture_quiz.app.result_export.service import ExportService
from lecture_quiz.app.result_export.store import ExportStore
from tests.conftest import (
    FakeClock,
    ManualScheduler,
    TeacherSession,
    create_activity,
    finalize_current,
    make_app,
    open_joining,
)
from tests.integration.ranking_world import close_round, post
from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway, FakeSheetsReader
from tests.unit.app.result_export.fakes import (
    FakeImportRecords,
    FakeSheetsWriter,
    RecordingPublisher,
)
from tests.unit.app.result_export.world import DEFAULT_PLAN, SOURCE, World, build_world

STAGES = [
    "PREPARING",
    "JOINING",
    "ROUND_OPEN",
    "RESULT_PENDING",
    "RESULT_FINAL",
    "ENDED",
    "CANCELLED",
]


def drive_to(client: TestClient, teacher: TeacherSession, stage: str) -> None:
    """用 HTTP 把真實活動帶到指定階段（只影響 001 的閘門，與假資料無關）。"""
    if stage == "PREPARING":
        return
    if stage == "CANCELLED":
        assert post(client, teacher, "/cancel").status_code == 200
        return
    open_joining(client, teacher)
    if stage == "JOINING":
        return
    joined = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 1}
    )
    assert joined.status_code == 200, joined.text
    assert post(client, teacher, "/rounds").status_code == 201
    if stage == "ROUND_OPEN":
        return
    close_round(client, teacher)
    if stage == "RESULT_PENDING":
        return
    assert finalize_current(client, teacher).status_code == 200
    if stage == "ENDED":
        assert post(client, teacher, "/end").status_code == 200


@dataclass
class Env:
    """一個 005 測試環境。"""

    client: TestClient
    teacher: TeacherSession
    service: ExportService
    writer: FakeSheetsWriter
    reader: FakeSheetsReader
    records: FakeImportRecords
    auth: FakeAuthGateway
    publisher: RecordingPublisher
    store: ExportStore
    world: World
    clock: FakeClock

    @property
    def code(self) -> str:
        """活動代碼。"""
        return self.teacher.code

    def requester(self, token: str | None = None):
        """以 token 解析身分（預設老師）。"""
        return self.client.app.state.activity_service.resolve_requester(
            self.code, token or self.teacher.token
        )

    def student(self):
        """一個非老師的身分。"""
        return self.client.app.state.activity_service.resolve_requester(
            self.code, "not-a-teacher-token"
        )

    def run(self, fn, *args, **kwargs):
        """在 TestClient 的事件迴圈中執行 async 方法。"""

        async def runner():
            return await fn(*args, **kwargs)

        return self.client.portal.call(runner)


@pytest.fixture
def make_env() -> Callable[..., Env]:
    """工廠 fixture：`make_env(layout, stage, plan, with_writer)`。"""
    clients: list[TestClient] = []

    def factory(
        layout: str = "a",
        stage: str = "RESULT_FINAL",
        plan: tuple = DEFAULT_PLAN,
        with_writer: bool = True,
    ) -> Env:
        clock = FakeClock()
        app = make_app(clock, ManualScheduler())
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        teacher = create_activity(client)
        drive_to(client, teacher, stage)
        world = build_world(layout, plan, code=teacher.code)
        reader = FakeSheetsReader()
        snapshot = world.parsed.snapshot
        reader.add(
            SOURCE.spreadsheet_id,
            "試算表",
            [(SOURCE.sheet_id, snapshot.sheet_name, snapshot)],
        )
        records = FakeImportRecords({teacher.code: world.record})
        writer = FakeSheetsWriter(reader)
        auth = FakeAuthGateway(authorized=True)
        publisher = RecordingPublisher()
        store = ExportStore()
        service = ExportService(
            activity=app.state.activity_service,
            imports=records,
            auth=auth,
            reader=reader,
            writer=writer if with_writer else None,
            submissions=world.submissions,
            ranking=world.ranking,
            store=store,
            publisher=publisher,
            clock=clock,
        )
        publisher.lock_probe = lambda: store.lock(teacher.code).locked()
        return Env(
            client,
            teacher,
            service,
            writer,
            reader,
            records,
            auth,
            publisher,
            store,
            world,
            clock,
        )

    yield factory
    for client in clients:
        client.__exit__(None, None, None)
