"""應用層測試的共用 fixture。"""

import pytest

from lecture_quiz.app.guided_notes_import.service import ImportService
from lecture_quiz.app.guided_notes_import.store import ImportStore
from tests.conftest import FakeClock
from tests.fixtures.guided_notes_layouts import layout_a, layout_b
from tests.unit.app.guided_notes_import.fakes import (
    FakeActivityGateway,
    FakeAuthGateway,
    FakeSheetsReader,
)

CODE = "ABC234"
SPREADSHEET = "sheet-1"


@pytest.fixture
def activity() -> FakeActivityGateway:
    gateway = FakeActivityGateway()
    gateway.add_activity(CODE)
    return gateway


@pytest.fixture
def auth() -> FakeAuthGateway:
    return FakeAuthGateway(authorized=True)


@pytest.fixture
def reader() -> FakeSheetsReader:
    fake = FakeSheetsReader()
    snapshot_a, _ = layout_a()
    snapshot_b, _ = layout_b()
    fake.add(
        SPREADSHEET, "學習單", [(0, "版面A", snapshot_a), (7, "版面B", snapshot_b)]
    )
    fake.add("single-sheet", "只有一張", [(0, "唯一", snapshot_a)])
    return fake


@pytest.fixture
def store() -> ImportStore:
    return ImportStore()


@pytest.fixture
def service(
    auth: FakeAuthGateway,
    reader: FakeSheetsReader,
    activity: FakeActivityGateway,
    store: ImportStore,
) -> ImportService:
    return ImportService(auth, reader, activity, store, FakeClock())
