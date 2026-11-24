"""US3：公平模式輪次的老師快照含處理當下次數、理由與各組暫算次數（FR-007）。"""

from lecture_quiz.core.ranking_review.models import Candidate, RankingInput
from lecture_quiz.core.ranking_review.order import QuestionOrder
from lecture_quiz.core.ranking_review.ranking import RankingCalculator
from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)


def test_fair_round_snapshot_has_counts_reasons_and_group_counts(client):
    """Scenario: US3-AS1／AS4 整合面；數字與核心直接計算相同。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=2, fair=True)
    answer(client, teacher, devices, 1, 1, "甲一")
    answer(client, teacher, devices, 1, 2, "甲二")
    answer(client, teacher, devices, 2, 1, "乙一")
    answer(client, teacher, devices, 2, 2, "乙二")
    close_round(client, teacher)

    rnd = snapshot(client, teacher.code, teacher.token)["ranking"]["rounds"][0]
    assert rnd["fairMode"] is True
    questions = {q["questionNumber"]: q for q in rnd["questions"]}
    assert questions[1]["successGroup"] == 1
    assert questions[2]["successGroup"] == 2
    q2 = {e["groupNumber"]: e for e in questions[2]["entries"]}
    assert q2[2]["reason"] == "FEWER_SUCCESSES"
    assert q2[1]["countAtProcessing"] == 1 and q2[2]["countAtProcessing"] == 0
    assert rnd["groupCounts"] == {"1": 1, "2": 1}

    # 與核心直接計算相同（以老師快照的題序與同一份輸入）
    from datetime import UTC, datetime

    fake = datetime(2026, 1, 1, tzinfo=UTC)
    data = RankingInput(
        (1, 2),
        True,
        {1: 0, 2: 0},
        (
            Candidate(1, 1, fake, 1),
            Candidate(1, 2, fake, 2),
            Candidate(2, 1, fake, 3),
            Candidate(2, 2, fake, 4),
        ),
    )
    expected = RankingCalculator.recompute(
        data, QuestionOrder.compute(data.question_numbers, data.candidates)
    )
    assert {str(g): c for g, c in expected.group_counts.items()} == rnd["groupCounts"]


def test_speed_round_has_no_counts(client):
    """速度模式不顯示處理當下次數。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    answer(client, teacher, devices, 1, 1)
    answer(client, teacher, devices, 2, 1)
    close_round(client, teacher)
    entry = snapshot(client, teacher.code, teacher.token)["ranking"]["rounds"][0][
        "questions"
    ][0]["entries"][0]
    assert entry["countAtProcessing"] is None
