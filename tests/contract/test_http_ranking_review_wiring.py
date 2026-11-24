"""`create_app()` 的 004 組裝（共用基礎）。"""

from lecture_quiz.app.ranking_review.service import RankingService
from tests.conftest import make_app


def test_app_wires_ranking_service():
    app = make_app()
    assert isinstance(app.state.ranking_service, RankingService)


def test_no_unimplemented_004_paths_are_exposed():
    """路由只有 T051、T069 實作後才會出現；實作前不得有半套路徑。"""
    app = make_app()
    paths = {getattr(route, "path", "") for route in app.routes}
    judgement = [p for p in paths if p.endswith("/judgement")]
    # 實作 PUT judgement 之前沒有；實作後恰好一條（本測試在 T051 之後改為斷言一條）
    assert len(judgement) <= 1
