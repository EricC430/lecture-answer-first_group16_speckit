"""US1 端到端：第一輪已定案、第二輪搶答中，經 HTTP 預覽與確認（真實 001～004）。"""

from tests.fixtures.guided_notes_layouts import layout_a


def test_history_written_without_the_running_round(export_stack):
    """Scenario: US1-AS1（活動中匯出歷史成果）、US1-AS6：活動中可寫回已定案成果。"""
    s = export_stack("a")
    _, expected = layout_a()
    cells = {(q, sub): pos for q, sub, pos in expected.blanks}
    s.join(1, 2, 3)
    s.open_round()
    # 第 1 輪：題 1（兩格題組）與題 3（單題）
    s.submit(1, 1, 1, ["甲一", "甲二"])
    s.submit(1, 1, 2, ["乙一", "乙二"])
    s.submit(1, 3, 2, ["第三題"])
    s.close()
    s.finalize()
    # 第 2 輪：開放剩下的題，保持搶答中並有暫時提交
    s.open_round([2, 4])
    s.submit(2, 2, 3, ["暫時一", "暫時二"])
    assert s.writer.write_calls == [], "定案不會自動寫回"

    preview = s.export("POST", "/preview")
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert {i["questionNumber"] for i in body["items"]} == {1, 3}
    assert body["unwrittenQuestions"] == [2, 4]

    written = s.export("POST", "/writes", {"snapshotId": body["snapshotId"]})
    assert written.status_code == 200 and written.json()["status"] == "SUCCESS"
    assert s.cell_text(*cells[(1, 1)]) == "甲一"
    assert s.cell_text(*cells[(1, 2)]) == "甲二"
    assert s.cell_text(*cells[(3, None)]) == "第三題"
    assert s.cell_text(*cells[(2, 1)]) is None  # 第二輪的暫時提交沒有被寫入
    assert len(s.writer.write_calls) == 1 and len(s.writer.write_calls[0]) == 3
