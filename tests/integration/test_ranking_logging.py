"""T080：004 日誌（憲章技術限制 3、FR-032）。

判錯、撤銷、定案各留一行 INFO，只含活動代碼、輪次、題號、組號、wrong／changed 與版本；
日誌找不到答案文字、token、憑證。
"""

import logging
import re

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
)

SECRET = "SECRET-ANSWER-字串"
MARK = re.compile(
    r"判錯 activity=(?P<a>\S+) round=(?P<r>\d+) question=(?P<q>\d+) "
    r"group=(?P<g>\d+) wrong=(?P<w>True|False) changed=(?P<c>True|False) "
    r"version=(?P<v>\d+)"
)
FINAL = re.compile(
    r"定案 activity=(?P<a>\S+) round=(?P<r>\d+) version=(?P<v>\d+) "
    r"already=(?P<al>True|False)"
)


def _put(client, teacher, group, wrong):
    return client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/1/groups/{group}/judgement",
        json={"wrong": wrong},
        headers=teacher.headers,
    )


def test_mark_unmark_finalize_each_log_one_info_line(client, caplog):
    caplog.set_level(logging.INFO)
    teacher, devices = open_ranking_round(client, groups=(1, 2), questions=1)
    answer(client, teacher, devices, 1, 1, SECRET)
    answer(client, teacher, devices, 2, 1, SECRET)
    close_round(client, teacher)
    caplog.clear()
    assert _put(client, teacher, 1, True).status_code == 200
    assert _put(client, teacher, 1, False).status_code == 200
    from tests.conftest import finalize_current

    assert finalize_current(client, teacher).status_code == 200

    records = [r for r in caplog.records if r.name.startswith("lecture_quiz")]
    marks = [
        MARK.search(r.getMessage())
        for r in records
        if "判錯 activity=" in r.getMessage()
    ]
    assert [(m["w"], m["c"], m["v"]) for m in marks] == [
        ("True", "True", "2"),
        ("False", "True", "3"),
    ]
    for m in marks:
        assert (m["a"], m["r"], m["q"], m["g"]) == (teacher.code, "1", "1", "1")
    finals = [
        FINAL.search(r.getMessage())
        for r in records
        if "定案 activity=" in r.getMessage()
    ]
    assert len(finals) == 1 and finals[0]["al"] == "False" and finals[0]["v"] == "3"
    assert all(
        r.levelno == logging.INFO
        for r in records
        if "判錯" in r.getMessage() or "定案" in r.getMessage()
    )

    text = "\n".join(r.getMessage() for r in caplog.records)
    for secret in (SECRET, teacher.token, *devices.values(), "Traceback"):
        assert secret not in text


def test_no_print_in_ranking_sources():
    """日誌只用 logging，不用 print。"""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src/lecture_quiz"
    files = [
        *root.glob("**/ranking_review/*.py"),
        root / "adapters/web/ranking_review.py",
    ]
    assert files
    for file in files:
        assert "print(" not in file.read_text(encoding="utf-8"), file
