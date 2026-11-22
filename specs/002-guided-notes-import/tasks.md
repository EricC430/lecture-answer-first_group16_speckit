---

description: "002-guided-notes-import 任務清單"
---

# Tasks: Guided Notes 匯入（Google Sheets 學習單）

**Input**: Design documents from `/specs/002-guided-notes-import/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（專案覆寫，憲章 v1.1.0 原則 VI）。

- spec 共有 28 個 Acceptance Scenario（US1 6、US2 5、US3 6、US4 5、US5 4、US6 2），每一個至少對應一個自動化測試；對照表在文末「Scenario 對照表」。
- 測試的 docstring 第一行寫 `Scenario: USn-ASm` 或 `Edge: <名稱>`。
- 測試先寫，並確認在實作前是失敗的（紅燈），把失敗的輸出摘要記在 PR 描述。
- Google OAuth／Sheets／Drive 一律 mock（`HttpMockSequence` 與 Fake 連接埠），預設測試不呼叫真實 Google。真實路徑用 `@pytest.mark.real_google`，手動執行，缺環境變數時明確失敗，不得跳過。
- 手寫 fixture 的檔頭標明「手寫、依 OpenSpec 與課程範本描述」；真實回應 fixture 只在真實驗證後才存在，擷取前不得宣稱入口路徑已驗證。

**Diagrams**: REQUIRED（原則 II）。實作前先確認 `diagrams/002-guided-notes-import-*.puml` 與 PNG 存在（T002）；實作後有一致性驗證任務（T073）。

**Architecture**: REQUIRED（技術限制 4，NON-NEGOTIABLE）。每個 Phase 的實作任務分層列出，相依方向為「轉接層 → 應用層 → 核心」：

- **核心**：`src/lecture_quiz/core/guided_notes_import/`，只能是純函式與不可變資料，只依賴標準函式庫；`parse(snapshot)` 沒有時間參數。
- **應用層**：`src/lecture_quiz/app/guided_notes_import/`。
- **轉接層**：`src/lecture_quiz/adapters/google/`、`src/lecture_quiz/adapters/web/guided_notes_import.py`、`static/js/import.js`。

**⚠ 骨架凍結**（見 [plan.md](plan.md)「相依與時程」）：jacky0407 的骨架 PR 合併前，002 **不得**建立 `pyproject.toml`、`main.py`、`src/`。T001 是整份清單的前置關卡。

**⚠ 共用檔案追加約定**：`main.py` 只加一行 router；`teacher.html` 只加一個區塊；`pyproject.toml` 相依追加在最後；`docs/alignment.md` 只追加在最後；`tests/conftest.py` 只追加 fixture 與參數，不改 001 既有簽章的預設行為。

**⚠ 待真實驗證的假設**（[plan.md](plan.md) 表格）：`drive.file` 足以讀取 Picker 選到的試算表、`GridRange` 結束索引為「不含」、非試算表的錯誤型態、Picker 在 `localhost` 的運作。驗證前不得宣稱成立；T028 是第一個里程碑。

**Organization**: 依 User Story 分組。順序 US1 → US2 → US3（P1，後面的故事需要前面的授權與解析）→ US4 → US5（P2）→ US6（P3）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- 路徑中 `<core>` = `src/lecture_quiz/core/guided_notes_import`，`<app>` = `src/lecture_quiz/app/guided_notes_import`，`<google>` = `src/lecture_quiz/adapters/google`，`<web>` = `src/lecture_quiz/adapters/web/guided_notes_import.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 確認骨架就緒，追加相依與目錄

- [ ] T001 **前置關卡**：確認 001 的骨架 PR 已合併到 `main`，且 002 分支已從 main 接續；檢查 `pyproject.toml`（含 Ruff、mypy 設定）、`src/lecture_quiz/{core,app,adapters}/`、`src/lecture_quiz/main.py` 的 `create_app`、`tests/conftest.py`、`tests/architecture/test_core_is_pure.py` 都存在。任一項缺少就**停止並回報**，不自行建立（骨架凍結）。
- [ ] T002 [P] 確認 `diagrams/002-guided-notes-import-{component,class,sequence}.puml` 與對應 PNG 都存在，且 PNG 不舊於 `.puml`；不符時先執行 `java -jar plantuml.jar "./diagrams/002-*.puml"`（原則 II）。
- [ ] T003 在 `pyproject.toml` 相依列表**最後**追加 `google-api-python-client`、`google-auth`、`google-auth-oauthlib`（核心相依，不放選用 extra）；版本以 `pip index versions <套件>` 查證後釘選並記錄在 PR 描述，不憑記憶。註冊 pytest marker `real_google`，並讓預設 `addopts` 排除它（與 001 的 `perf` 並存）。
- [ ] T004 [P] 建立套件與測試目錄，各放空的 `__init__.py`：`<core>/`、`<app>/`、`src/lecture_quiz/adapters/google/`、`tests/unit/core/guided_notes_import/`、`tests/unit/app/guided_notes_import/`、`tests/unit/adapters/google/`、`tests/contract/guided_notes_import/`、`tests/fixtures/`、`tests/real_google/`。
- [ ] T005 [P] 在 `.env.example` **追加**五個空白設定：`GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_API_KEY`、`GOOGLE_APP_ID`、`OAUTH_REDIRECT_URI`（註解寫明本機固定值 `http://localhost:8000/api/oauth/callback`）；確認 `.gitignore` 已排除 `.env`。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有 User Story 共用的資料型別、連接埠、Fake 與測試輔助

**⚠️ CRITICAL**: 本階段完成前不得開始任何 User Story

### 核心（純函式層）

