# 驗證紀錄：003-round-submission

依憲章原則 VI：記錄日期、實際執行的指令與結果數字。人工驗證與真實路徑驗證在本檔後段（尚未進行）。

## 基準（T002，實作前）

- 日期：2026-11-23；環境：Windows 11、Python 3.11.5；分支 `feature/7-003-round-submission`（已合併 main `a22f047`，含 001）。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 125 files already formatted |
| `mypy` | Success: no issues found in 26 source files |
| `pytest` | 389 passed, 1 deselected |

## Foundational（T005～T019）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T005～T009 共 5 個測試檔先寫，執行 `pytest`（只跑這 5 個檔）結果為 5 errors during collection（`RecordSubmission`、`HandlerStep`、`round_submission` 模組尚不存在）。
- **例外**：T018 的 dev seed `blanks` 測試是在實作之後補寫（順序與 TDD 不符），補寫後執行通過；已在此記錄。
- 實作中發現一個**測試本身的錯誤**：`test_accept_marks_then_commits_inside_lock_and_publishes_once` 的 setup 只清了 `published`、沒清 `locked_during_publish`，導致比對到建立活動時的推送紀錄；修正測試的 setup，程式碼未改。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 141 files already formatted |
| `mypy` | Success: no issues found in 34 source files |
| `pytest` | **421 passed**, 1 deselected（001 既有 389 個 + 新增 32 個） |
| `pytest tests/architecture` | 28 passed（`core/round_submission/` 已納入純函式檢查） |

- **001 既有測試**：全部通過，沒有修改任何既有斷言（T014）。既有測試檔中只有 `tests/conftest.py`（新增 003 共用工具，`make_app` 預設注入 `FakeQuestionShapeSource`）與 `tests/integration/test_dev_seed.py`（在檔尾新增 2 個測試）有變更。

## US1（T020～T028）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T020～T023 先寫；執行 `pytest tests/unit/core/round_submission/test_decide_us1.py tests/unit/app/round_submission tests/contract/test_http_submissions.py` 結果 24 failed、3 passed（通過的 3 個是 Foundational 已完成的 `test_store.py`）；`test_answer_rules.py` 收集失敗（模組不存在）。`questionShapes` 的整合測試也先寫並確認失敗（1 failed）。
- **設計調整**：`SubmissionRejection`、`DecisionKind`、`SubmissionDecision` 定義在 `core/round_submission/models.py`（`rules.py` 重新匯出），避免 `rules.py` 與 `answer_rules.py` 循環匯入；plan 的結構說明已同步。
- **前端**：`js/submission.js`、`js/round-submission.js` 以 `node --check` 通過；尚未在瀏覽器手動操作（留待 quickstart 人工驗證）。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `mypy` | Success: no issues found in 35 source files |
| `pytest` | **465 passed**, 1 deselected（新增 44 個；001 既有測試未修改） |
