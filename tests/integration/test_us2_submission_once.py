"""US2：HTTP 重送與刪除組別（每組每題每輪只算第一筆）。

同組另一台裝置收到含答案的快照（US2-AS1 推送部分）在 US4 的
`test_submission_visibility.py` 驗證；離組後公開資料仍屬原組（US2-AS6）在 US5 的
`test_us5_published.py` 驗證，兩者都需要快照中的提交資料。
"""

import pytest

from tests.conftest import create_activity, join_group, seed_questions, submit


@pytest.fixture
def opened(client):
    """版面 A、第 1 組兩台裝置、第 2 組一台、已開第 1 輪（不倒數）。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    joined = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 1}
    ).json()
    second = join_group(client, teacher.code, 1, joined["credential"])
    other = join_group(client, teacher.code, 2)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201, response.text
    return teacher, {"a": joined["deviceToken"], "b": second, "other": other}


def test_resend_returns_200_with_original(client, opened):
    """Scenario: US2-AS1、US2-AS2（重送與同組另一台送出都回原提交）。"""
    teacher, devices = opened
    first = submit(client, teacher.code, devices["a"], 1, 1, ["甲一", "甲二"])
    assert first.status_code == 201
    original = first.json()["submission"]
    for token, answers in (
        (devices["a"], ["甲一", "甲二"]),
        (devices["b"], ["乙一", "乙二"]),
        (devices["b"], ["只有一格"]),
    ):
        again = submit(client, teacher.code, token, 1, 1, answers)
        assert again.status_code == 200, again.text
        body = again.json()
        assert body["result"] == "alreadySubmitted"
        assert body["submission"] == original
        assert "本組已送出" in body["message"]
    other = submit(client, teacher.code, devices["other"], 1, 1, ["丙一", "丙二"])
    assert other.status_code == 201


def test_cannot_delete_group_with_submissions(client, opened):
    """Scenario: US2-AS7（搶答中不能刪組；有提交的組關輪後也不能刪）。"""
    teacher, devices = opened
    assert submit(client, teacher.code, devices["a"], 1, 3, ["丙"]).status_code == 201
    during = client.delete(
        f"/api/activities/{teacher.code}/groups/2", headers=teacher.headers
    )
    assert during.status_code == 409
    close = client.post(
        f"/api/activities/{teacher.code}/rounds/current/close",
        json={},
        headers=teacher.headers,
    )
    assert close.status_code == 200
    blocked = client.delete(
        f"/api/activities/{teacher.code}/groups/1", headers=teacher.headers
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "GROUP_HAS_SUBMISSIONS"
    ledger = client.app.state.submission_service._store.get(teacher.code)
    assert [(s.group_number, s.question_number) for s in ledger.submissions] == [(1, 3)]
