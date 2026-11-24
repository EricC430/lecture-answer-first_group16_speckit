"""`create_app()` 的 004 組裝（共用基礎）。"""

from lecture_quiz.app.ranking_review.service import RankingService
from tests.conftest import make_app


def test_app_wires_ranking_service():
    app = make_app()
    assert isinstance(app.state.ranking_service, RankingService)


def test_judgement_route_is_exposed_exactly_once():
    """PUT judgement 已實作（T051）；finalize 路由到 T069 才由 004 接手。"""
    app = make_app()
    paths = app.openapi()["paths"]
    judgement = {p: list(m) for p, m in paths.items() if p.endswith("/judgement")}
    assert len(judgement) == 1
    assert next(iter(judgement.values())) == ["put"]
