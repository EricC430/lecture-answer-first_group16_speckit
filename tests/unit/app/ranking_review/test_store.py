"""`ReviewStore`：審閱狀態、每活動一把鎖、快取（共用基礎，data-model「應用層」）。"""

from lecture_quiz.app.ranking_review.store import ReviewStore
from lecture_quiz.core.ranking_review.models import RoundResult
from lecture_quiz.core.ranking_review.review import RoundReview


def _review(round_number: int, version: int = 1) -> RoundReview:
    return RoundReview(
        round_number=round_number,
        version=version,
        wrong_marks=frozenset(),
        result=RoundResult((), ()),
        affected=frozenset(),
        replaced={},
        finalized=None,
    )


def test_unknown_activity_returns_none():
    assert ReviewStore().get("ABC123", 1) is None


def test_put_then_get_returns_same_object_and_isolates_rounds_and_activities():
    store = ReviewStore()
    first, second = _review(1), _review(2)
    store.put("ABC123", first)
    store.put("ABC123", second)
    assert store.get("ABC123", 1) is first
    assert store.get("ABC123", 2) is second
    assert store.get("ZZZ999", 1) is None


def test_one_lock_per_activity():
    store = ReviewStore()
    assert store.lock("ABC123") is store.lock("ABC123")
    assert store.lock("ABC123") is not store.lock("ZZZ999")


def test_cache_key_includes_final_flag():
    """定案不增加結果版本卻改變輸出，所以「是否定案」必須在快取鍵裡。"""
    store = ReviewStore()
    store.cache_put("ABC123", 1, 3, False, "teacher", {"final": False})
    assert store.cache_get("ABC123", 1, 3, False, "teacher") == {"final": False}
    assert store.cache_get("ABC123", 1, 3, True, "teacher") is None
    assert store.cache_get("ABC123", 1, 4, False, "teacher") is None
    assert store.cache_get("ABC123", 1, 3, False, "student") is None
