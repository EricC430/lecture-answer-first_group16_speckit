"""US4：搶答中只看得到自己組，老師看得到全部（FR-021、FR-022、SC-005）。

「1 秒內沒有收到訊息」的檢查方式與 `test_fr030_student_push.py` 相同：他組提交之後
再做一次公開變更（關輪），學生的下一則訊息必須就是那次變更，版本只多 1。
"""

import json

import pytest

from tests.conftest import (
    create_activity,
    join_group,
    join_json,
    seed_questions,
    submit,
)


def _connect(client, code, token):
    ctx = client.websocket_connect(f"/ws/activities/{code}")
    ws = ctx.__enter__()
    ws.send_json({"type": "auth", "token": token})
    return ctx, ws, ws.receive_json()


@pytest.fixture
def opened(client):
    """版面 A；第 1 組兩台裝置（a、b）、第 2 組一台；已開第 1 輪（不倒數）。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    joined = join_json(client, teacher.code, {"groupNumber": 1})
    b = join_group(client, teacher.code, 1, joined["credential"])
    other = join_group(client, teacher.code, 2)
    response = client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )
    assert response.status_code == 201
    return teacher, {"a": joined["browserKey"], "b": b, "other": other}


def test_student_gets_nothing_from_other_groups(client, opened):
    """Scenario: US4-AS2（OpenSpec「檢查學生資料回應」；FR-022、SC-005）。"""
    teacher, devices = opened
    code = teacher.code
    headers = {"Authorization": f"Bearer {devices['a']}"}
    before = client.get(f"/api/activities/{code}/snapshot", headers=headers).json()
    ctx, ws, first = _connect(client, code, devices["a"])
    try:
        assert (
            submit(client, code, devices["other"], 1, 1, ["乙一", "乙二"]).status_code
            == 201
        )
        after = client.get(f"/api/activities/{code}/snapshot", headers=headers).json()
        assert after["version"] == before["version"]
        assert after["changedAt"] == before["changedAt"]
        assert after == before
        text = json.dumps(after, ensure_ascii=False)
        assert "乙一" not in text and "乙二" not in text
        assert after["ownGroup"]["successCount"] == 0  # Q-22：本組成功次數可見
        closed = client.post(
            f"/api/activities/{code}/rounds/current/close",
            json={},
            headers=teacher.headers,
        ).json()
        nxt = ws.receive_json()
        assert nxt["stage"] == "RESULT_PENDING"
        assert nxt["version"] == first["version"] + 1 == closed["version"]
    finally:
        ctx.__exit__(None, None, None)


@pytest.mark.parametrize("path", ["/submissions", "/groups/2/submissions"])
def test_no_endpoint_to_read_submissions(client, opened, path):
    """FR-021：沒有可依組號查詢提交的端點。"""
    teacher, devices = opened
    response = client.get(
        f"/api/activities/{teacher.code}{path}",
        headers={"Authorization": f"Bearer {devices['a']}"},
    )
    assert response.status_code in (404, 405)


def test_teacher_board_and_same_group_device_update(client, opened):
    """Scenario: US4-AS4、US4-AS6、US2-AS1（老師看板與同組另一台即時更新）。"""
    teacher, devices = opened
    code = teacher.code
    t_ctx, t_ws, t_first = _connect(client, code, teacher.token)
    b_ctx, b_ws, b_first = _connect(client, code, devices["b"])
    try:
        assert b_first["submissions"]["current"]["own"] == []
        accepted = submit(client, code, devices["a"], 1, 1, ["甲一", "甲二"])
        assert accepted.status_code == 201
        board = t_ws.receive_json()
        assert board["revision"] == t_first["revision"] + 1
        q1 = board["submissions"]["current"]["questions"][0]
        assert q1["questionNumber"] == 1
        assert q1["entries"] == [
            {
                "groupNumber": 1,
                "answers": ["甲一", "甲二"],
                "receivedAt": accepted.json()["submission"]["receivedAt"],
                "order": 1,
            }
        ]
        mine = b_ws.receive_json()
        assert mine["version"] == b_first["version"]
        assert mine["submissions"]["current"]["own"] == [
            {
                "questionNumber": 1,
                "answers": ["甲一", "甲二"],
                "receivedAt": accepted.json()["submission"]["receivedAt"],
            }
        ]
    finally:
        b_ctx.__exit__(None, None, None)
        t_ctx.__exit__(None, None, None)
