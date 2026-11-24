"""004 整合測試共用：以真 app 建立「已開輪」的活動、提交與讀取快照。"""

from tests.conftest import create_activity, seed_questions, submit


def snapshot(client, code, token):
    """以某身分讀 `GET /snapshot`（老師用老師 token、學生用裝置 token）。"""
    return client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def post(client, teacher, path, body=None):
    """老師送出 POST；回傳 response。"""
    return client.post(
        f"/api/activities/{teacher.code}{path}",
        json=body if body is not None else {},
        headers=teacher.headers,
    )


def open_ranking_round(client, groups=(1, 2, 3), questions=3, fair=False):
    """建立活動、題號、各組加入並開第 1 輪；回傳 (teacher, {組號: 裝置 token})。"""
    teacher = create_activity(client)
    seed_questions(client, teacher, questions, blanks=[1] * questions)
    assert post(client, teacher, "/open-joining").status_code == 200
    devices = {}
    for group in groups:
        joined = client.post(
            f"/api/activities/{teacher.code}/groups/join", json={"groupNumber": group}
        ).json()
        devices[group] = joined["deviceToken"]
    body = {"fairMode": True} if fair else {}
    assert post(client, teacher, "/rounds", body).status_code == 201
    return teacher, devices


def answer(client, teacher, devices, group, question, text="答案", round_number=1):
    """某組提交某題（單格答案）；斷言被接受。"""
    response = submit(
        client, teacher.code, devices[group], round_number, question, [text]
    )
    assert response.status_code == 201, response.text


def close_round(client, teacher):
    """老師關輪；斷言成功。"""
    assert post(client, teacher, "/rounds/current/close").status_code == 200
