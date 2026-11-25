"""005 在 create_app 的組裝（共用基礎）。"""

from fastapi.testclient import TestClient

from lecture_quiz.app.result_export.service import ExportService
from tests.conftest import make_app


def test_export_service_is_wired():
    app = make_app()
    assert isinstance(app.state.export_service, ExportService)


def test_injected_sheets_writer_is_used():
    class Marker:
        pass

    marker = Marker()
    app = make_app(export_sheets_writer=marker)
    assert app.state.export_service._writer is marker


def test_real_writer_is_wired_without_building_google_clients():
    """A1、T047：預設用真實寫入器共用 002 的授權閘道，建構時不建立用戶端。"""
    from lecture_quiz import main
    from lecture_quiz.adapters.google.sheets_reader import default_service_factory
    from lecture_quiz.adapters.google.sheets_writer import GoogleSheetsWriter

    writer = main.app.state.export_service._writer
    assert isinstance(writer, GoogleSheetsWriter)
    assert writer._service_factory is default_service_factory
    assert writer._credentials is main.app.state.import_service.auth_gateway


def test_fake_auth_gateway_without_writer_leaves_writer_unset():
    """測試注入了假的授權閘道、沒有注入寫入器時，服務沒有寫入器（明確錯誤，不退回真實）。"""
    from tests.unit.app.guided_notes_import.fakes import (
        FakeAuthGateway,
        FakeSheetsReader,
    )

    app = make_app(
        import_auth_gateway=FakeAuthGateway(), import_sheets_reader=FakeSheetsReader()
    )
    assert app.state.export_service._writer is None


def test_router_exists_and_unknown_paths_still_404():
    with TestClient(make_app()) as client:
        assert client.get("/api/activities/ABC/export/unknown").status_code == 404
