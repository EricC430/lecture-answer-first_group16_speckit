"""US7：特殊文字與長答案在資料面逐字保存；004 不複製答案（FR-028、FR-035）。"""

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)

MARKUP = "<b>粗體</b><script>alert(1)</script>"
LONG_MULTILINE = "\n".join("第" + str(i) + "行" + "字" * 95 for i in range(5))


def test_answers_survive_judgement_verbatim_and_004_holds_no_answers(client):
    """Scenario: US7-AS7／AS12。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    answer(client, teacher, devices, 1, 1, MARKUP)
    answer(client, teacher, devices, 2, 1, LONG_MULTILINE)
    assert len(LONG_MULTILINE) >= 500 - 10
    close_round(client, teacher)
    client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/1/groups/1/judgement",
        json={"wrong": True},
        headers=teacher.headers,
    )
    snap = snapshot(client, teacher.code, teacher.token)
    published = snap["submissions"]["published"][0]["questions"][0]["entries"]
    by_group = {e["groupNumber"]: e["answers"] for e in published}
    assert by_group == {1: [MARKUP], 2: [LONG_MULTILINE]}
    ranking_text = str(snap["ranking"])
    assert "script" not in ranking_text and "第0行" not in ranking_text
