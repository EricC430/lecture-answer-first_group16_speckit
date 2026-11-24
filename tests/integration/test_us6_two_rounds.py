"""US6／US1：兩輪端對端，驗證定案成果成為下一輪基準。"""

from tests.conftest import finalize_current
from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    post,
    snapshot,
)


def test_success_counts_feed_next_round_baseline(client):
    """Scenario: US1-AS1／AS2／US6-AS1（速度第 1 輪定案 → 第 2 輪公平依基準）。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=3)
    answer(client, teacher, devices, 1, 1)
    answer(client, teacher, devices, 1, 2)
    answer(client, teacher, devices, 2, 3)
    close_round(client, teacher)
    assert finalize_current(client, teacher).status_code == 200
    groups = {
        g["number"]: g for g in snapshot(client, teacher.code, teacher.token)["groups"]
    }
    assert groups[1]["successCount"] == 2 and groups[2]["successCount"] == 1
    # 第 1 輪已全部成功 → 001 拒絕開下一輪（不屬 004，確認不退步）
    refused = post(client, teacher, "/rounds", {"fairMode": True})
    assert refused.status_code == 400, refused.text


def test_second_round_fair_uses_baseline(client):
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=3)
    answer(client, teacher, devices, 1, 1)
    close_round(client, teacher)
    assert finalize_current(client, teacher).status_code == 200
    opened = post(client, teacher, "/rounds", {"fairMode": True})
    assert opened.status_code == 201
    answer(client, teacher, devices, 1, 2, round_number=2)
    answer(client, teacher, devices, 2, 2, round_number=2)
    close_round(client, teacher)
    rounds = snapshot(client, teacher.code, teacher.token)["ranking"]["rounds"]
    assert [r["roundNumber"] for r in rounds] == [1, 2]
    q2 = next(q for q in rounds[1]["questions"] if q["questionNumber"] == 2)
    assert q2["successGroup"] == 2  # 乙基準 0、甲基準 1，乙雖較晚仍優先
    assert q2["entries"][0]["reason"] == "FEWER_SUCCESSES"
    assert rounds[0]["final"] is True and rounds[1]["final"] is False


def test_round_without_submissions_finalizes_with_unchanged_counts(client):
    """Scenario: US6-AS7。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=2)
    close_round(client, teacher)
    assert finalize_current(client, teacher).status_code == 200
    snap = snapshot(client, teacher.code, teacher.token)
    assert all(g["successCount"] == 0 for g in snap["groups"])
    assert snap["ranking"]["rounds"][0]["final"] is True