- [ ] T006 [P] 在 `<core>/models.py` 建立 `@dataclass(frozen=True)` 型別，欄位與規則照 [data-model.md](data-model.md) 原文：`CellRef(row, col)`、`CellValue(number, text, display)`、`MergeRange(first_row, first_col, last_row, last_col)`（皆含）、`SheetSnapshot(spreadsheet_id, sheet_id, sheet_name, row_count, col_count, cells, merges)`、`Question(number, blank_count, is_group)`、`Blank(question_number, sub_index, target)`、`StructureSnapshot(header_number, header_answer, answer_cols, data_start_row, merges, row_numbers, answer_cells)`、`IssueKind`（11 個值：`MISSING_HEADER_NUMBER`、`MISSING_HEADER_ANSWER`、`AMBIGUOUS_HEADER`、`NON_NUMERIC_NUMBER`、`NUMBER_GAP`、`NON_ADJACENT_DUPLICATE`、`SUB_INDEX_MISSING`、`SUB_INDEX_DUPLICATE`、`ORPHAN_SUB_BLANK`、`MISSING_ANSWER_CELL`、`TARGET_OVERLAP`）、`ValidationIssue(kind, at, quoted, hint)`、`ParseResult(ok, questions, blanks, structure, issues)`。座標一律 0 起算；`ok` 為真時 `issues` 為空，為假時 `questions`、`blanks`、`structure` 全空（原子，FR-016）；任何型別都不含題目敘述（FR-008）。每個公開類別與方法有型別提示與 docstring。
- [ ] T007 [P] 擴充 `tests/architecture/test_core_is_pure.py`，把 `src/lecture_quiz/core/guided_notes_import/**/*.py` 納入 `ast` 掃描：匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`googleapiclient`、`google`、`httpx`、`lecture_quiz.app`、`lecture_quiz.adapters` 時失敗；呼叫 `datetime.now`、`datetime.utcnow`、`date.today` 時失敗；另在測試內以一段違規的臨時原始碼確認掃描器確實會失敗（負對照，避免假綠燈）。依據：research R9、技術限制 4。

### 測試輔助與 fixture

- [ ] T008 [P] 建立 `tests/unit/core/guided_notes_import/helpers.py`：`build_snapshot(matrix, merges, *, sheet_name, origin=(0, 0), row_count=None, col_count=None)`，把「文字矩陣＋合併範圍清單」轉成 `SheetSnapshot`；數字用 `float`、文字用 `str`，並能分別表示「數值 1.0」與「文字 `"1"`」；`origin` 用來把整份內容平移。
- [ ] T009 [P] 建立 `tests/fixtures/guided_notes_layouts.py`（檔頭標明「手寫、依 OpenSpec 與課程範本描述」），提供：
  - 版面 A（課程範本題組版）：表頭在第 4 列、題號在 B 欄、作答在 G 欄，前兩題各兩個子空格且題號縱向合併、後兩題各一格 → 預期 4 題 6 格。
  - 版面 B：整體移位、工作表更名、單題與題組混合 → 題數與格數與版面 A 的規則一致，答案位置對應新位置。
  - 單題範本：六題、作答格橫向合併 → 預期 6 題 6 格，位置為合併範圍左上角。
  - 題組變體：相鄰列重複題號（無縱向合併）、夾間隔列、子空格之間夾空白列（縱向合併與逐列重複兩種）。
  - 缺陷 builder：九種缺陷各一份與近似錯誤對照（格式對、內容有缺陷，例如表頭存在但題號跳號）。

### 應用層

