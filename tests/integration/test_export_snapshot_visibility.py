"""005 資料可見性（憲章原則 V）：學生任何階段都看不到匯出資料，也不能呼叫端點。"""


def student_snapshot(s, device):
    return s.client.get(
        f"/api/activities/{s.code}/snapshot",
        headers={"Authorization": f"Bearer {device}"},
    ).json()


def test_students_never_see_export_and_cannot_call_endpoints(export_stack):
    """學生快照在寫回前後都沒有 export；X1～X7 對學生全部 403。"""
    s = export_stack("a")
    s.join(1, 2)
    s.open_round()
    s.submit(1, 3, 1, ["秘密答案"])
    s.close()
    s.finalize()
    device = s.devices[2]
    assert "export" not in student_snapshot(s, device)
    preview = s.export("POST", "/preview").json()
    first = s.export("POST", "/writes", {"snapshotId": preview["snapshotId"]}).json()
    student = {"Authorization": f"Bearer {device}"}
    attempt = first["attemptId"]
    calls = [
        ("POST", "/preview"),
        ("POST", "/writes"),
        ("POST", f"/writes/{attempt}/recheck"),
        ("POST", f"/writes/{attempt}/retry"),
        ("GET", "/writes/latest"),
        ("POST", "/authorization"),
        ("GET", "/csv"),
    ]
    for method, path in calls:
        url = f"/api/activities/{s.code}/export{path}"
        response = (
            s.client.get(url, headers=student)
            if method == "GET"
            else s.client.post(url, json={"snapshotId": "1"}, headers=student)
        )
        assert response.status_code == 403, (method, path, response.status_code)
        assert "秘密答案" not in response.text
    assert "export" not in student_snapshot(s, device)


def test_teacher_summary_has_no_answers_or_cell_content(export_stack):
    """老師快照的 export 不含答案、原內容與網址。"""
    s = export_stack("a")
    s.join(1)
    s.open_round()
    s.submit(1, 3, 1, ["不該出現在摘要的答案"])
    s.close()
    s.finalize()
    preview = s.export("POST", "/preview").json()
    s.export("POST", "/writes", {"snapshotId": preview["snapshotId"]})
    snapshot = s.client.get(
        f"/api/activities/{s.code}/snapshot", headers=s.teacher.headers
    ).json()
    summary = snapshot["export"]
    assert summary["status"] == "SUCCESS"
    text = str(summary)
    assert "不該出現在摘要的答案" not in text and "http" not in text
