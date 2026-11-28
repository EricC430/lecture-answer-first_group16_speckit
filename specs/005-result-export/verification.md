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

| US5（T064～T067） | 2026-11-25 | `pytest tests/unit/app/result_export/test_download_csv.py tests/contract/result_export/test_http_csv.py tests/integration/test_export_us5_csv.py -q`（`download_csv`、X7 尚未實作） | 12 failed（共 12）；實作後 17 passed（連同 `test_export_static.py` 的其他檢查）。核心 `build_rows` 的測試（T064）在核心階段已完成，見第一列 |
| US6（T072～T075） | 2026-11-25 | `pytest tests/architecture/test_export_static.py -q` | 1 failed（`test_protection_prefix_note_is_fixed_text`，說明文字尚未加入）、5 passed；加入說明文字後 6 passed。T072、T073（`render_csv`、`protect_text`）與 `tests/integration/test_export_us6_safety.py` 在核心實作後才執行（核心階段先寫的核心測試當時已隨模組一起失敗再通過，見第一列），整合測試 2 passed |

## 自動化結果

（Polish 階段填寫：日期、指令、通過／失敗／略過數）

最終（T087、T088、T090，2026-11-25，US1～US6 與 Polish 自動化部分完成後）：

| 指令 | 結果 |
|---|---|
| `.venv\Scripts\ruff check .` | All checks passed |
| `.venv\Scripts\ruff format --check .` | 386 files already formatted |
| `.venv\Scripts\mypy` | Success: no issues found in 83 source files |
| `.venv\Scripts\python -m pytest -m "not real_google and not perf" -q` | 1328 passed、8 deselected、0 failed（基準 1089 passed；新增 239 項） |
| `.venv\Scripts\python -m pytest tests/architecture/test_core_is_pure.py -q` | 29 passed（`core/result_export/` 的 6 個模組被掃描，無違規） |

| 日期 | 指令 | 結果 |
|---|---|---|
| 2026-11-25（US6 完成時，中途紀錄） | `pytest -m "not real_google and not perf" -q` | 1324 passed、5 deselected、0 failed |
| 2026-11-25（US4 完成時，中途紀錄） | `pytest -m "not real_google and not perf" -q` | 1309 passed、1 failed、5 deselected；失敗的是 `tests/architecture/test_export_static.py::test_protection_prefix_note_is_fixed_text`（US6 的保護前綴說明文字，預期尚未完成） |

## 效能

2026-11-25，`pytest -m perf tests/perf/test_export_latency.py -q -o log_cli=true -o log_cli_level=INFO`：2 passed。

| 項目 | 結果 |
|---|---|
| 預覽計算（50 題、99 組；不含 Google 往返） | 0.001 s（50 項），門檻 < 3 s |
| CSV 產生（50 題 × 99 組 = 4950 列） | 0.019 s，門檻 < 3 s |
| 寫回狀態推送（真實 uvicorn、老師 1＋6 組各 2 條共 13 條 WebSocket、10 次，Google 用假替身） | 最大 4.5 ms、平均 3.9 ms，門檻 < 2000 ms；12 條學生連線收到 `export` 欄位的次數為 0 |

數字只代表 005 自己的處理與推送，不含真實 Google 往返。

## 真實路徑

（T083、T094：兩份真實 Google 試算表）**通過**：2026-11-27 在 `main`（02b47b4）完整測試並錄影，jacky0407 於 2026-11-28 回報全部通過；細節依使用者決定不逐步記錄，以錄影為證。

## 人工驗證

（T095：非實作者）**通過**：2026-11-27 在 `main`（02b47b4）完整測試並錄影，jacky0407 於 2026-11-28 回報全部通過；細節依使用者決定不逐步記錄，以錄影為證。

## R17 假設驗證結果

| # | 假設 | 結果 | 日期 | 執行者 |
|---|---|---|---|---|
| 1 | `drive.file` 足以對 Picker 選定的檔案執行 `batchUpdate` 與 `spreadsheets.get` | 成立（使用者回報，未逐項記錄） | 2026-11-27 | jacky0407 |
| 2 | 重新授權後仍能存取先前選定的檔案 | 成立（使用者回報，未逐項記錄） | 2026-11-27 | jacky0407 |
| 3 | `stringValue` 以等號、加號、減號、@、單引號開頭、前導零、類日期、換行讀回逐字相同 | 成立（使用者回報，未逐項記錄） | 2026-11-27 | jacky0407 |
| 4 | 合併作答格只寫左上角，格式與合併不變 | 成立（使用者回報，未逐項記錄） | 2026-11-27 | jacky0407 |
| 5 | 受保護範圍或唯讀權限時回 403 | 成立（使用者回報，未逐項記錄） | 2026-11-27 | jacky0407 |