- [ ] T010 [P] 在 `<app>/models.py` 建立：`SourceRef(spreadsheet_id, sheet_id)`、`SheetInfo(sheet_id, title)`、`SpreadsheetInfo(spreadsheet_id, title, sheets)`、`SourceSelection(source, sheet_title)`、`ImportRecord(source, sheet_title, blanks, structure, question_numbers)`、`ImportPreview(question_numbers, blanks_per_question, total_questions, total_blanks)`、`ImportOutcome(ok, preview, issues, rejection)`、`ImportRejection` 列舉（`NOT_AUTHORIZED`、`AUTH_DENIED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`NOT_A_SPREADSHEET`、`SHEET_NOT_FOUND`、`SOURCE_NOT_SELECTED`、`READ_FAILED`、`VALIDATION_FAILED`、`ACTIVITY_NOT_FOUND`、`NOT_TEACHER`、`ROUND_STARTED`、`ACTIVITY_CANCELLED`、`STAGE_NOT_PREPARING`、`GATEWAY_REJECTED`、`GOOGLE_NOT_CONFIGURED`、`INVALID_REQUEST`）、與 001 `Outcome` 同形的 `Result[T]`（`ok`、`value`、`rejection`）。服務不拋業務錯誤。
- [ ] T011 [P] 在 `<app>/ports.py` 以 `typing.Protocol` 定義 `AuthGateway`（`start_authorization`、`complete_authorization`、`is_authorized`、`picker_credentials`）與 `SheetsReader`（`inspect`、`read`），簽章照 [contracts/service-interfaces.md](contracts/service-interfaces.md)；所有跨出應用層的 I/O 為 `async`。`Clock` 與 `ActivityGateway`（`stage`、`is_teacher`、`replace_questions`）沿用 001，不重複定義。
- [ ] T012 [P] 在 `<app>/store.py` 建立 `ImportStore`：依活動代碼為 key 的 `sessions`、`selections`、`records`、`locks`（每個活動一把 `asyncio.Lock`，與 001 活動鎖分開）；只在記憶體，不持久化（原則 VII）。
- [ ] T013 在 `<app>/messages.py` 建立固定中文訊息對照表（每個 `ImportRejection` 一則，`IssueKind` 的修正建議於 T053 補齊），儲存格引用截斷在 40 字元；在 `tests/unit/app/guided_notes_import/test_messages.py` 測試每個代碼都有訊息，且訊息不含 token、授權碼、`state`、client secret、檔案路徑、堆疊字樣（FR-022、SC-005；`Edge: 輸入驗證失敗`）。（依賴 T010）
- [ ] T014 [P] 建立 `tests/unit/app/guided_notes_import/fakes.py`：`FakeAuthGateway`、`FakeSheetsReader`（可注入快照、授權狀態、各種拒絕）、`FakeActivityGateway`（行為依 001 契約：`stage`、`is_teacher`、`replace_questions` 只允許老師在準備中、成功回傳新 `version`、被拒時題目不變；可注入「解析後、寫入前階段改變」）。檔頭標明為測試替身。
- [ ] T015 [P] 在 `<google>/config.py` 讀取五個環境變數，**空字串視為未設定**，缺任何一項時匯入相關操作回 `GOOGLE_NOT_CONFIGURED`，不退回離線路徑、不假裝成功；授權範圍常數（`drive.file`）與 `state` 有效期限各只定義在這個檔案。在 `tests/unit/adapters/google/test_config.py` 測試：缺值、空字串、全部齊備三種情況。
- [ ] T016 擴充 `tests/conftest.py`（只追加）：`make_app` 增加選用參數 `auth_gateway`、`sheets_reader`（預設為 Fake），讓契約測試使用 001 的真實 `ActivityService`、`teacher` fixture 與 `FakeClock`，只替換 Google 相關連接埠。（依賴 T014）

**Checkpoint**: 型別、連接埠、Fake 與測試輔助就緒，可以開始 User Story

---

## Phase 3: User Story 1 - 老師授權並選取 Google 試算表與工作表 (Priority: P1) 🎯 MVP

**Goal**: 老師授權、用 Google Picker 選試算表、選定工作表；任何失敗都有看得懂的訊息且活動題目不變。

**Independent Test**: 用含多張工作表的真實 Google 試算表走完「授權 → 選檔 → 選工作表」，再逐一製造取消、拒絕、過期、權限不足、非試算表。

### Tests for User Story 1 (REQUIRED — one or more per Acceptance Scenario) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] 在 `tests/unit/adapters/google/test_auth.py` 測試 `GoogleAuthGateway`（以 `FakeClock` 與假的 token 交換）：`state` 只能用一次、超過有效期限失敗、不符或重複使用時**不交換 token** 並導回 `auth=error`；使用者取消或拒絕 → `auth=denied`；token 只在記憶體、不出現在任何回傳值或日誌（`Scenario: US1-AS3`、`US1-AS4`）。
- [ ] T018 [P] [US1] 在 `tests/unit/adapters/google/test_sheets_inspect.py` 用 `HttpMockSequence`（手寫回應 JSON，標明手寫）測試 `inspect`：先以 Drive `mimeType` 判斷，非 Google 試算表（Google 文件、PDF、XLSX）→ `NOT_A_SPREADSHEET`；是試算表才以欄位遮罩 `properties.title,sheets.properties(sheetId,title,hidden,gridProperties)` 取得工作表清單；多張與單張兩種（`Scenario: US1-AS1`、`US1-AS2`、`US1-AS6`）。
- [ ] T019 [P] [US1] 在 `tests/unit/adapters/google/test_errors.py` 測試 `HttpError` → `ImportRejection` 對應：401 → `AUTH_EXPIRED`、403／404 → `PERMISSION_DENIED`、429／逾時／5xx → `READ_FAILED`；對應結果的訊息不含憑證與內部細節（`Scenario: US1-AS4`；`Edge: 選檔後檔案消失或失去權限`）。
- [ ] T020 [P] [US1] 在 `tests/unit/app/guided_notes_import/test_service_source.py` 以 Fake 連接埠測試：`inspect_spreadsheet` 不改任何狀態；`select_source` 驗證 `sheet_id` 屬於該試算表後才保存、失敗時舊的選擇不變；沒有授權 → `NOT_AUTHORIZED`；取消選檔（沒有任何呼叫）不留下半途來源；授權在流程中途失效時，已選來源保留、重新授權後可直接重試（`Scenario: US1-AS1`、`US1-AS3`、`US1-AS4`、`US1-AS5`；`Edge: 授權在流程中途失效`）。
- [ ] T021 [P] [US1] 在 `tests/contract/guided_notes_import/test_auth_source_api.py` 以 `TestClient` 依 [contracts/http-api.md](contracts/http-api.md) 驗證端點 #1～#6 與 `/oauth/callback`：狀態碼、回應形狀與 302 導回 `auth=ok|denied|error`；`picker-config` 帶 `Cache-Control: no-store` 且只限該活動老師；學生 token、其他活動老師、無 token 一律被拒；`GOOGLE_NOT_CONFIGURED` → 503 且訊息不含變數名稱；**路由表中沒有任何本機檔案上傳端點**（FR-005，`Scenario: US1-AS6`）。

### Implementation for User Story 1

**應用層**

- [ ] T022 [US1] 在 `<app>/service.py` 建立 `ImportService`（建構子注入 `AuthGateway`、`SheetsReader`、`ActivityGateway`、`ImportStore`、`Clock`），實作 `start_auth`、`inspect_spreadsheet`、`select_source`：每個入口先以 `stage(code)`、`is_teacher(code, requester)` 判斷（錯誤代碼依 research R8），`select_source` 驗證 `sheet_id` 屬於該試算表才寫入 `selections`。（依賴 T010～T014）

**轉接層**

- [ ] T023 [P] [US1] 在 `<google>/errors.py` 實作 `HttpError`／逾時 → `ImportRejection` 的對應（T019 的規則）。
- [ ] T024 [US1] 在 `<google>/auth.py` 實作 `GoogleAuthGateway`：授權碼流程（`google-auth-oauthlib`）、一次性且有期限的 `state`、token 只存記憶體（`ImportStore.sessions`）、`picker_credentials` 只回短效 `drive.file` token；不記錄 token、授權碼、`state`、client secret。（依賴 T015、T023）
- [ ] T025 [P] [US1] 在 `<google>/sheets_reader.py` 實作 `GoogleSheetsReader.inspect`：Drive `files.get` 取 `mimeType`，再以 `spreadsheets.get` 與欄位遮罩取工作表清單；以 `asyncio.to_thread` 呼叫同步的 Google 程式庫；只用讀取方法（FR-023）。
- [ ] T026 [US1] 在 `<web>` 實作端點 #1～#6 與 `/oauth/callback`、錯誤轉換（依 http-api 的錯誤碼與狀態碼表，訊息取自 `messages.py`）與請求日誌（只記活動代碼、端點名稱、結果代碼）；在 `main.py` **只加一行** `include_router`。（依賴 T022、T024、T025）

**前端**

- [ ] T027 [US1] 在 `teacher.html` **只加一個**「匯入學習單」區塊，並建立 `static/js/import.js`：按鈕 → `auth/start` → 導向 Google → 回來後依 `?auth=ok|denied|error` 顯示狀態與重新授權入口 → `picker-config` → Google Picker（只允許 Google 試算表 MIME，取消時維持原狀）→ `inspect` → 只有一張工作表時自動 `PUT source` 並顯示名稱，多張時要求老師明確選一張。所有後端與試算表來的文字一律以 `textContent` 輸出。

**真實驗證里程碑**

- [ ] T028 [US1] **里程碑 0（待驗證假設 1）**：以真實 Google 帳號與一份真實試算表，依 [quickstart.md](quickstart.md) 前置條件設定好 `.env`，用 `uvicorn` 啟動後走完「授權 → Picker 選檔 → `inspect`」，確認 `drive.file` 足以讀取 Picker 選到的試算表。把日期、操作與結果填入 quickstart 紀錄表；若讀取失敗，依 [research.md](research.md) R1 的 fallback 評估改用敏感範圍，並在 plan「待真實驗證的假設」註明；**未做之前不得宣稱授權範圍成立**。（依賴 T026、T027）

**Checkpoint**: 老師可以授權、選檔並選定工作表；失敗時題目不變

---

## Phase 4: User Story 2 - 匯入單題學習單並不依賴固定位置 (Priority: P1)

**Goal**: 依「題號」「作答」表頭與合併範圍動態定位單題學習單，不依賴固定列欄或工作表名稱。

**Independent Test**: 六題、作答格橫向合併的單題學習單，與整體移位且工作表更名後的同內容版本，兩份都得到 6 題 6 格，位置各自正確。

### Tests for User Story 2 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [ ] T029 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_numbers.py` 表格驅動測試題號正規化（[research.md](research.md) R5）：接受 `numberValue` 的 1、1.0、`" 1 "`、`"01"`、`"1"`；拒絕 0、-1、1.5、`"1."`、`"第1題"`、`"Q1"`、全形 `"１"`、布林與錯誤值；用明確 ASCII 規則，不使用 `isdigit`（`Scenario: US2-AS4`；`Edge: 題號格式`）。
- [ ] T030 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_parse_single.py` 測試：單題範本 → 6 題 6 格，每題答案位置為橫向合併範圍的左上角（`Scenario: US2-AS1`）；同樣內容以不同 `origin` 平移並更換工作表名稱 → 題數與格數不變、位置對應新位置，且結果不含任何固定座標假設（`Scenario: US2-AS2`；原則 III）。
- [ ] T031 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_parse_header_values.py` 測試：「題號」「作答」前後帶半形與全形空白仍可辨識（`Scenario: US2-AS3`）；題號值為數值 1.0 與文字 `"1"` 都得到題號 1（`Scenario: US2-AS4`）；工作表含題目敘述欄時，`ParseResult` 與其中任何欄位的字串化內容都不含題目敘述文字（`Scenario: US2-AS5`；FR-008）。
- [ ] T032 [P] [US2] 在 `tests/unit/adapters/google/test_sheets_read.py` 用 `HttpMockSequence`（手寫回應 JSON）測試 `read`：欄位遮罩字串為 `sheets(properties(sheetId,title,gridProperties),merges,data(startRow,startColumn,rowData(values(effectiveValue,formattedValue))))`；`startRow`／`startColumn` 位移還原成絕對座標；`rowData` 省略結尾空儲存格；`GridRange` 結束索引「不含」轉成 `MergeRange` 的「含」；`numberValue` 與 `stringValue` 正確區分；工作表標題含單引號時的 `ranges` 跳脫；全程只送出讀取請求（FR-023；`Edge: 同一個格子被兩題指到` 前提）。
- [ ] T033 [P] [US2] 在 `tests/unit/app/guided_notes_import/test_service_import.py` 測試 `import_sheet` 的順序與原子性（[research.md](research.md) R6）：階段與身分 → 讀取 → 解析 → 001 `replace_questions` → 才保存；讀取失敗、解析失敗、001 拒絕三種情況下都不保存、不改既有記錄；成功時只傳題號清單給 001；兩個並行的匯入依序執行，最後成功的一次整份取代（`Edge: 連續快速重複匯入`、`Edge: 解析後、寫入前階段或身分改變`）；多個活動同時存在互不影響。
- [ ] T034 [P] [US2] 在 `tests/contract/guided_notes_import/test_import_api.py` 驗證 `POST /activities/{code}/import`：200 的 `ImportResult` 形狀（含 001 回傳的 `version`）、`SOURCE_NOT_SELECTED`、同一個 `Idempotency-Key` 重送回傳第一次的結果而不重複匯入。

