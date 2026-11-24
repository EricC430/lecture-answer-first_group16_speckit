"""US5：重算後受影響題目的標示與版本單調（FR-016）。"""

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)


def _put(client, teacher, question, group, wrong):
    return client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/{question}/groups/{group}/judgement",
        json={"wrong": wrong},
        headers=teacher.headers,
    )


def _round(client, teacher, token=None):
    return snapshot(client, teacher.code, token or teacher.token)["ranking"]["rounds"][
        0
    ]


def _setup(client):
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=3, fair=True)
    for q in (1, 2, 3):
        answer(client, teacher, devices, 1, q)
    for q in (1, 2):
        answer(client, teacher, devices, 2, q)
    close_round(client, teacher)
    return teacher, devices


def test_affected_marks_follow_latest_change_and_versions_increase(client):
    """Scenario: US5-AS5／AS6。"""
    teacher, devices = _setup(client)
    assert _round(client, teacher)["affectedQuestions"] == []
    assert _put(client, teacher, 1, 1, True).json()["affectedQuestions"] == [1, 2]
    rnd = _round(client, teacher)
    assert rnd["affectedQuestions"] == [1, 2]
    # 晚開啟的頁面（學生）看到相同標示
    assert _round(client, teacher, devices[2])["affectedQuestions"] == [1, 2]
    first_version = rnd["resultVersion"]
    assert _put(client, teacher, 3, 1, True).json()["affectedQuestions"] == [3]
    rnd = _round(client, teacher)
    assert rnd["affectedQuestions"] == [3]
    assert rnd["resultVersion"] > first_version
    versions = [_round(client, teacher)["resultVersion"] for _ in range(5)]
    assert versions == sorted(versions) and versions[0] >= rnd["resultVersion"]


def test_winner_marked_wrong_is_replaced_by_next(client):
    """Scenario: US5-AS8。"""
    teacher, _ = _setup(client)
    _put(client, teacher, 3, 1, True)
    q3 = next(
        q for q in _round(client, teacher)["questions"] if q["questionNumber"] == 3
    )
    assert q3["successGroup"] is None
    entry = q3["entries"][0]
    assert entry["displayStatus"] == "WRONG"
    _put(client, teacher, 1, 1, True)
    q1 = next(
        q for q in _round(client, teacher)["questions"] if q["questionNumber"] == 1
    )
    assert q1["successGroup"] == 2
    assert {e["groupNumber"]: e["displayStatus"] for e in q1["entries"]} == {
        1: "WRONG",
        2: "SUCCESS",
    }


def test_finalized_round_has_no_affected_marks(client):
    """定案後 affectedQuestions 為空（final 的輸出；此處以 view 輸出驗證）。"""
    from tests.conftest import finalize_current

    teacher, _ = _setup(client)
    _put(client, teacher, 1, 1, True)
    assert finalize_current(client, teacher).status_code == 200
    assert _round(client, teacher)["affectedQuestions"] == []
