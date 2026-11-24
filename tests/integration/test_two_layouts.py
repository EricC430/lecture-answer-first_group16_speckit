"""T058：兩份版面的格數（憲章原則 III、SC-009）。

以 dev seed 的格數建立兩個活動：版面 A（課程範本 [2, 2, 1, 1]）、版面 B
（起始位置不同、含三格題組 [1, 3, 1, 2, 1]）。每個活動完成「格數錯誤被拒 →
正確格數接受 → 關輪公開」。格數只來自匯入結果，程式沒有假設固定格數。
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeClock, ManualScheduler, join_group, make_app, submit

LAYOUTS = {"A": [2, 2, 1, 1], "B": [1, 3, 1, 2, 1]}


@pytest.fixture
def dev_client():
    """啟用 dev seed 的 app：格數走真實的 `DevQuestionShapeSource`。"""
    with TestClient(make_app(FakeClock(), ManualScheduler(), dev_seed=True)) as c:
        yield c


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_layout_blanks_drive_validation(dev_client, layout):
    client = dev_client
    blanks = LAYOUTS[layout]
    created = client.post("/api/activities", json={"maxGroups": 6}).json()
    code = created["code"]
    headers = {"Authorization": f"Bearer {created['teacherToken']}"}
    seeded = client.post(
        f"/api/dev/activities/{code}/seed-questions",
        json={"count": len(blanks), "blanks": blanks},
        headers=headers,
    )
    assert seeded.status_code == 200, seeded.text
    client.post(f"/api/activities/{code}/open-joining", json={}, headers=headers)
    device = join_group(client, code, 1)
    client.post(f"/api/activities/{code}/rounds", json={}, headers=headers)

    snapshot = client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()
    assert snapshot["questionShapes"] == {
        str(n): b for n, b in enumerate(blanks, start=1)
    }

    widest = max(range(len(blanks)), key=lambda i: blanks[i]) + 1
    need = blanks[widest - 1]
    wrong = submit(client, code, device, 1, widest, ["x"] * (need + 1))
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "WRONG_BLANK_COUNT"
    right = submit(client, code, device, 1, widest, [f"格{i}" for i in range(need)])
    assert right.status_code == 201
    assert len(right.json()["submission"]["answers"]) == need

    closed = client.post(
        f"/api/activities/{code}/rounds/current/close", json={}, headers=headers
    )
    assert closed.status_code == 200
    published = client.get(
        f"/api/activities/{code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()["submissions"]["published"]
    question = next(
        q for q in published[0]["questions"] if q["questionNumber"] == widest
    )
    assert question["entries"][0]["answers"] == [f"格{i}" for i in range(need)]
    assert len(published[0]["questions"]) == len(blanks)
