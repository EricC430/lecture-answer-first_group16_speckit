# Implementation Plan: 定案成果寫回 Google Sheets 與 CSV 匯出（Result Export）

**Branch**: `feature/9-005-result-export` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-result-export/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/005-result-export-component.puml`](../../diagrams/005-result-export-component.puml)
- 類別圖：[`diagrams/005-result-export-class.puml`](../../diagrams/005-result-export-class.puml)
- 時序圖：[`diagrams/005-result-export-sequence.puml`](../../diagrams/005-result-export-sequence.puml)

本 plan 的模組、類別與流程依這三張圖命名。plan 階段因研究 R3（單一 `batchUpdate` 原子寫入）、R4（005 自己讀取目標格的 `userEnteredValue`）、R5（結構比對的差異分類）、R8（重新授權直接使用 002 的授權連接埠）調整了圖，三張圖已在同一個 commit 更新並重新轉出 PNG。實作偏離時先改圖。

**前置條件**：005 依賴 001（匯出檢視、快照擴充、推送）、002（`ImportRecord`、`SheetsReader`、`GuidedNotesParser`、`AuthGateway`）、003（`all_submissions`）與 004（`finalized_rounds`），四者都已在 main，本分支已合併；005 不修改它們（研究 R16）。

## Summary

老師手動把已定案輪次的搶答成功者答案寫回原學習單，並可下載完整紀錄 CSV。寫回前先預覽（題號、子空格、搶答成功者、答案、目標位置、覆寫影響），確認綁定成果快照；每次寫入與重試前重新讀取來源並以 002 的規則重新辨識、逐項比對結構，不符就整次停止；答案以文字值寫入作答格，其他內容不變；結果分為成功、明確失敗、待確認，可核對與重試且冪等；CSV 九欄、UTF-8、公式字元文字保護。

技術做法：

- **核心**（`core/result_export/`，純函式）：`snapshot.py`（成果快照與覆寫影響）、`structure.py`（`compare_structure`，七類差異）、`reconcile.py`（核對判定）、`csv_export.py`（資料列、`render_csv`、`protect_text`）。輸入都是已查好的資料（004 的候選、003 的提交、002 的映射、目前的格內容），沒有時鐘或 I/O。
- **服務層**（`app/result_export/`）：`ExportService` 用**自己的**記憶體存放區與每活動一把鎖，Google I/O 在鎖外（研究 R1）；先經 001 `export_view` 做老師身分與「已取消」閘門；寫回狀態以快照擴充 `export` 推送給老師（研究 R11）。
- **外層**：`adapters/google/sheets_writer.py`（`GoogleSheetsWriter`：讀取目標格 `userEnteredValue`；單一 `spreadsheets.batchUpdate`、每格 `updateCells`、`stringValue`、`fields="userEnteredValue"` 原子寫入；把 Google 回應分成成功／明確失敗／待確認）；`adapters/web/result_export.py`（X1～X7）；老師頁匯出區塊 `js/result-export.js`。
- **不改 001～004、不新增套件**（研究 R16）；重新授權直接使用 002 的 `AuthGateway`，不受匯入階段限制（研究 R8，修正了 clarify 時「需調整 002」的假設）。

## Technical Context

**Language/Version**: Python 3.11 以上（沿用）

**Primary Dependencies**: FastAPI、uvicorn、pydantic、`google-api-python-client`、`google-auth`、`google-auth-oauthlib`（全部已是核心相依，不新增套件）；CSV 用標準函式庫 `csv`；前端原生 JavaScript

**Storage**: 只存在後端記憶體（憲章原則 VII）；寫回嘗試與預覽隨後端重啟清空；已寫入老師試算表的內容不回復

**Testing**: pytest（`perf`、`real_google` 預設排除）、pytest-timeout、FastAPI TestClient、`googleapiclient.http.HttpMockSequence`（轉接層）；ruff、ruff format、mypy（`src/`）

**Target Platform**: Windows 本機，後端只監聽 127.0.0.1

**Project Type**: 單一 web 服務（後端 + 靜態前端），沿用 001 的 src layout 與三層相依方向

**Performance Goals**: 50 題規模下，預覽計算（不含 Google 往返）與 CSV 產生各不超過 3 秒（SC-008，`perf` 測試）；寫回狀態變更在 2 秒內反映到老師畫面（老師 + 6 組、每組 2 條連線為必過門檻，沿用 001／004 的同步驗證）

**Constraints**: 核心不依賴網路、框架、系統時鐘；寫入前結構檢查不可略過（寫入與重試）；整次寫入原子（單一 `batchUpdate`）；不修改非目標格；答案逐字文字值、不加保護前綴；CSV 不依賴 Google；日誌不記答案、原儲存格內容與 token；Google 呼叫在 `asyncio.to_thread` 內，不阻塞推送

**Scale/Scope**: 題數 50 題以內、每活動最多 99 組（001 A2）；每格答案 ≤ 500 字（003）；一次預覽讀取兩次整張工作表（002 的 `read` 與 005 的目標格讀取），一次寫入一個 `batchUpdate`（最多數百個 `updateCells` 請求）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致（NON-NEGOTIABLE） | spec 的 Traceability 涵蓋 result-export 全部 6 個 Requirement、12 個 Scenario；偏離或新增只有「取消的活動不提供寫回與 CSV」，已記於 alignment 2026-11-23（C8，OpenSpec 組同意）；alignment 待確認表目前只有 Q-07（已決議）；clarify 的兩項決定（重新授權入口、核對不做結構檢查）屬設計方式，不改變 OpenSpec 規定的行為 | ✅ |
| II 圖表生成（NON-NEGOTIABLE） | 三張圖已在 specify 產出；plan 因研究 R3、R4、R5、R8 調整後同步更新並重新轉出 PNG；implement 後要做「程式碼 ↔ 圖」一致性檢查（tasks 列為必做） | ✅ |
| III Guided Notes 動態定位 | 目標位置完全取自 002 保存的 `Blank.target`，以 `sheetId` 與列欄索引寫入，不寫死工作表名稱或座標；每次寫入與重試前重新讀取並以 002 的 `parse` 重新辨識、與匯入時結構逐項比對（`compare_structure`），不符整次停止、不猜新位置；答案以 `stringValue` 文字值寫入；驗證至少用 `layout_a`、`layout_b` 兩份版面（單題／題組、縱向合併／相鄰重複題號、起始列欄與工作表名稱不同）端到端寫回，並以兩份真實試算表人工驗證 | ✅ |
| IV 後端為唯一事實來源 | 順位、搶答成功者與答錯標記只取 004 的定案結果，005 不重新計算；答案與接收時間取 003；老師身分只依 001；成果快照識別由後端依已定案輪次計算，確認時重新計算比對；同一活動一次一個寫入、重送不產生第二次寫入 | ✅ |
| V 資料可見性與安全 | 所有端點只限活動老師，學生快照永遠沒有 `export`；答案與原儲存格內容在畫面一律 `textContent`；CSV 的組別與答案以保護前綴防公式；所有外部輸入（活動代碼、快照識別、嘗試編號、身分、授權、來源內容）後端驗證，失敗不改儲存格或狀態；錯誤訊息集中管理、不含堆疊／路徑／憑證；日誌只記活動代碼、快照識別、格數、結果與原因類別 | ✅ |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 與 OpenSpec Scenario 都有測試並加入 `tests/SCENARIO_MAP.md`；自動化測試 100% 使用 Google mock（`HttpMockSequence`、假的 `SheetsReader`／`SheetsWriter`／`AuthGateway`）；真實路徑：`tests/real_google/test_real_export.py`（`real_google` 標記，缺環境變數明確失敗）＋非實作者以兩份真實試算表人工驗證（SC-009、R17 五項假設）；記錄日期、指令、結果數字，沒執行不宣稱完成 | ✅ |
| VII 簡單與本機運作 | 不新增套件、不新增資料庫；只在記憶體保存嘗試；不修改 001～004；`main.py` 只加組裝函式與一行 router | ✅ |
| 技術限制：架構（NON-NEGOTIABLE） | `core/result_export/` 只匯入標準函式庫與 `lecture_quiz.core` 內模組（含 002、004 的核心型別）；`tests/architecture/test_core_is_pure.py` 已涵蓋整個 `core/`；時間只來自已保存的 `received_at` 與 `Clock`（服務層） | ✅ |
| 技術限制：日誌、風格 | `logging` INFO；Google 例外只對應成代碼、不記訊息本文；Google docstring、型別提示；ruff、ruff format、mypy 全過才提交 | ✅ |

**Post-design 重新檢查（Phase 1 後）**：data-model、contracts、quickstart 沒有引入新的違反項目。對既有程式沒有修改，所以不需要 Complexity Tracking 中的「修改已合併功能」項目；僅 `main.py`、`teacher.html`、`app.css`、`tests/SCENARIO_MAP.md`、`tests/conftest.py` 依 `docs/DEVELOPMENT.md` 的子功能擴充約定追加（見下）。

## Project Structure

### Documentation (this feature)

```text
specs/005-result-export/
├── plan.md              # 本檔
├── research.md          # Phase 0：R1～R17 決策與待真實驗證的假設
├── data-model.md        # Phase 1：實體、狀態轉移、演算法、驗證規則
├── quickstart.md        # Phase 1：自動化、真實路徑與人工驗證步驟
├── verification.md      # 實作時建立：驗證紀錄（日期、指令、結果數字）
├── contracts/
│   ├── http-api.md          # X1～X7
│   ├── sync-websocket.md    # 老師快照的 export 欄位
│   └── service-interfaces.md # 005 ↔ 001／002／003／004
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks 產生（NOT created by /speckit-plan）
```

### Source Code (repository root)

```text
src/lecture_quiz/
├── core/
│   └── result_export/              # 005 新增（純函式）
│       ├── __init__.py
│       ├── models.py               # FinalizedEntry、FinalizedQuestion、SubmissionFact、BlankTarget、CurrentCell、OverwriteImpact、WritePlanItem、ResultSnapshot、DiffKind、StructureDifference、StructureCheck、CellCheck、OutcomeStatus、Reconciliation、ExportRow
│       ├── snapshot.py             # snapshot_id_of、build_snapshot（覆寫影響、未寫入題）
│       ├── structure.py            # compare_structure（七類差異）
│       ├── reconcile.py            # reconcile（核對判定，不做結構檢查）
│       └── csv_export.py           # build_rows、render_csv、protect_text
├── app/
│   └── result_export/              # 005 新增
│       ├── __init__.py
│       ├── ports.py                # SheetsWriter、WriteResult（Protocol）
│       ├── models.py               # WriteAttempt、AttemptKind、AttemptStatus、AttemptReason、ExportRejection、Result、PreviewView
│       ├── messages.py             # 錯誤與狀態訊息的集中對照表
│       ├── store.py                # ExportStore（記憶體）、每活動鎖
│       └── service.py              # ExportService（preview、confirm_write、recheck、retry、latest_attempt、start_authorization、download_csv、snapshot_extension）
└── adapters/
    ├── google/
    │   └── sheets_writer.py        # GoogleSheetsWriter：read_cells（userEnteredValue）、write_text_cells（batchUpdate／updateCells）、回應分類
    ├── web/
    │   └── result_export.py        # X1～X7（create_router）
    └── static/
        ├── teacher.html            # 加一個 <section id="export-section">
        ├── css/app.css             # 追加樣式
        └── js/result-export.js     # 預覽、確認、狀態、核對、重試、重新授權、CSV 下載；全部 textContent

