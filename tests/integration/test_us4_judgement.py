"""US4：判錯與撤銷的端對端（真 app、HTTP + 快照）。"""

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)


def _put(client, teacher, question, group, wrong, round_number=1):
    return client.put(
        f"/api/activities/{teacher.code}/rounds/{round_number}/questions/"
        f"{question}/groups/{group}/judgement",
        json={"wrong": wrong},
        headers=teacher.headers,
    )


def _question(client, teacher, question=1, token=None):
    snap = snapshot(client, teacher.code, token or teacher.token)
    rnd = snap["ranking"]["rounds"][0]
    return next(q for q in rnd["questions"] if q["questionNumber"] == question)


def _setup(client, groups=(1, 2, 3, 4)):
    teacher, devices = open_ranking_round(client, groups=groups, questions=2)
    for group in groups:
        answer(client, teacher, devices, group, 1, f"答案{group}")
    close_round(client, teacher)
    return teacher, devices


def test_speed_sequence_marks_and_replacement(client):
    """Scenario: US4-AS7（判 1、2 錯 → 3 成功、4 失敗；再判 3 錯 → 4 遞補）。"""
    teacher, _ = _setup(client)
    assert _put(client, teacher, 1, 1, True).status_code == 200
    assert _put(client, teacher, 1, 2, True).status_code == 200
    q = _question(client, teacher)
    status = {
        e["groupNumber"]: (e["displayStatus"], e["judgedWrong"]) for e in q["entries"]
    }
    assert status[1] == ("WRONG", True) and status[2] == ("WRONG", True)
    assert status[3] == ("SUCCESS", False) and status[4] == ("FAILED", False)
    _put(client, teacher, 1, 3, True)
    q = _question(client, teacher)
    assert q["successGroup"] == 4
    assert {e["groupNumber"]: e["displayStatus"] for e in q["entries"]}[4] == "SUCCESS"


def test_undo_steps_back_and_actions_follow(client):
    """Scenario: US4-AS3／AS10（撤銷退回上一步，actions 依規則更新）。"""
    teacher, _ = _setup(client)
    _put(client, teacher, 1, 1, True)
    _put(client, teacher, 1, 2, True)
    q = _question(client, teacher)
    assert q["successGroup"] == 3
    assert q["actions"] == {"judgeGroup": 3, "undoGroup": 2}
    _put(client, teacher, 1, 2, False)
    q = _question(client, teacher)
    assert q["successGroup"] == 2 and q["replacedGroup"] == 1
    assert q["actions"] == {"judgeGroup": 2, "undoGroup": 1}
    _put(client, teacher, 1, 1, False)
    q = _question(client, teacher)
    assert q["successGroup"] == 1 and q["replacedGroup"] is None
    assert q["actions"] == {"judgeGroup": 1, "undoGroup": None}


def test_question_group_judgement_keeps_answers(client):
    """Scenario: US4-AS1／AS2（判錯後 003 的答案仍在 submissions.published）。"""
    teacher, _ = _setup(client, groups=(1, 2))
    _put(client, teacher, 1, 1, True)
    q = _question(client, teacher)
    entry = next(e for e in q["entries"] if e["groupNumber"] == 1)
    assert entry["judgedWrong"] is True and entry["displayStatus"] == "WRONG"
    published = snapshot(client, teacher.code, teacher.token)["submissions"][
        "published"
    ]
    answers = [
        e["answers"]
        for r in published
        for qq in r["questions"]
        if qq["questionNumber"] == 1
        for e in qq["entries"]
        if e["groupNumber"] == 1
    ]
    assert answers == [["答案1"]]


def test_api_allows_judging_a_non_winner(client):
    """Scenario: US4-AS9 的 API 部分。"""
    teacher, _ = _setup(client)
    assert _put(client, teacher, 1, 3, True).status_code == 200
    q = _question(client, teacher)
    assert q["successGroup"] == 1
    assert {e["groupNumber"]: e["judgedWrong"] for e in q["entries"]}[3] is True
