"""005 整合測試的完整世界：真實 001／002／003／004，只把 Google 換成假的。"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    FakeClock,
    ManualScheduler,
    TeacherSession,
    create_activity,
    finalize_current,
    make_app,
    submit,
)
from tests.fixtures.guided_notes_layouts import layout_a, layout_b
from tests.integration.ranking_world import close_round, post
from tests.unit.app.guided_notes_import.fakes import FakeAuthGateway, FakeSheetsReader
from tests.unit.app.result_export.fakes import FakeSheetsWriter

SHEET_FOR = {"a": 0, "b": 7}


@dataclass
class Stack:
    """一個走完整入口的測試世界（匯入走 002 的 HTTP，提交走 003，定案走 004）。"""

    client: TestClient
    teacher: TeacherSession
    reader: FakeSheetsReader
    writer: FakeSheetsWriter
    auth: FakeAuthGateway
    layout: str
    devices: dict[int, str] = field(default_factory=dict)

    @property
    def code(self) -> str:
        """活動代碼。"""
        return self.teacher.code

    def join(self, *groups: int) -> None:
        """各組加入。"""
        for group in groups:
            joined = self.client.post(
                f"/api/activities/{self.code}/groups/join", json={"groupNumber": group}
            )
            assert joined.status_code == 200, joined.text
            self.devices[group] = joined.json()["deviceToken"]

    def open_round(self, questions: list[int] | None = None) -> None:
        """開輪（預設全部未成功題）。"""
        body = {} if questions is None else {"questionNumbers": questions}
        assert post(self.client, self.teacher, "/rounds", body).status_code == 201

    def submit(self, round_number: int, question: int, group: int, answers: list[str]):
        """某組提交某題。"""
        response = submit(
            self.client,
            self.code,
            self.devices[group],
            round_number,
            question,
            answers,
        )
        assert response.status_code == 201, response.text

    def close(self) -> None:
        """關輪。"""
        close_round(self.client, self.teacher)

    def finalize(self) -> None:
        """定案目前這一輪。"""
        assert finalize_current(self.client, self.teacher).status_code == 200

    def judge(self, round_number: int, question: int, group: int, wrong: bool) -> None:
        """老師判錯或撤銷。"""
        response = self.client.put(
            f"/api/activities/{self.code}/rounds/{round_number}/questions/"
            f"{question}/groups/{group}/judgement",
            json={"wrong": wrong},
            headers=self.teacher.headers,
        )
        assert response.status_code == 200, response.text

    def export(self, method: str, path: str, body: dict | None = None):
        """呼叫 005 的端點（老師身分）。"""
        url = f"/api/activities/{self.code}/export{path}"
        if method == "GET":
            return self.client.get(url, headers=self.teacher.headers)
        return self.client.post(url, json=body or {}, headers=self.teacher.headers)

    def cell_text(self, row: int, col: int) -> str | None:
        """目前（寫回後）試算表某格的文字。"""
        from lecture_quiz.core.guided_notes_import.models import CellRef

        snapshot = self.reader.snapshots[("sheet-1", SHEET_FOR[self.layout])]
        value = snapshot.cells.get(CellRef(row, col))
        return None if value is None else value.text


@pytest.fixture
def export_stack() -> Iterator[Callable[..., Stack]]:
    """工廠：`export_stack(layout="a")`；已匯入題目並開放加入，尚未開輪。"""
    clients: list[TestClient] = []

    def factory(layout: str = "a") -> Stack:
        clock = FakeClock()
        reader = FakeSheetsReader()
        snapshot_a, _ = layout_a()
        snapshot_b, _ = layout_b()
        reader.add(
            "sheet-1", "學習單", [(0, "版面A", snapshot_a), (7, "版面B", snapshot_b)]
        )
        auth = FakeAuthGateway(authorized=True)
        writer = FakeSheetsWriter(reader)
        app = make_app(
            clock,
            ManualScheduler(),
            import_auth_gateway=auth,
            import_sheets_reader=reader,
            export_sheets_writer=writer,
        )
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        teacher = create_activity(client)
        put = client.put(
            f"/api/activities/{teacher.code}/import/source",
            json={"spreadsheetId": "sheet-1", "sheetId": SHEET_FOR[layout]},
            headers=teacher.headers,
        )
        assert put.status_code == 200, put.text
        imported = client.post(
            f"/api/activities/{teacher.code}/import", json={}, headers=teacher.headers
        )
        assert imported.status_code == 200, imported.text
        opened = post(client, teacher, "/open-joining")
        assert opened.status_code == 200, opened.text
        return Stack(client, teacher, reader, writer, auth, layout)

    yield factory
    for client in clients:
        client.__exit__(None, None, None)