## 問題紀錄

（實作時發現的問題、偏離與決定，依序記錄）

- **P-01（2026-11-25）**：002 的 `ImportService` 沒有公開它使用的授權閘道與 Sheets 讀取器，005 要共用同一份授權（`ImportStore.sessions`）就必須取得同一個實例。對 002 新增兩個**唯讀屬性** `auth_gateway`、`sheets_reader`（`src/lecture_quiz/app/guided_notes_import/service.py`，不改任何既有行為）。這偏離 plan R16「不修改 001～004」，但是純追加；002 既有測試全數通過。
- **P-02**：tasks T029 把 `Attempt` JSON 序列化放在 web 層，但快照擴充（app 層）也要用；相依方向只能由外層指向核心，所以序列化放在 `src/lecture_quiz/app/result_export/views.py`，web 層與擴充共用。
- **P-03**：`AttemptReason` 新增 `READ_FAILED`（寫入前讀取來源失敗、網路問題，沒有任何格被改）；data-model.md 與 http-api.md 已同步。
- **P-04**：ruff 的 E501 以顯示寬度計算（中文字算 2），測試與 docstring 的長中文句子需縮短；不改行寬設定。
- **P-06（T086，2026-11-25）圖表與程式碼一致性**：逐一比對三張圖與實作——組件圖（外層／應用層／核心與 001～004 唯讀相依、寫入轉接、重新授權直接用 002 授權連接埠）一致；類別圖補上 `WriteAttempt` 的三個格數與 `alreadyInProgress`、`PreviewView`、`WriteResult` 後與程式一致；時序圖修正兩處：預覽時「沒有成果」在讀取 Google 之前就拒絕（程式先檢查再讀取），以及核對的核心函式名稱為 `reconcile`。三張圖已重新轉出 PNG 並開啟檢視。
- **P-07（T091）quickstart A 節**：ruff、format、mypy、pytest（預設）、perf 的指令都已執行並記錄在本檔；B 節（真實路徑自動化）與 C 節（人工）尚未執行。
- **P-08（T092 未完成）**：實際啟動 `python -m lecture_quiz` 走一次預覽、寫回、CSV 需要真實 Google，尚未執行；日誌內容由 `tests/integration/test_export_logging.py` 以 caplog 驗證（不含答案、原儲存格內容、token、授權網址、`state`，且 stdout 沒有任何輸出），`grep` 確認 005 程式沒有 `print(`。
- **P-09（T093）**：`git ls-files` 沒有 `.env`、憑證或金鑰檔（只有既有的 `secrets_gen.py` 與其測試）；`pyproject.toml` 沒有變更（不新增套件）。
- **P-05**：整合測試 `tests/integration/conftest.py` 以真實 001～004 與 002 的 HTTP 入口建立世界，只把 Google 換成假的（`FakeSheetsWriter` 與 `FakeSheetsReader` 共用試算表狀態，analyze C1）。
- **P-10（2026-11-25，人工測試發現，屬 004 的既有漏洞）**：關輪之後老師頁沒有判錯、撤銷、確認定案的介面。原因：004 的 tasks T035、T036 要求在 `teacher.html`、`student.html` 各加一行 `<script>`，但 main 上實際沒有加，`ranking-review-teacher.js` 與 `ranking-review.js` 完全沒被載入（`git show origin/main:.../teacher.html` 只有 `teacher.js`、`import.js`、`round-submission-teacher.js`）；004 的 HTTP 與 JSON 測試都不載入頁面，所以沒有任何測試發現。修正：兩個頁面各補一行 `<script>`，並新增 `tests/architecture/test_feature_scripts_loaded.py`（先確認 3 項失敗再修；修後全部通過）檢查每個子功能的腳本都被載入、標了 `data-feature` 的區塊都有對應腳本、引用的腳本伺服器都提供。**限制**：只驗證到腳本被載入、語法正確與可被伺服器取得，沒有在真實瀏覽器操作過；老師與學生頁的實際畫面需要人工確認（quickstart 004、005 的人工驗證）。
- **P-11（2026-11-25，issue #26）**：合併 004 修正（#24）後，建立新活動時 005 的寫回預覽、狀態與核對表也要清掉：`result-export.js` 註冊 `onTeacherReset`；`tests/browser/test_pages.py::test_creating_new_activity_clears_previous_activity_screen` 加入 `export-section`／預覽檢查（拿掉重設時失敗，還原後通過）。合併後 `ruff check .` All checks passed、`mypy` no issues found in 83 source files、`pytest -m "not real_google and not perf" -q` 1338 passed、8 deselected。
