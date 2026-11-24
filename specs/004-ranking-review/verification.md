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
| Phase 3～4 完成（T019～T036，US1／US2） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy`；`pytest tests/architecture -q` | 598 passed, 2 deselected（Phase 2 後 563 + 新增 35）；ruff All checks passed；format 214 files already formatted；mypy Success: no issues found in 48 source files；architecture 50 passed。測試先行：US1 核心測試先因匯入失敗（collection error）、app 4 項失敗，實作後通過；US2 3 個核心測試檔先 collection error、view／app／integration 先失敗，實作後通過。前端（T035／T036）無自動化測試，僅通過靜態文字安全檢查，畫面行為待 T094 人工驗證 |
| Phase 5 完成（T037～T042，US3） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 611 passed, 2 deselected（+13）；ruff All checks passed；format 217 files already formatted；mypy Success: no issues found in 48 source files。**未做到先紅後綠**：`rank_fair` 在 US2 實作 `recompute` 時一併完成，所以 US3 測試一寫完就通過；改以突變檢查補強：暫時把公平排序鍵的成功次數改成常數 0，`test_rank_fair.py`＋`test_fair_layouts.py` 11 項中 5 failed、6 passed，還原後 41 passed（`tests/unit/core/ranking_review`）。前端（T042）無自動化測試，待 T094 |
| Phase 6 完成（T043～T052、T055，US4） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 693 passed, 2 deselected（+82）；ruff All checks passed；format 224 files already formatted；mypy Success: no issues found in 48 source files。測試先行：`test_review_rules_mark.py` 先 ImportError（`RoundReviewRules` 不存在）、服務層 3 個測試檔先 `NotImplementedError`、HTTP 契約與端對端 19 項先全數失敗（`19 failed`），實作後 `19 passed`。`test_diff.py` 的 3 項在 `diff` 於 US2 已實作時就通過（同 P-06）。前端判錯／撤銷按鈕（T052）無自動化測試，待 T094 人工驗證 |
| Phase 7 完成（T053～T054、T056～T059，US5） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 703 passed, 2 deselected（+10）；ruff All checks passed；format 227 files already formatted；mypy Success: no issues found in 48 source files。依 T058 說明，重算在 US2～US4 已實作，所以這組測試一寫完就通過（不要求先失敗）；鑑別力由 T054 負對照證明：累加式錯誤實作 `accumulating_recompute` 跑完判錯、撤銷後與初始結果不同（`!=` 斷言通過），正確實作相同。前端「結果已更新」與版本守衛（T059）無自動化測試，待 T094 |
| Phase 8 完成（T060～T070，US6） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 733 passed, 2 deselected（+30）；ruff All checks passed；format 235 files already formatted；mypy Success: no issues found in 48 source files。測試先行：`test_finalize_plan.py` 先 `AttributeError`（無 `finalize_plan`），其餘 US6 測試在實作前因 `finalize` 為 `NotImplementedError` 失敗。實作後 001 的空定案路由已移除，既有 2 個測試因行為變化調整（見 P-09、P-10）。老師頁「確認定案」按鈕（T070）無自動化測試，待 T094 |
| PR #20 審查回應（T096） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 735 passed, 2 deselected（+2，新增 `test_single_finalize_button.py`）；ruff All checks passed；format 236 files already formatted；mypy Success: no issues found in 48 source files。已移除 001 老師頁的舊「確認定案」按鈕；Q-23／24／25 於 alignment.md 標為定案 |

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
| P-06 | Phase 5 | tasks 要求 US3 測試先失敗再實作，但 `rank_fair` 已在 US2 完成 | 如實記錄於上表，並以突變檢查證明測試能分辨對錯 |
| P-07 | Phase 6 | 測試寫「已取消且有輪次」的活動判錯，但 001 只允許第一輪之前取消，該情境不可能發生 | 改為對「取消後（沒有輪次）的活動」判錯，回 `ACTIVITY_CANCELLED`；判定順序仍是取消先於 `NO_ROUND` |
| P-08 | Phase 6 | 佈線測試原本用 `app.routes` 的 `path` 找路由，但巢狀 router 的 path 是空字串，斷言恆為 0（上一版的 `<= 1` 是假綠燈） | 改用 `app.openapi()["paths"]`，斷言恰有一條 `PUT .../judgement` |
| P-09 | Phase 8 | `test_finalize_during_round_is_409` 斷言搶答中定案的訊息為「請先關輪，再確認定案。」；004 接手後預設訊息變成「本輪尚未關閉，無法判錯。」 | 定案時的 `ROUND_STILL_OPEN` 沿用原訊息，測試斷言未改 |
| P-10 | Phase 8 | `test_second_round_keeps_history_and_hides_new_answers` 在第 2 輪提交題一，但 001 空定案換成 004 真定案後題一已成功、提交被拒（400） | 該測試改提交題二；這是定案行為從「不記成果」變成「記成功題」的預期後果，未放寬任何斷言 |
| P-11 | Phase 8 | 我寫的 US6 測試有三處預期算錯（沒判錯時乙只成功題二，次數應為 1 而不是 2）；第 2 輪「全題成功後開輪」001 回 400 而非 409 | 修正測試預期，實作未改 |
