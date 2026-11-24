"""US7：每個身分看到的 resultVersion 單調不減（FR-016，後端層保證）。"""

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)


def _version(client, teacher, token):
    return snapshot(client, teacher.code, token)["ranking"]["rounds"][0][
        "resultVersion"
    ]


def test_versions_never_decrease_across_marks_and_reads(client):
    """Scenario: US7-AS8。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2, 3), questions=1)
    for group in (1, 2, 3):
        answer(client, teacher, devices, group, 1)
    close_round(client, teacher)
    tokens = [teacher.token, devices[1], devices[3]]
    last = dict.fromkeys(tokens, 0)
    ops = [(1, True), (2, True), (2, False), (1, False), (3, True)]
    for group, wrong in ops:
        client.put(
            f"/api/activities/{teacher.code}/rounds/1/questions/1/groups/{group}/judgement",
            json={"wrong": wrong},
            headers=teacher.headers,
        )
        for token in tokens:
            for _ in range(3):
                version = _version(client, teacher, token)
                assert version >= last[token]
                last[token] = version
    assert last[teacher.token] == 1 + len(ops)
