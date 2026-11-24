"""US4：`RoundReviewRules.mark` 的判錯／撤銷規則（FR-010～FR-014、FR-025）。"""

import itertools

import pytest

from lecture_quiz.core.ranking_review.models import DisplayStatus
from lecture_quiz.core.ranking_review.review import (
    ReviewRejection,
    RoundReview,
    RoundReviewRules,
)
from tests.unit.core.ranking_review.helpers import cand, inp


def _three_groups():
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3), cand(1, 2, 4, 4)],
        questions=(1, 2),
    )
    return data, RoundReview.initial(1, data)


def _apply(review, data, group, question, wrong):
    decision = RoundReviewRules.mark(review, data, group, question, wrong)
    assert decision.ok, decision.rejection
    return decision


def test_mark_non_winner_keeps_original_candidate_data():
    """Scenario: US4-AS1／AS2 ↔ OpenSpec「非勝者與題組判錯」。"""
    data, review = _three_groups()
    decision = _apply(review, data, 2, 1, True)
    new = decision.review
    entry = next(e for e in new.result.ranking_of(1).entries if e.group_number == 2)
    assert entry.rank is None and entry.display_status is DisplayStatus.WRONG
    assert new.result.ranking_of(1).success_group == 1  # 勝者不變
    assert dict(new.replaced) == {}  # 判錯非搶答成功者 → 歷程不變
    assert data.candidates[1] == cand(2, 1, 2, 2)  # 原始資料沒被改


def test_unmark_restores_original_rank():
    """Scenario: US4-AS3 ↔ OpenSpec「撤銷誤判」。"""
    data, review = _three_groups()
    marked = _apply(review, data, 1, 1, True).review
    restored = _apply(marked, data, 1, 1, False).review
    assert restored.result == review.result
    assert restored.wrong_marks == frozenset()


def test_missing_submission_is_rejected():
    """Scenario: US4-AS6（（組, 題）沒有候選）。"""
    data, review = _three_groups()
    decision = RoundReviewRules.mark(review, data, 3, 2, True)
    assert not decision.ok
    assert decision.rejection is ReviewRejection.SUBMISSION_NOT_FOUND


def test_same_state_is_unchanged_and_version_stays():
    """FR-025：重複判錯、對未判錯者撤銷都不變、版本不變。"""
    data, review = _three_groups()
    again = RoundReviewRules.mark(review, data, 2, 1, False)
    assert again.ok and not again.changed and again.review is review
    marked = _apply(review, data, 2, 1, True).review
    twice = RoundReviewRules.mark(marked, data, 2, 1, True)
    assert twice.ok and not twice.changed and twice.review is marked


def test_real_change_bumps_version_and_sets_affected():
    """實際變更 → version + 1，affected 為最近一次變更的題號。"""
    data, review = _three_groups()
    new = _apply(review, data, 1, 1, True).review
    assert new.version == review.version + 1
    assert new.affected == frozenset({1})
    newer = _apply(new, data, 1, 2, True).review
    assert newer.affected == frozenset({2})  # 覆蓋，不累計


def test_replaced_history_appends_only_for_current_winner():
    """判錯「判錯前是搶答成功者」的組 → 附加到歷程末端。"""
    data, review = _three_groups()
    r1 = _apply(review, data, 1, 1, True).review
    assert r1.result.ranking_of(1).success_group == 2
    assert r1.replaced[1] == (1,)
    r2 = _apply(r1, data, 2, 1, True).review
    assert r2.result.ranking_of(1).success_group == 3
    assert r2.replaced[1] == (1, 2)


def test_undo_steps_back_one_at_a_time():
    """Scenario: US4-AS10／US7-AS3（連續判錯甲、乙後撤銷兩次）。"""
    data, review = _three_groups()
    r = _apply(_apply(review, data, 1, 1, True).review, data, 2, 1, True).review
    r = _apply(r, data, 2, 1, False).review
    assert r.result.ranking_of(1).success_group == 2
    assert r.replaced[1] == (1,)
    r = _apply(r, data, 1, 1, False).review
    assert r.result.ranking_of(1).success_group == 1
    assert dict(r.replaced).get(1, ()) == ()


@pytest.mark.parametrize("seed", range(40))
def test_replaced_invariant_holds_for_any_sequence(seed):
    """不變式：歷程中每一組都在該題 wrong_marks 內，且沒有重複。"""
    import random

    rng = random.Random(seed)
    data, review = _three_groups()
    targets = [(g, 1) for g in (1, 2, 3)] + [(1, 2)]
    for _ in range(12):
        group, question = rng.choice(targets)
        review = _apply(review, data, group, question, rng.random() < 0.6).review
        for q, history in review.replaced.items():
            marked = {g for (g, qq) in review.wrong_marks if qq == q}
            assert set(history) <= marked
            assert len(history) == len(set(history))


def test_all_sequences_of_two_ops_are_deterministic():
    """同樣的操作序列得到同樣的結果（重算只依輸入）。"""
    data, review = _three_groups()
    ops = [(1, 1, True), (2, 1, True), (1, 1, False), (2, 1, False)]
    for first, second in itertools.permutations(ops, 2):
        a = _apply(_apply(review, data, *first).review, data, *second).review
        b = _apply(_apply(review, data, *first).review, data, *second).review
        assert a == b
