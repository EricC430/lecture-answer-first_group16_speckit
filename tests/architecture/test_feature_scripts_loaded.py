"""每個子功能的前端腳本都有被頁面載入（docs/DEVELOPMENT.md 的擴充約定）。

曾經發生：004 的 `ranking-review-teacher.js` 與 `ranking-review.js` 寫好了，卻沒有在
`teacher.html`、`student.html` 加 `<script>`，所以關輪之後老師沒有判錯、撤銷、確認定案
的介面，學生也看不到結果。測試只看 HTTP 與 JSON，沒有任何一項會發現這件事。
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import make_app

STATIC = Path(__file__).resolve().parents[2] / "src/lecture_quiz/adapters/static"

TEACHER_SCRIPTS = (
    "teacher.js",  # 001
    "import.js",  # 002
    "round-submission-teacher.js",  # 003
    "ranking-review-teacher.js",  # 004：關輪後的順位、判錯、撤銷判錯、確認定案
    "result-export.js",  # 005
)
STUDENT_SCRIPTS = (
    "student.js",  # 001
    "round-submission.js",  # 003
    "ranking-review.js",  # 004：關輪後的結果
)


def _scripts(page: str) -> list[str]:
    html = (STATIC / page).read_text(encoding="utf-8")
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return re.findall(r'<script[^>]*\ssrc="js/([^"]+)"', html)


def test_teacher_page_loads_every_feature_script():
    """老師頁載入 001～005 各自的腳本。"""
    assert set(TEACHER_SCRIPTS) <= set(_scripts("teacher.html")), set(
        TEACHER_SCRIPTS
    ) - set(_scripts("teacher.html"))


def test_student_page_loads_every_feature_script():
    """學生頁載入 001、003、004 的腳本。"""
    assert set(STUDENT_SCRIPTS) <= set(_scripts("student.html")), set(
        STUDENT_SCRIPTS
    ) - set(_scripts("student.html"))


def test_every_section_with_a_feature_has_its_script():
    """頁面上每個標了 data-feature 的區塊，都有對應功能的腳本被載入。"""
    prefixes = {
        "001-activity-session": ("teacher.js", "student.js"),
        "002-guided-notes-import": ("import.js",),
        "003-round-submission": ("round-submission-teacher.js", "round-submission.js"),
        "004-ranking-review": ("ranking-review-teacher.js", "ranking-review.js"),
        "005-result-export": ("result-export.js",),
    }
    for page in ("teacher.html", "student.html"):
        html = (STATIC / page).read_text(encoding="utf-8")
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        loaded = set(_scripts(page))
        for feature in set(re.findall(r'data-feature="([^"]+)"', html)):
            assert loaded & set(prefixes[feature]), (page, feature)


def test_all_referenced_scripts_are_served():
    """頁面引用的每個腳本都真的由伺服器提供（200）。"""
    with TestClient(make_app()) as client:
        for page in ("teacher.html", "student.html"):
            for name in _scripts(page):
                response = client.get(f"/js/{name}")
                assert response.status_code == 200, (page, name)