### Implementation for User Story 2

**核心**

- [ ] T035 [P] [US2] 在 `<core>/numbers.py` 實作題號正規化（T029 的規則，明確 ASCII 規則運算式，不用 `isdigit`／寬鬆 `int()`）。
- [ ] T036 [P] [US2] 在 `<core>/headers.py` 實作「找表頭」：文字以 `strip()` 正規化（含全形空白）後與「題號」「作答」完全相同才算；取得題號欄、作答欄範圍（含合併）與資料起始列；不接受同義詞，不以結構猜測。表頭缺少與歧義的回報在 T051 補齊。
- [ ] T037 [US2] 在 `<core>/rows.py` 實作單題路徑：有題號值且作答欄範圍內沒有子編號的列，取作答欄範圍第一欄的儲存格（屬合併範圍則取左上角）為答案位置。（依賴 T035、T036）
- [ ] T038 [US2] 在 `<core>/parser.py` 實作 `GuidedNotesParser.parse(snapshot) -> ParseResult`：串起表頭、逐列分類、組成 `Question`／`Blank` 與 `StructureSnapshot`（表頭位置、`answer_cols`、`data_start_row`、與表頭列及資料區相交的合併範圍、各列題號、答案格映射）；題目敘述欄完全不讀取。（依賴 T037）

