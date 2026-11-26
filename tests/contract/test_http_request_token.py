"""007 T006：請求者身分的來源與優先順序（research R4，contracts §2）。"""

from tests.conftest import create_joinable, new_browser_client


def _join_by_cookie(browser, code, number):
    return browser.post(
        f"/api/activities/{code}/groups/join", json={"groupNumber": number}
    )


def test_bearer_wins_over_student_cookie(client):
    """同一瀏覽器有學生 cookie 時，帶老師 Bearer 的請求仍是老師（US3、FR-009）。"""
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join_by_cookie(browser, teacher.code, 1).status_code == 200
    response = browser.post(
        f"/api/activities/{teacher.code}/rounds",
        json={"questionNumbers": [1]},
        headers=teacher.headers,
    )
    assert response.status_code == 201, response.text


def test_cookie_only_is_student(client):
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join_by_cookie(browser, teacher.code, 2).status_code == 200
    snapshot = browser.get(f"/api/activities/{teacher.code}/snapshot")
    assert snapshot.status_code == 200
    assert snapshot.json()["ownGroup"]["number"] == 2


def test_malformed_cookie_is_anonymous(client):
    teacher = create_joinable(client)
    browser = new_browser_client(client)
    assert _join_by_cookie(browser, teacher.code, 2).status_code == 200
    browser.cookies.clear()
    browser.cookies.set("lq_browser", "x" * 10)
    snapshot = browser.get(f"/api/activities/{teacher.code}/snapshot")
    assert snapshot.status_code == 403
    assert snapshot.json()["error"]["code"] == "NOT_TEACHER"
