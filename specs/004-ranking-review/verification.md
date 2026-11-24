# 驗證紀錄：004-ranking-review

所有指令都在專案根目錄用 `.venv\Scripts\` 的工具執行（Python 3.14.7）。每筆紀錄只寫實際執行過的指令與結果數字。

## 基準（T002，2026-11-24，實作開始前，分支已合併 main 的 003）

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 184 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest -q` | 547 passed, 2 deselected |

## 先寫測試的失敗紀錄

| 階段 | 日期 | 指令 | 實作前的結果 |
|---|---|---|---|
| Phase 2（T005～T008） | 2026-11-24 | `pytest tests/unit/core/ranking_review tests/unit/app/ranking_review tests/contract/test_http_ranking_review_wiring.py -q` | 收集階段 ImportError：`No module named 'lecture_quiz.app.ranking_review.service'`（conftest 無法載入），0 個測試能執行 |

## 自動化結果

| 階段 | 日期 | 指令 | 結果 |
|---|---|---|---|
| Phase 2 完成（T018） | 2026-11-24 | `pytest -q` | 563 passed, 2 deselected（基準 547 + 新增 16）；`pytest tests/architecture -q` 47 passed；`ruff check .` All checks passed；`ruff format --check .` 201 files already formatted；`mypy` Success: no issues found in 45 source files |

## 效能（T082～T083）

（尚未執行）

## 人工驗證（T094）

（尚未執行；需要 002 合併後才能真實匯入題目）

## N/A 說明（T090）

（Polish 階段填寫）

## 問題紀錄

| 編號 | 階段 | 問題 | 處理 |
|---|---|---|---|
| P-01 | Phase 2 | `core/ranking_review/models.py` 的資料型別在寫 T005 測試之前已先草擬，不是先有失敗的測試 | 型別本身沒有行為邏輯；T005 測試補齊後通過。之後每個 Story 先寫測試並確認失敗再實作 |
| P-02 | Phase 2 | 專案沒有 `pytest-asyncio`，既有測試以 `asyncio.run(scenario())` 寫非同步測試 | 004 的測試沿用同一做法 |
| P-03 | Phase 2 | tasks 寫「`Outcome` 沿用 001 的型別」，但 001 的 `Outcome.rejection` 型別是 001 的 `RejectionReason` | 004 另定 `ReviewOutcome[T]`（`rejection` 為 `ReviewRejection`），與 contracts 的錯誤表一致；不放寬 001 的型別 |
| P-04 | Phase 2 | `T005` 的「RankingInput 不變式以 recompute 拒絕」依賴 recompute | 該不變式測試放在 US2 的 `test_recompute_speed.py`（recompute 實作時一併驗證） |
| P-05 | Phase 2 | T017 遷移既有測試：`test_finalize_contract` 原斷言回應 `== {"version": ...}`，004 取代 001 空定案路由後回應多了 `resultVersion`、`alreadyFinalized` | 斷言改為只比對 `["version"]`（活動狀態版本語意不變）；這是契約本身的變更，已記錄；其他測試只改呼叫方式（補 `{"resultVersion": 1}`），斷言未改 |