**轉接層**

- [ ] T039 [P] [US2] 在 `<google>/sheets_reader.py` 實作 `read`：依 T032 的規則發出一次欄位遮罩請求並轉成 `SheetSnapshot`（保存列欄總數）；轉接層型別不得外洩到核心與應用層。（依賴 T025）

**應用層**

- [ ] T040 [US2] 在 `<app>/service.py` 實作 `import_sheet`：持有該活動的匯入鎖，順序固定為「`stage`／`is_teacher` → `read` → `parse` → `replace_questions`（只傳題號清單）→ 以新的 `ImportRecord` 整份取代舊的」；任何失敗都不寫入。（依賴 T038、T039）

**轉接層**

- [ ] T041 [US2] 在 `<web>` 新增端點 #7 `POST /activities/{code}/import`：處理 `Idempotency-Key`、回傳 `ImportResult`；驗證失敗的 422 格式在 T053 補齊。（依賴 T040）

**Checkpoint**: 單題學習單可匯入，不依賴固定位置

---

## Phase 5: User Story 3 - 匯入題組與單題混合的學習單 (Priority: P1)

**Goal**: 題組算一個競賽題目，每個子空格有精確答案位置，不漏續列、不指向編號格。

**Independent Test**: 原始題組範例得到 4 題 6 格；相鄰重複題號與夾間隔列的變體各匯入一次。

### Tests for User Story 3 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [ ] T042 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_parse_groups.py` 測試：原始題組範例 → 4 題 6 格，第二個子空格被辨識、答案位置為「（n）」右側的作答格而非編號格、編號位於作答表頭涵蓋的欄範圍內（`Scenario: US3-AS1`）；相鄰重複題號與縱向合併得到相同的題數與格數（`Scenario: US3-AS2`）；沒有題號也沒有子空格的間隔列被忽略、不繼承題號（`Scenario: US3-AS3`）；空白題號只在縱向合併範圍內繼承（`Scenario: US3-AS4`）；單題與題組混合，題組只算一題（`Scenario: US3-AS5`）；同一題的兩個子空格之間夾完全空白的列（縱向合併與逐列重複兩種，含合併範圍把間隔列包進去）→ 忽略該列、格數不變（`Scenario: US3-AS6`；FR-026）。
- [ ] T043 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_structure_snapshot.py` 以版面 A、版面 B 測試 `StructureSnapshot` 內容：表頭位置、`answer_cols`、`data_start_row`、僅含相交者的合併範圍、各列題號、答案格映射（FR-024；供 005 寫回前比對）。
- [ ] T044 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_sub_index_format.py` 測試子編號被接受的格式：「（1）」「(1)」（半形或全形括號、半形數字），且必須位於作答表頭涵蓋的欄範圍內（`Edge: 子編號與作答格的位置`；拒絕的變體在 T048 測試）。

### Implementation for User Story 3

**核心**

- [ ] T045 [US3] 擴充 `<core>/rows.py`：空白題號在縱向合併範圍內繼承左上角的值、範圍外不繼承；在作答欄範圍內以 `^[（(][0-9]+[）)]$` 辨識子編號；作答格為編號儲存格（含其合併範圍）**右側緊鄰**的格子，屬合併範圍取左上角，右側超出工作表列欄範圍視為缺少答案格；沒有題號值也沒有子編號的列一律略過（FR-026）。（依賴 T037）
- [ ] T046 [US3] 建立 `<core>/validator.py` 的分組：忽略空白列後，**相鄰**且題號值相同的列歸為同一題（涵蓋縱向合併與逐列重複兩種表示），產生 `Question`（`blank_count`、`is_group`）與帶 `sub_index` 的 `Blank`。（依賴 T045）
- [ ] T047 [US3] 擴充 `<core>/parser.py`：串接 `validator`，並讓 `StructureSnapshot` 涵蓋題組的子空格答案格映射。（依賴 T046）

**Checkpoint**: 單題與題組混合的學習單可以正確匯入

---

## Phase 6: User Story 4 - 學習單有問題時整份拒絕並指出位置 (Priority: P2)

**Goal**: 缺陷學習單整份拒絕、指出列欄與原因；先前成功匯入的資料不變。

**Independent Test**: 每種缺陷各一份負面學習單，先成功匯入合法的，再依序匯入負面的，確認每次都被拒絕且既有資料不變。

### Tests for User Story 4 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [ ] T048 [P] [US4] 在 `tests/unit/core/guided_notes_import/test_parse_defects.py` 測試（**先寫、先確認失敗並記錄**）：缺「題號」、缺「作答」、兩者皆缺、空工作表（`Scenario: US4-AS1`）；兩個表頭區塊、同列重複表頭、「題號」「作答」不在同一列（`Scenario: US4-AS2`；`Edge: 兩組表頭但只有一組有合法題目`）；題號跳號、非相鄰重複題號、子編號缺漏、子編號重複、非數字題號（`Scenario: US4-AS3`）；孤立子空格、缺少答案格（含右側無儲存格與題號存在卻找不到任何作答格）、目標格重疊（`Scenario: US4-AS4`）；被拒絕的子編號變體：全形數字「（１）」、括號內夾空白；**近似錯誤對照**（格式與關鍵字都對、內容有缺陷，例如表頭存在但題號跳號）必須被拒絕；多個缺陷同時存在時**全部收集**回報；`ok` 為假時 `questions`、`blanks`、`structure` 為空（FR-016）。（SC-004）
- [ ] T049 [P] [US4] 在 `tests/unit/app/guided_notes_import/test_import_rejection.py` 測試：先成功匯入一份合法學習單，再匯入各種缺陷學習單，每次都被整份拒絕，`FakeActivityGateway.replace_questions` 沒有被呼叫，既有的 `ImportRecord` 與題號清單完全不變（`Scenario: US4-AS5`）；解析成功但 001 拒絕（`GATEWAY_REJECTED`）時，002 保存的資料也不變（`Edge: 解析後、寫入前階段或身分改變`）。
- [ ] T050 [P] [US4] 在 `tests/contract/guided_notes_import/test_validation_api.py` 驗證 422 `VALIDATION_FAILED` 的 `issues` 形狀：`kind`、`row`、`col`（1 起算，欄以 A、B… 字母表示，無位置時為 `null`）、`quoted`（≤40 字元）、`hint`；回應不含堆疊、檔案路徑或憑證；含 `<script>` 之類字樣的儲存格文字原樣當純文字回傳（FR-022、SC-004；`Edge: 不可信的儲存格文字`）。