tests/
├── unit/core/result_export/        # 快照與覆寫影響、結構比對各類差異、核對、CSV 資料列與跳脫、確定性（含 layout_a／layout_b）
├── unit/app/result_export/         # ExportService + 真 ActivityService + FakeClock + 假 SheetsReader／SheetsWriter／AuthGateway；併發、陳舊快照、冪等、核對三種實況、取消的活動
├── unit/adapters/google/           # test_sheets_writer.py：HttpMockSequence 驗證請求形狀與 4xx／5xx／逾時分類
├── contract/result_export/         # X1～X7 端點、錯誤碼、身分與訊息安全
├── integration/test_export_*.py    # 兩份版面端到端（含寫入後再預覽結構仍相符）、CSV 嚴格解析、日誌不含機敏資訊、005 對活動唯讀
├── architecture/test_static_text_safety.py（擴充涵蓋 result-export.js）
├── real_google/test_real_export.py # real_google 標記，手動執行
├── perf/test_export_latency.py     # perf 標記
└── SCENARIO_MAP.md（追加 005 的 Scenario 對照）
```

**Structure Decision**：沿用 001 的三層 src layout；005 新增 `core/result_export/`、`app/result_export/`、`adapters/google/sheets_writer.py`、`adapters/web/result_export.py`。依 `docs/DEVELOPMENT.md` 的約定，在 `main.py` 的「子功能 router」區塊加一行掛載，並在組裝處（004 之後）建立 `ExportService`；`create_app` 增加可注入的 `export_sheets_writer` 參數供測試使用。檔案配置符合子功能擴充約定。

## Complexity Tracking

> Constitution Check 沒有需要說明理由的違反項目；下列是「與既有設計不同、容易被問」的取捨，列出理由以免實作時反覆。

| 取捨 | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| 005 自己持有每活動一把 asyncio 鎖與「進行中」旗標，Google I/O 在鎖外 | 寫入可能長達數十秒；FR-020 要求一次只有一個寫入，同時 FR-022 要求 CSV 與預覽不受寫回阻擋 | 用 001 的活動鎖：不可重入、會擋住整個活動的操作；整個 I/O 放在鎖內：預覽與 CSV 被卡住 |
| 預覽讀兩次工作表（002 的 `read` 給結構比對、005 的 `userEnteredValue` 給覆寫影響） | 002 的讀取只含 `effectiveValue`，無法分辨公式與文字、數字與文字，覆寫影響會誤判 `SAME` | 修改 002 的 `READ_FIELDS`：會影響 002 已通過的測試與真實驗證，違反「不修改 001～004」 |
| 結構比對自寫 `compare_structure` 分類差異，而不是比較兩個 `StructureSnapshot` 是否相等 | FR-008 要求指出差異類別與位置；`==` 只能得到不相等 | 直接比較：無法滿足 FR-008 |
| 核對（`recheck`）不做結構檢查 | clarify Q2 決定（使用者選 B）；核對只讀取、不改任何儲存格 | 核對前也做結構檢查（建議選項）：被使用者否決；取捨已記在 research R7，畫面必須逐格顯示內容並提醒 |
| 成果快照識別用「已定案輪次編號集合」而非內容雜湊 | 與 spec FR-005 字面一致（有新輪次定案就須重新預覽），最簡單、確定 | 內容雜湊：新輪次沒有成功者時預覽不失效，與 spec 字面不同，可能造成兩組行為分歧 |
