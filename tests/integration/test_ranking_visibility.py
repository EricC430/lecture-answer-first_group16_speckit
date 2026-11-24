"""US7：依角色可見的結果資料（FR-024、FR-030、FR-036、SC-007、SC-010）。

這裡只驗證資料面；畫面實際只顯示哪些組由前端決定，專案沒有前端單元測試設施，
該部分由 T094 人工驗證，不在此宣稱。
"""

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    post,
    snapshot,
)

HIDDEN_FROM_STUDENTS = {"reason", "countAtProcessing", "groupCounts", "actions"}


def _keys(node, found=None):
    found = set() if found is None else found
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            _keys(value, found)
    elif isinstance(node, list):
        for item in node:
            _keys(item, found)
    return found


def _put(client, teacher, question, group, wrong):
    return client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/{question}/groups/{group}/judgement",
        json={"wrong": wrong},
        headers=teacher.headers,
    )


def _q(client, teacher, token, question=1):
    rnd = snapshot(client, teacher.code, token)["ranking"]["rounds"][0]
    return next(q for q in rnd["questions"] if q["questionNumber"] == question)


def _setup(client, groups=(1, 2, 3, 4), fair=False):
    teacher, devices = open_ranking_round(client, groups=groups, questions=2, fair=fair)
    for group in groups:
        answer(client, teacher, devices, group, 1, f"答{group}")
    close_round(client, teacher)
    return teacher, devices


def test_no_ranking_while_round_is_open_for_every_role(client):
    """Scenario: US7-AS1（SC-007）。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    before = snapshot(client, teacher.code, devices[1])
    answer(client, teacher, devices, 2, 1)
    after = snapshot(client, teacher.code, devices[1])
    assert "ranking" not in before and "ranking" not in after
    assert after == before  # 他組動態不改變本組看到的內容
    assert "ranking" not in snapshot(client, teacher.code, teacher.token)


def test_student_json_hides_teacher_only_keys_but_teacher_has_them(client):
    """Scenario: US7-AS5／AS6（SC-010）。"""
    teacher, devices = _setup(client, fair=True)
    student = snapshot(client, teacher.code, devices[1])["ranking"]
    teacher_json = snapshot(client, teacher.code, teacher.token)["ranking"]
    assert _keys(student) & HIDDEN_FROM_STUDENTS == set()
    assert {"reason", "countAtProcessing", "groupCounts", "actions"} <= _keys(
        teacher_json
    )
    entry = student["rounds"][0]["questions"][0]["entries"][0]
    assert {"rank", "judgedWrong", "displayStatus"} <= set(entry)
    assert student["rounds"][0]["questions"][0]["successGroup"] is not None


def test_no_success_question_and_old_rounds_stay_public(client):
    """Scenario: US7-AS9／AS10／AS13。"""
    teacher, devices = _setup(client, groups=(1, 2))
    q2 = _q(client, teacher, devices[1], 2)
    assert q2["successGroup"] is None and q2["entries"] == []  # 無人提交 → 沒有 entry
    from tests.conftest import finalize_current

    assert finalize_current(client, teacher).status_code == 200
    assert post(client, teacher, "/rounds", {}).status_code == 201
    answer(client, teacher, devices, 2, 2, "新答案", round_number=2)
    snap = snapshot(client, teacher.code, devices[1])
    assert [r["roundNumber"] for r in snap["ranking"]["rounds"]] == [1]  # 新輪不出現
    assert "新答案" not in str(snap)


def test_replacement_chain_data_for_student_screen(client):
    """Scenario: US7-AS3／AS4／AS11、US4-AS10（資料部分）。"""
    teacher, devices = _setup(client)
    token = devices[4]
    _put(client, teacher, 1, 1, True)
    q = _q(client, teacher, token)
    assert (q["successGroup"], q["replacedGroup"]) == (2, 1)
    status = {e["groupNumber"]: e["displayStatus"] for e in q["entries"]}
    assert status[1] == "WRONG" and status[2] == "SUCCESS" and status[3] == "FAILED"
    _put(client, teacher, 1, 2, True)
    q = _q(client, teacher, token)
    assert (q["successGroup"], q["replacedGroup"]) == (3, 2)
    _put(client, teacher, 1, 2, False)
    q = _q(client, teacher, token)
    assert (q["successGroup"], q["replacedGroup"]) == (2, 1)
    _put(client, teacher, 1, 1, False)
    q = _q(client, teacher, token)
    assert (q["successGroup"], q["replacedGroup"]) == (1, None)


def test_all_wrong_hides_replaced_from_students_but_not_teacher(client):
    """Scenario: US7-AS9。"""
    teacher, devices = _setup(client, groups=(1, 2))
    _put(client, teacher, 1, 1, True)
    _put(client, teacher, 1, 2, True)
    student = _q(client, teacher, devices[1])
    teacher_q = _q(client, teacher, teacher.token)
    assert student["successGroup"] is None and student["replacedGroup"] is None
    assert teacher_q["successGroup"] is None and teacher_q["replacedGroup"] == 2


def test_final_shows_correct_and_clears_replaced(client):
    """Scenario: US7-AS14。"""
    from tests.conftest import finalize_current

    teacher, devices = _setup(client, groups=(1, 2))
    _put(client, teacher, 1, 1, True)
    assert finalize_current(client, teacher).status_code == 200
    q = _q(client, teacher, devices[2])
    assert q["replacedGroup"] is None
    assert {e["groupNumber"]: e["displayStatus"] for e in q["entries"]} == {
        1: "WRONG",
        2: "CORRECT",
    }
