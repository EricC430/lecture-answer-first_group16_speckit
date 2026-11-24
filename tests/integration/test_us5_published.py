"""US5：關輪後公開本輪提交，歷史可查但不洩漏新輪（FR-024～FR-026、FR-036）。"""

import json

import pytest

from tests.conftest import create_activity, join_group, seed_questions, submit


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    return ctx, ws, ws.receive_json()


def _post(client, teacher, path, body=None):
    response = client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body or {},
        headers=teacher.headers,
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture
def round1(client):
    """版面 A；第 1、2 組各一台裝置（甲、乙），已開第 1 輪（不倒數）。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    _post(client, teacher, "/open-joining")
    a = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 1}
    ).json()
    b = client.post(
        f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": 2}
    ).json()
    _post(client, teacher, "/rounds")
    return teacher, {
        "a": a["deviceToken"],
        "b": b["deviceToken"],
        "b_credential": b["credential"],
    }


def _snapshot(client, code, token):
    return client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_close_publishes_to_every_student(client, round1):
    """Scenario: US5-AS1、US5-AS4（關輪 version + 1；關輪後快照版本較新）。"""
    teacher, devices = round1
    code = teacher.code
    assert submit(client, code, devices["b"], 1, 1, ["乙一", "乙二"]).status_code == 201
    assert submit(client, code, devices["a"], 1, 1, ["甲一", "甲二"]).status_code == 201
    a_ctx, a_ws, a_first = _connect(client, code, devices["a"])
    try:
        assert a_first["submissions"]["published"] == []
        _post(client, teacher, "/rounds/current/close")
        closed = a_ws.receive_json()
        assert closed["version"] == a_first["version"] + 1
        assert closed["submissions"]["current"] is None
        published = closed["submissions"]["published"]
        assert [r["roundNumber"] for r in published] == [1]
        q1 = published[0]["questions"][0]
        assert [(e["groupNumber"], e["order"]) for e in q1["entries"]] == [
            (2, 1),
            (1, 2),
        ]
        assert q1["entries"][0]["answers"] == ["乙一", "乙二"]
        assert all(e["judgedWrong"] is False for e in q1["entries"])
        others = {q["questionNumber"]: q for q in published[0]["questions"][1:]}
        assert all(q["noSubmission"] for q in others.values())
    finally:
        a_ctx.__exit__(None, None, None)


def test_second_round_keeps_history_and_hides_new_answers(client, round1):
    """Scenario: US5-AS3（第 2 輪中乙組提交，甲組收不到訊息，仍看得到第 1 輪）。"""
    teacher, devices = round1
    code = teacher.code
    assert submit(client, code, devices["b"], 1, 1, ["乙一", "乙二"]).status_code == 201
    _post(client, teacher, "/rounds/current/close")
    _post(client, teacher, "/rounds/current/finalize", {"resultVersion": 1})
    _post(client, teacher, "/rounds")
    a_ctx, a_ws, a_first = _connect(client, code, devices["a"])
    try:
        history = a_first["submissions"]["published"]
        assert [r["roundNumber"] for r in history] == [1]
        assert (
            submit(client, code, devices["b"], 2, 2, ["乙新", "乙新"]).status_code
            == 201
        )
        after = _snapshot(client, code, devices["a"])
        assert after == a_first
        assert "乙新" not in json.dumps(after, ensure_ascii=False)
        closed = _post(client, teacher, "/rounds/current/close")
        nxt = a_ws.receive_json()
        assert nxt["version"] == a_first["version"] + 1 == closed["version"]
        assert [r["roundNumber"] for r in nxt["submissions"]["published"]] == [1, 2]
    finally:
        a_ctx.__exit__(None, None, None)


def test_reader_returns_sorted_immutable_tuples(client, round1):
    """FR-036：`SubmissionReader` 給 004、005 的資料已排序且不可修改。"""
    teacher, devices = round1
    code = teacher.code
    submit(client, code, devices["b"], 1, 2, ["乙", "乙"])
    submit(client, code, devices["a"], 1, 1, ["甲", "甲"])
    reader = client.app.state.submission_service
    in_round = reader.round_submissions(code, 1)
    assert isinstance(in_round, tuple)
    assert [s.group_number for s in in_round] == [2, 1]
    assert reader.all_submissions(code.lower()) == in_round
    assert reader.round_submissions(code, 2) == ()


def test_submission_stays_with_original_group_after_leaving(client, round1):
    """Scenario: US2-AS6（由 T031 移入；alignment B4）。

    第 1 輪替第 1 組送出後關輪、定案，該裝置離開並加入第 2 組；第 1 輪公開資料中
    該提交仍屬第 1 組。
    """
    teacher, devices = round1
    code = teacher.code
    assert submit(client, code, devices["a"], 1, 3, ["甲三"]).status_code == 201
    _post(client, teacher, "/rounds/current/close")
    _post(client, teacher, "/rounds/current/finalize", {"resultVersion": 1})
    left = client.post(
        f"/api/activities/{code}/groups/leave",
        json={},
        headers={"Authorization": f"Bearer {devices['a']}"},
    )
    assert left.status_code == 200, left.text
    moved = join_group(client, code, 2, devices["b_credential"])
    mine = _snapshot(client, code, moved)
    assert mine["ownGroup"]["number"] == 2
    snapshot = _snapshot(client, code, devices["b"])
    q3 = next(
        q
        for q in snapshot["submissions"]["published"][0]["questions"]
        if q["questionNumber"] == 3
    )
    assert [e["groupNumber"] for e in q3["entries"]] == [1]
    assert q3["entries"][0]["answers"] == ["甲三"]
    stored = client.app.state.submission_service.round_submissions(code, 1)
    assert [(s.question_number, s.group_number) for s in stored] == [(3, 1)]