### Implementation for User Story 4

**核心**

- [ ] T051 [US4] 補完 `<core>/headers.py` 的問題回報：缺「題號」、缺「作答」、歧義（多個表頭區塊、同列重複、不在同一列）各回對應的 `ValidationIssue`（`MISSING_HEADER_NUMBER`、`MISSING_HEADER_ANSWER`、`AMBIGUOUS_HEADER`）。
- [ ] T052 [US4] 補完 `<core>/validator.py` 的整體檢查：`NON_NUMERIC_NUMBER`（只檢查題號欄的資料列，題號欄空白不算）、`NUMBER_GAP`（依出現順序必須是 1, 2, 3…）、`NON_ADJACENT_DUPLICATE`、`SUB_INDEX_MISSING`、`SUB_INDEX_DUPLICATE`（題組子編號從 1 連續不重複）、`ORPHAN_SUB_BLANK`、`MISSING_ANSWER_CELL`、`TARGET_OVERLAP`（指出兩處）；錯誤全部收集，任何問題都讓 `ok = False` 且不產生任何題目。（依賴 T046、T051）

**應用層與轉接層**

- [ ] T053 [US4] 在 `<app>/messages.py` 為每個 `IssueKind` 補上老師可照做的修正建議；在 `<web>` 把 `ValidationIssue` 轉成 http-api 的 `issues`（1 起算列號、欄字母、`quoted` 截斷 40 字元）。（依賴 T052）

**前端**

- [ ] T054 [US4] 在 `static/js/import.js` 以表格呈現錯誤清單（列、欄、原因、修正建議），全部以 `textContent` 輸出；授權與讀取類錯誤顯示固定訊息與下一步。

**Checkpoint**: 每種缺陷都被整份拒絕並指出位置，既有資料不變

---

## Phase 7: User Story 5 - 老師看到匯入預覽並可在準備中重新匯入 (Priority: P2)

**Goal**: 匯入成功後顯示題號、各題空格數、總題數與總空格數；準備中可整份替換；保存來源映射與匯入時結構供 005。

**Independent Test**: 匯入混合範例得到「4 題、6 格」與每題空格數；再匯入另一份合法學習單，舊結果整份被取代。

### Tests for User Story 5 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [ ] T055 [P] [US5] 在 `tests/unit/app/guided_notes_import/test_preview.py` 測試：混合範例 → 「4 題、6 格」，`blanks_per_question` 為 {1: 2, 2: 2, 3: 1, 4: 1}（`Scenario: US5-AS1`）；題組有多個子空格時總題數只算一題、總格數按子空格累計（`Scenario: US5-AS3`；FR-018）。
- [ ] T056 [P] [US5] 在 `tests/unit/app/guided_notes_import/test_reimport.py` 測試：準備中改選另一份合法學習單 → 新結果整份取代舊結果，`ImportRecord` 與傳給 001 的題號清單都沒有舊題目的殘餘（`Scenario: US5-AS2`）；重新匯入同一份試算表且內容已修正 → 依新內容更新（`Scenario: US5-AS4`）；兩個活動各自的 `ImportRecord` 互不影響（FR-024）。
- [ ] T057 [P] [US5] 在 `tests/contract/guided_notes_import/test_import_summary_api.py` 驗證 `GET /activities/{code}/import`：沒有匯入過回 `{"imported": false}`，有則回與 `POST` 相同形狀的 `ImportResult`（頁面重新整理恢復預覽）；`get_import_record` 為唯讀，修改回傳物件不影響 `ImportStore`；學生看不到來源映射與結構（原則 V）。

### Implementation for User Story 5

**應用層**

- [ ] T058 [US5] 在 `<app>/service.py` 實作 `ImportPreview` 的建立、`get_import_summary(code, requester)`、`get_import_record(code)`（給 005，唯讀，回傳不可變物件）。（依賴 T040）

**轉接層**

- [ ] T059 [US5] 在 `<web>` 新增端點 #8 `GET /activities/{code}/import`。（依賴 T058）

**前端**

- [ ] T060 [US5] 在 `static/js/import.js` 顯示預覽（題號清單、各題空格數、總題數、總空格數）、頁面重新整理時以 #8 恢復、準備中可改選並重新匯入。

**Checkpoint**: 老師可核對匯入結果，005 可取得來源映射與結構

---

## Phase 8: User Story 6 - 第一輪開始後鎖定題目來源 (Priority: P3)

**Goal**: 第一輪開始後拒絕更換來源、重新匯入與修改題目定義；身分與階段的閘門一致。

**Independent Test**: 讓活動進入第一輪開始後的狀態，嘗試更換試算表與重新匯入，兩者都被拒絕，來源映射與既有提交不變。

