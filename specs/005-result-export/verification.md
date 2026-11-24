# 驗證紀錄：005-result-export

**規則**：只記錄這次真的執行過的指令與輸出；沒有執行的項目留空並註明，不得補寫（全域規則、憲章原則 VI）。日期為執行當天。

## 基準（T002）

在還沒有任何 005 程式碼的分支上（已合併 main 的 001～004）：

| 日期 | 指令 | 結果 |
|---|---|---|
| 2026-11-25 | `.venv\Scripts\ruff check .` | All checks passed |
| 2026-11-25 | `.venv\Scripts\ruff format --check .` | 319 files already formatted |
| 2026-11-25 | `.venv\Scripts\mypy` | Success: no issues found in 68 source files |
| 2026-11-25 | `.venv\Scripts\python -m pytest -m "not real_google and not perf" -q` | 1089 passed, 5 deselected, 1 warning（53.05s） |

## 先寫測試的失敗紀錄

（各 User Story 實作前先執行新測試並記錄失敗數，實作時填寫）

| Story／階段 | 日期 | 指令 | 失敗數 |
|---|---|---|---|
| 核心測試（T006、T019、T020、T031、T050、T064、T072、T073） | 2026-11-25 | `pytest tests/unit/core/result_export -q`（模組尚未存在） | 8 個測試檔收集階段就失敗（ModuleNotFoundError）；實作後 114 passed（含 `tests/architecture`） |
| Foundational 應用層（T007～T010） | 2026-11-25 | `pytest tests/unit/app/result_export tests/contract/result_export -q`（服務尚未存在） | `conftest` 載入即 ImportError（整個目錄無法執行）；建立骨架後 wiring 3 failed、其餘 33 passed；組裝後 36 passed |
| US1（T019～T024） | 2026-11-25 | `pytest tests/unit/app/result_export tests/contract/result_export tests/integration/test_export_us1_two_rounds.py -q`（preview／confirm 尚未實作） | 20 failed、37 passed（共 57）；實作後 57 passed |
| US2（T031～T035） | 2026-11-25 | `pytest test_structure_gate.py test_auth_failures.py test_reauthorization.py test_http_authorization.py -q` | 28 failed、5 passed（共 33）；實作後 150 passed（連同 US1 與核心） |
| US3（T042～T045） | 2026-11-25 | `pytest tests/unit/adapters/google/test_sheets_writer_request.py ...test_sheets_writer_read.py -q`（`sheets_writer.py` 尚未存在） | 2 個檔案收集階段失敗；實作後 15 passed。`tests/integration/test_export_us3_two_layouts.py` 與 `test_exact_write.py`（8 個）在轉接層實作前就通過：它們驗證的服務層邏輯已在 US1、US2 完成，轉接層（真實 Google 請求形狀）才是 US3 新增的部分，由前兩個檔案涵蓋 |
| US4（T049～T056） | 2026-11-25 | `pytest test_sheets_writer_outcomes.py test_pending_and_recheck.py test_retry_idempotent.py test_read_only_for_activity.py test_status_push.py test_http_attempts.py -q`（進行中控制、核對、重試尚未實作；`test_in_progress.py` 另跑） | 36 failed、2 passed（共 38）；`test_in_progress.py` 因當時會重複寫入而在 30 秒逾時（視為失敗，共 37 項失敗）；實作後這批與之前所有測試 410 passed（`tests/unit/app/result_export`、`tests/contract/result_export`、`tests/integration`、`tests/unit/adapters/google`、`tests/unit/core/result_export`） |

## 自動化結果

（Polish 階段填寫：日期、指令、通過／失敗／略過數）

| 日期 | 指令 | 結果 |
|---|---|---|
| 2026-11-25（US4 完成時，中途紀錄） | `pytest -m "not real_google and not perf" -q` | 1309 passed、1 failed、5 deselected；失敗的是 `tests/architecture/test_export_static.py::test_protection_prefix_note_is_fixed_text`（US6 的保護前綴說明文字，預期尚未完成） |

## 效能

（T082、T089）

## 真實路徑

（T083、T094：兩份真實 Google 試算表。**尚未執行**）

## 人工驗證

（T095：非實作者。**尚未執行**）

## R17 假設驗證結果

| # | 假設 | 結果 | 日期 | 執行者 |
|---|---|---|---|---|
| 1 | `drive.file` 足以對 Picker 選定的檔案執行 `batchUpdate` 與 `spreadsheets.get` | 未驗證 | | |
| 2 | 重新授權後仍能存取先前選定的檔案 | 未驗證 | | |
| 3 | `stringValue` 以等號、加號、減號、@、單引號開頭、前導零、類日期、換行讀回逐字相同 | 未驗證 | | |
| 4 | 合併作答格只寫左上角，格式與合併不變 | 未驗證 | | |
| 5 | 受保護範圍或唯讀權限時回 403 | 未驗證 | | |

## 問題紀錄

（實作時發現的問題、偏離與決定，依序記錄）

- **P-01（2026-11-25）**：002 的 `ImportService` 沒有公開它使用的授權閘道與 Sheets 讀取器，005 要共用同一份授權（`ImportStore.sessions`）就必須取得同一個實例。對 002 新增兩個**唯讀屬性** `auth_gateway`、`sheets_reader`（`src/lecture_quiz/app/guided_notes_import/service.py`，不改任何既有行為）。這偏離 plan R16「不修改 001～004」，但是純追加；002 既有測試全數通過。
- **P-02**：tasks T029 把 `Attempt` JSON 序列化放在 web 層，但快照擴充（app 層）也要用；相依方向只能由外層指向核心，所以序列化放在 `src/lecture_quiz/app/result_export/views.py`，web 層與擴充共用。
- **P-03**：`AttemptReason` 新增 `READ_FAILED`（寫入前讀取來源失敗、網路問題，沒有任何格被改）；data-model.md 與 http-api.md 已同步。
- **P-04**：ruff 的 E501 以顯示寬度計算（中文字算 2），測試與 docstring 的長中文句子需縮短；不改行寬設定。
- **P-05**：整合測試 `tests/integration/conftest.py` 以真實 001～004 與 002 的 HTTP 入口建立世界，只把 Google 換成假的（`FakeSheetsWriter` 與 `FakeSheetsReader` 共用試算表狀態，analyze C1）。
