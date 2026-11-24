"""T080：日誌檢查（技術限制 3）：只用 logging、INFO 層級，不記錄 token 或憑證。"""

import logging
import pathlib

from tests.conftest import create_activity, join_group, open_joining

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"


def test_full_flow_logs_contain_no_secrets(client, caplog):
    caplog.set_level(logging.INFO)
    teacher = create_activity(client)
    open_joining(client, teacher)
    base = f"/api/activities/{teacher.code}"
    device = join_group(client, teacher.code, 1)
    credential = client.get(f"{base}/snapshot", headers=teacher.headers).json()[
        "groups"
    ][0]["credential"]
    join_group(client, teacher.code, 1, credential)
    for path in ("/rounds", "/rounds/current/close", "/rounds/current/finalize"):
        body = {"resultVersion": 1} if path.endswith("/finalize") else {}
        client.post(f"{base}{path}", json=body, headers=teacher.headers)
    client.post(
        f"{base}/groups/leave", json={}, headers={"Authorization": f"Bearer {device}"}
    )
    client.post(f"{base}/end", json={}, headers=teacher.headers)

    records = [r for r in caplog.records if r.name.startswith("lecture_quiz")]
    assert records
    assert {r.levelno for r in records} == {logging.INFO}
    text = "\n".join(r.getMessage() for r in records)
    for secret in (teacher.token, device, credential):
        assert secret not in text


def test_source_has_no_print_calls():
    offenders = [
        str(path)
        for path in SRC.rglob("*.py")
        if "print(" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