### Tests for User Story 6 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [ ] T061 [P] [US6] 在 `tests/unit/app/guided_notes_import/test_lock_after_round.py` 測試：001 階段為搶答中、結果未定案、結果已定案、已結束時，`select_source` 與 `import_sheet` 都回 `ROUND_STARTED`，`ImportRecord` 與既有提交不變（`Scenario: US6-AS1`）；002 不提供任何修改題號、空格數、答案位置的端點（對 `main.py` 路由表掃描），且透過 001 `replace_questions` 的修改被拒、題目定義不變（`Scenario: US6-AS2`）；已取消回 `ACTIVITY_CANCELLED`，其他非準備中階段回 `STAGE_NOT_PREPARING`（`Edge: 活動不在「準備中」`）。
- [ ] T062 [P] [US6] 在 `tests/contract/guided_notes_import/test_identity_gate.py` 測試每個端點（#1、#3～#8）：非老師、其他活動的老師、不存在的活動代碼都被拒絕且不更動任何題目（`Edge: 非老師的請求`、`Edge: 活動代碼不存在`；FR-025）；解析成功但 001 因階段剛好改變而拒絕 → `GATEWAY_REJECTED`、001 題目與 002 保存的資料都不變。

### Implementation for User Story 6

**應用層**

- [ ] T063 [US6] 檢查 `<app>/service.py` 每個入口（`start_auth`、`inspect_spreadsheet`、`select_source`、`import_sheet`、`get_import_summary`、`get_import_record`）都先查 `stage`／`is_teacher` 並依 research R8 回對應代碼；缺漏補上。不需要 002 自己維護「已鎖定」狀態，鎖定完全由 001 的 `stage()` 與 `replace_questions` 決定。（依賴 T058）

**前端**

- [ ] T064 [US6] 在 `static/js/import.js` 依 001 的活動快照在階段不是準備中時停用匯入區塊，並顯示「搶答已開始，題目不可更動」（已取消時顯示「活動已取消」）。

**Checkpoint**: 所有 User Story 完成

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的驗證、真實路徑與品質關卡

- [ ] T065 [P] 在 `tests/integration/test_logging_guided_notes_import.py` 以 `caplog` 檢查日誌（技術限制 3）：走完授權、匯入成功與各種失敗後，日誌只含活動代碼、端點名稱、結果代碼、題數與格數、001 版本；**不含** token、授權碼、`state`、client secret、試算表標題與儲存格內容；程式碼中沒有 `print` 日誌。
- [ ] T066 [P] 在 `tests/unit/core/guided_notes_import/test_parse_scale.py` 測試 50 題、數百列學習單的解析結果正確（SC-006 的前提；不以 mock 的耗時冒充真實耗時，真實秒數在 T071 記錄）。
- [ ] T067 [P] 在 `tests/integration/test_import_two_layouts.py` 以版面 A、版面 B（原則 III、SC-003）走入口：`TestClient` → 真實 `GoogleSheetsReader`（`HttpMockSequence` 餵入手寫的 `spreadsheets.get` 回應 JSON，標明手寫）→ `parse` → 001 `ActivityService`，驗證兩份版面都得到正確題數、格數與答案位置、整體移位後結果一致（`Scenario: US2-AS2`、`US3-AS1`、`US5-AS1`）。
- [ ] T068 [P] 建立 `scripts/capture_real_fixture.py`：把真實 `spreadsheets.get` 回應去識別化（刪除標題、帳號、檔案 ID）後存成 `tests/fixtures/real/*.json`；憑證與輸出只在本機，不入版控的內容不得提交。
- [ ] T069 [P] 建立 `tests/real_google/test_real_import.py`，標記 `@pytest.mark.real_google`，明確指定真實轉接器（不跟隨預設的 Fake）；缺少任何 Google 環境變數時**明確失敗**並說明缺什麼，不跳過、不退回離線路徑。預設 `pytest` 不執行它。
- [ ] T070 在 [quickstart.md](quickstart.md) B 區補一步「選只有一張工作表的試算表 → 自動選用並顯示名稱」（`Scenario: US1-AS2`，前端行為無自動化測試，以人工驗證涵蓋），並把 US1-AS5「選檔取消」對應到 B-3。
- [ ] T071 **真實路徑驗證（SC-009，合併前必做）**：EricC430 以兩份版面不同的真實 Google 試算表，依 quickstart B-1～B-13 各走一次，記錄日期、操作、結果數字與 SC-006 的「確認工作表到看見預覽」秒數，填入 quickstart 紀錄表；憑證只在本機，不貼進 repo、Issue、PR。（依賴 T074）
- [ ] T072 T071 通過後執行 T068 擷取兩份版面的真實回應，新增「JSON → 轉接層 → 解析」的入口測試，確認 `GridRange` 結束索引「不含」的假設，並把假設 1～4 的驗證結果寫回 plan「待真實驗證的假設」。擷取之前不得宣稱入口路徑已驗證。（依賴 T071）
- [ ] T073 程式碼與圖表一致性驗證：逐一比對 `diagrams/002-guided-notes-import-{component,class,sequence}.puml` 與實作（`ImportService` 的方法、`AuthGateway`／`SheetsReader` 的方法、`ImportRecord` 的欄位——類別圖目前寫 `sourceMapping`，data-model 與實作用 `blanks`，需同步；`IssueKind` 的值）。有差異時先更新圖表並重新轉出 PNG（原則 II）。
- [ ] T074 執行全部自動化測試 `pytest -m "not real_google"`，並以 `-v` 確認核心、應用層、轉接層（`HttpMockSequence`）、HTTP 契約、架構純度、日誌各自有項目、沒有任何一類是 0 筆；記錄日期、指令與通過／失敗／略過數字（原則 VI）。
- [ ] T075 執行 `ruff check .`、`ruff format --check .`、`mypy src`，全部通過並記錄結果（技術限制 2）。
- [ ] T076 由非實作者（jacky0407）依 [quickstart.md](quickstart.md) B 區做人工驗證，記錄日期、每一步操作與結果於 quickstart 紀錄表並簽名（原則 VI）。
- [ ] T077 追蹤 001 的開發用 seed API（`adapters/web/dev_seed.py`、`LECTURE_QUIZ_DEV_SEED`、`tests/integration/test_dev_seed.py`、前端「放入假題目」按鈕）：依 001 plan 在 002 合併後的第一個 PR 移除；因檔案屬 001，先與 jacky0407 協調是在本 PR 一併移除還是另開 PR，並在 PR 描述記錄結論。
- [ ] T078 更新 `CLAUDE.md`「專案現況」：補上 `pytest -m real_google` 的手動執行方式與 002 的三層路徑；再用全新 clone 在乾淨的 venv 重跑安裝與 `pytest`，確認不依賴任何本機未提交的檔案（規章第 9 節）。
- [ ] T079 開 PR 前確認：文末 Scenario 對照表的 28 個項目都有已通過的測試；spec 的 Traceability 與 `docs/alignment.md` 沒有新增偏離項；quickstart 紀錄表沒有空白的已執行項目；PR 描述列出尚未驗證的假設（若有）。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：T001 是前置關卡，未通過不得繼續；其餘可並行。
- **Foundational (Phase 2)**：依賴 Phase 1，**阻擋所有 User Story**。
- **User Stories**：
  - US1 → US2 → US3 為順序依賴：US2 需要 US1 的授權與 `SheetsReader`；US3 擴充 US2 的 `rows.py`、`parser.py`。
  - US4 依賴 US3 的分組（`validator.py`）；US5 依賴 US2 的 `import_sheet`（US4 完成後預覽才能涵蓋拒絕路徑，但不是硬性依賴）；US6 依賴 US5 的 `get_import_record` 以檢查入口。
