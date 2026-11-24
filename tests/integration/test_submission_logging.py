"""T057：003 提交日誌（FR-035、研究 R13）。

接受、本組已送出與各種拒絕都要留下 activity、round、question、group、result；
不得記下裝置 token、答案內容或 Traceback。
"""

import logging
import re

from tests.conftest import create_activity, join_group, seed_questions, submit

SECRET = "SECRET-ANSWER-字串"
PATTERN = re.compile(
    r"提交 activity=(?P<activity>\S+) round=(?P<round>\S+) "
    r"question=(?P<question>\S+) group=(?P<group>\S+) result=(?P<result>\S+)"
)


def _logs(caplog):
    return [
        PATTERN.search(r.getMessage())
        for r in caplog.records
        if r.name.startswith("lecture_quiz") and "提交 activity=" in r.getMessage()
    ]


def test_submission_logs_have_fields_but_no_secrets(client, caplog):
    caplog.set_level(logging.INFO)
    teacher = create_activity(client)
    seed_questions(client, teacher, 4, blanks=[2, 2, 1, 1])
    client.post(
        f"/api/activities/{teacher.code}/open-joining", json={}, headers=teacher.headers
    )
    device = join_group(client, teacher.code, 2)
    client.post(
        f"/api/activities/{teacher.code}/rounds", json={}, headers=teacher.headers
    )

    cases = [
        (submit(client, teacher.code, device, 1, 1, [SECRET, SECRET]), "accepted"),
        (submit(client, teacher.code, device, 1, 1, [SECRET, "x"]), "alreadySubmitted"),
        (submit(client, teacher.code, device, 1, 2, [SECRET, " "]), "BLANK_EMPTY"),
        (submit(client, teacher.code, device, 1, 3, ["a", "b"]), "WRONG_BLANK_COUNT"),
        (submit(client, teacher.code, device, 9, 3, [SECRET]), "STALE_ROUND"),
        (submit(client, teacher.code, "not-a-token", 1, 3, [SECRET]), "NOT_IN_GROUP"),
    ]
    assert [r.status_code for r, _ in cases] == [201, 200, 400, 400, 409, 403]

    logs = _logs(caplog)
    assert all(logs), "每筆提交日誌都要有五個欄位"
    assert [m["result"] for m in logs] == [result for _, result in cases]
    for match in logs:
        assert match["activity"] == teacher.code
    for match in logs[:5]:
        assert match["round"] == "1"  # 本輪輪次（舊頁面送來的 9 不寫進日誌）
        assert match["group"] == "2"
    assert [m["question"] for m in logs[:5]] == ["1", "1", "2", "3", "3"]
    assert logs[5]["group"] == "-"  # 不屬於任何組

    text = "\n".join(r.getMessage() for r in caplog.records)
    assert SECRET not in text
    assert device not in text and "not-a-token" not in text
    assert "Traceback" not in text and not any(r.exc_info for r in caplog.records)