- **Polish**：依賴所有想要的 User Story；T071 依賴 T074，T072 依賴 T071。

### Within Each User Story

- 測試先寫並確認失敗，再實作。
- 核心 → 應用層 → 轉接層 → 前端。
- 同一檔案的任務（`rows.py`、`validator.py`、`parser.py`、`service.py`、`import.js`、`messages.py`）不可並行。

### Parallel Opportunities

- Phase 1：T002、T004、T005。
- Phase 2：T006～T012、T014、T015（T013 依賴 T010）。
- 每個故事內標 [P] 的測試可並行（不同檔案）。
- US1 的 T023、T025；US2 的 T035、T036、T039。
- Polish：T065～T070。

---

## Parallel Example: User Story 2

```bash
# 同時撰寫 US2 的測試（不同檔案）：
Task: "test_numbers.py（T029）"
Task: "test_parse_single.py（T030）"
Task: "test_parse_header_values.py（T031）"
Task: "test_sheets_read.py（T032）"

# 同時實作核心（不同檔案）：
Task: "<core>/numbers.py（T035）"
Task: "<core>/headers.py（T036）"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2。
2. US1（含 T028 真實驗證里程碑，確認授權範圍成立）→ US2 → US3：完成這三個即可匯入單題與題組學習單，是可展示的最小版本。
3. **停下來驗證**：用兩份版面學習單走入口測試（T067）。

### Incremental Delivery

1. 加 US4（缺陷拒絕）→ 加 US5（預覽與重新匯入，005 需要）→ 加 US6（鎖定）。
2. 每個故事完成後都跑 `pytest -m "not real_google"`，不得破壞前一個故事。
3. 最後做 Polish 與真實路徑驗證；真實驗證通過後才擷取真實 fixture。

### Parallel Team Strategy

- 實作者 EricC430 負責全部任務；jacky0407 負責 T001 的前置（骨架 PR）、T076 非實作者人工驗證與 T077 的協調。
- 與 005 的介面：`ImportRecord`（`blanks`、`structure`、`source`）與 `get_import_record` 在 US5 完成後穩定，通知 005 的實作者。

---

## Scenario 對照表

| Scenario | 對應測試任務 |
|---|---|
| US1-AS1 | T018、T020、T067（人工 T071） |
| US1-AS2 | T018（自動選用為前端行為，人工 T070、T071） |
| US1-AS3 | T017、T020、T021 |
| US1-AS4 | T017、T019、T020 |
| US1-AS5 | T020（人工 T070、T071） |
| US1-AS6 | T018、T021 |
| US2-AS1 | T030 |
| US2-AS2 | T030、T067 |
| US2-AS3 | T031 |
| US2-AS4 | T029、T031 |
| US2-AS5 | T031、T033 |
| US3-AS1 | T042、T067 |
| US3-AS2 | T042 |
| US3-AS3 | T042 |
| US3-AS4 | T042 |
| US3-AS5 | T042 |
| US3-AS6 | T042 |
| US4-AS1 | T048 |
| US4-AS2 | T048 |
| US4-AS3 | T048 |
| US4-AS4 | T048 |
| US4-AS5 | T049 |
| US5-AS1 | T055、T067 |
| US5-AS2 | T056 |
| US5-AS3 | T055 |
| US5-AS4 | T056 |
| US6-AS1 | T061 |
| US6-AS2 | T061 |

**Edge Case 對照**：授權中途失效 → T020；選檔後檔案消失 → T019；子編號與作答格位置 → T044、T048；題號格式 → T029；同一格被兩題指到 → T048；非相鄰重複 → T048；非老師、活動不存在、非準備中 → T061、T062；解析後寫入前階段改變 → T033、T049、T062；連續快速重複匯入 → T033；輸入驗證失敗與訊息不含內部細節 → T013、T050；不可信的儲存格文字 → T050、T054；讀取期間老師編輯試算表（以一次讀取為準，匯入後不自動更新）→ T033。

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 實作前先確認測試是失敗的；負面案例（T048）與負對照（T007）要真的會失敗，才能相信測試。
- 預設測試不得呼叫真實 Google；任何真實呼叫都必須明確標記並指定真實轉接器。
- 沒有實際執行過的指令，不得在 quickstart 紀錄表、PR 或任務清單寫成已通過。
- Commit after each task or logical group；`docs/alignment.md` 只追加。
