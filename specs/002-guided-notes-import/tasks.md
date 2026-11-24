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
- **轉接層**：`src/lecture_quiz/adapters/google/`、`src/lecture_quiz/adapters/web/guided_notes_import.py`、`src/lecture_quiz/adapters/static/js/import.js`。

**⚠ 骨架凍結**（見 [plan.md](plan.md)「相依與時程」）：jacky0407 的骨架 PR 合併前，002 **不得**建立 `pyproject.toml`、`main.py`、`src/`；且 001 的活動建立、老師 token、`replace_questions`、開輪與取消完成之前也不開工（2026-11-22 決定：等相依完成再開始，不以 Fake 先行）。T001 是整份清單的前置關卡。

**⚠ 共用檔案追加約定**：`main.py` 只做最小追加（一行 router，加上 `create_app` 的兩個選用注入參數，見 T026）；`<static>/teacher.html` 只加一個區塊；`pyproject.toml` 相依追加在最後；`__main__.py` 只在 `uvicorn.run` 追加 `env_file=".env"`（T015）；`docs/alignment.md` 只追加在最後；`tests/conftest.py` 只追加 fixture 與參數，不改 001 既有簽章的預設行為。

**⚠ 待真實驗證的假設**（[plan.md](plan.md) 表格）：`drive.file` 足以讀取 Picker 選到的試算表、`GridRange` 結束索引為「不含」、非試算表的錯誤型態、Picker 在 `localhost` 的運作。驗證前不得宣稱成立；T028 是第一個里程碑。

**Organization**: 依 User Story 分組。順序 US1 → US2 → US3（P1，後面的故事需要前面的授權與解析）→ US4 → US5（P2）→ US6（P3）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- 路徑中 `<core>` = `src/lecture_quiz/core/guided_notes_import`，`<app>` = `src/lecture_quiz/app/guided_notes_import`，`<google>` = `src/lecture_quiz/adapters/google`，`<web>` = `src/lecture_quiz/adapters/web/guided_notes_import.py`，`<static>` = `src/lecture_quiz/adapters/static`（`<static>/teacher.html`、`<static>/js/import.js`）

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 確認骨架就緒，追加相依與目錄

- [X] T001 **前置關卡（等相依完成再開始）**：確認以下兩項都已完成，在 `main` 或 002 所接續的 001 分支上都可以，**未完成就停止並回報，不開工、不自行建立**：(1) 001 的骨架 PR（#14，2026-11-23 已合併）已合併，且 002 分支已從該基底接續；(2) 001 的 `ActivityService` 已實作 002 契約測試與真實驗證會用到的功能：建立活動與老師 token（001 US1）、`replace_questions`（001 tasks T043 對應的實作）、開輪與取消（001 US3、US4，US6 測試需要）。骨架檢查： `pyproject.toml`（含 Ruff、mypy 設定）、`src/lecture_quiz/{core,app,adapters}/`、`src/lecture_quiz/main.py` 的 `create_app`、`tests/conftest.py`、`tests/architecture/test_core_is_pure.py` 都存在。任一項缺少就**停止並回報**，不自行建立（骨架凍結）。
- [X] T002 [P] 確認 `diagrams/002-guided-notes-import-{component,class,sequence}.puml` 與對應 PNG 都存在，且 PNG 不舊於 `.puml`；不符時先執行 `java -jar plantuml.jar "./diagrams/002-*.puml"`（原則 II）。
- [X] T003 在 `pyproject.toml` 相依列表**最後**追加 `google-api-python-client`、`google-auth`、`google-auth-oauthlib`（核心相依，不放選用 extra）；版本以 `pip index versions <套件>` 查證後釘選並記錄在 PR 描述，不憑記憶。註冊 pytest marker `real_google`，並讓預設 `addopts` 排除它：`addopts` 合併為單一表達式 `-m "not perf and not real_google"`（001 已有 `-m 'not perf'`；命令列再給 `-m` 會**覆蓋**它，所以指令一律用 `not real_google and not perf`）。
- [X] T004 [P] 建立套件與測試目錄，各放空的 `__init__.py`：`<core>/`、`<app>/`、`src/lecture_quiz/adapters/google/`、`tests/unit/core/guided_notes_import/`、`tests/unit/app/guided_notes_import/`、`tests/unit/adapters/google/`、`tests/contract/guided_notes_import/`、`tests/fixtures/`、`tests/real_google/`。
- [X] T005 [P] 在 `.env.example` **追加**五個空白設定：`GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_API_KEY`、`GOOGLE_APP_ID`、`OAUTH_REDIRECT_URI`（註解寫明本機固定值 `http://localhost:8000/api/oauth/callback`）；確認 `.gitignore` 已排除 `.env`。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有 User Story 共用的資料型別、連接埠、Fake 與測試輔助

**⚠️ CRITICAL**: 本階段完成前不得開始任何 User Story

### 核心（純函式層）

- [X] T006 [P] 在 `<core>/models.py` 建立 `@dataclass(frozen=True)` 型別，欄位與規則照 [data-model.md](data-model.md) 原文：`CellRef(row, col)`、`CellValue(number, text, display)`、`MergeRange(first_row, first_col, last_row, last_col)`（皆含）、`SheetSnapshot(spreadsheet_id, sheet_id, sheet_name, row_count, col_count, cells, merges)`、`Question(number, blank_count, is_group)`、`Blank(question_number, sub_index, target)`、`StructureSnapshot(header_number, header_answer, answer_cols, data_start_row, merges, row_numbers, answer_cells)`、`IssueKind`（11 個值：`MISSING_HEADER_NUMBER`、`MISSING_HEADER_ANSWER`、`AMBIGUOUS_HEADER`、`NON_NUMERIC_NUMBER`、`NUMBER_GAP`、`NON_ADJACENT_DUPLICATE`、`SUB_INDEX_MISSING`、`SUB_INDEX_DUPLICATE`、`ORPHAN_SUB_BLANK`、`MISSING_ANSWER_CELL`、`TARGET_OVERLAP`）、`ValidationIssue(kind, at, quoted, hint)`、`ParseResult(ok, questions, blanks, structure, issues)`。座標一律 0 起算；`ok` 為真時 `issues` 為空，為假時 `questions`、`blanks`、`structure` 全空（原子，FR-016）；任何型別都不含題目敘述（FR-008）。每個公開類別與方法有型別提示與 docstring。
- [X] T007 [P] 擴充 `tests/architecture/test_core_is_pure.py`，把 `src/lecture_quiz/core/guided_notes_import/**/*.py` 納入 `ast` 掃描：匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`googleapiclient`、`google`、`httpx`、`lecture_quiz.app`、`lecture_quiz.adapters` 時失敗；呼叫 `datetime.now`、`datetime.utcnow`、`date.today` 時失敗；另在測試內以一段違規的臨時原始碼確認掃描器確實會失敗（負對照，避免假綠燈）。依據：research R9、技術限制 4。

### 測試輔助與 fixture

- [X] T008 [P] 建立 `tests/unit/core/guided_notes_import/helpers.py`：`build_snapshot(matrix, merges, *, sheet_name, origin=(0, 0), row_count=None, col_count=None)`，把「文字矩陣＋合併範圍清單」轉成 `SheetSnapshot`；數字用 `float`、文字用 `str`，並能分別表示「數值 1.0」與「文字 `"1"`」；`origin` 用來把整份內容平移。
- [X] T009 [P] 建立 `tests/fixtures/guided_notes_layouts.py`（檔頭標明「手寫、依 OpenSpec 與課程範本描述」），提供：
  - 版面 A（課程範本題組版）：表頭在第 4 列、題號在 B 欄、作答在 G 欄，前兩題各兩個子空格且題號縱向合併、後兩題各一格 → 預期 4 題 6 格。
  - 版面 B：整體移位、工作表更名、單題與題組混合 → 題數與格數與版面 A 的規則一致，答案位置對應新位置。
  - 單題範本：六題、作答格橫向合併 → 預期 6 題 6 格，位置為合併範圍左上角。
  - 題組變體：相鄰列重複題號（無縱向合併）、夾間隔列、子空格之間夾空白列（縱向合併與逐列重複兩種）。
  - 缺陷 builder：九種缺陷各一份與近似錯誤對照（格式對、內容有缺陷，例如表頭存在但題號跳號）。

### 應用層

- [X] T010 [P] 在 `<app>/models.py` 建立：`SourceRef(spreadsheet_id, sheet_id)`、`SheetInfo(sheet_id, title)`、`SpreadsheetInfo(spreadsheet_id, title, sheets, auto_select_sheet_id)`、`SourceSelection(source, sheet_title)`、`ImportRecord(source, sheet_title, blanks, structure, question_numbers)`、`ImportPreview(question_numbers, blanks_per_question, total_questions, total_blanks)`、`ImportOutcome(ok, preview, issues, rejection)`、`ImportRejection` 列舉（`NOT_AUTHORIZED`、`AUTH_DENIED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`NOT_A_SPREADSHEET`、`SHEET_NOT_FOUND`、`SOURCE_NOT_SELECTED`、`READ_FAILED`、`VALIDATION_FAILED`、`ACTIVITY_NOT_FOUND`、`NOT_TEACHER`、`ROUND_STARTED`、`ACTIVITY_CANCELLED`、`STAGE_NOT_PREPARING`、`GATEWAY_REJECTED`、`GOOGLE_NOT_CONFIGURED`、`INVALID_REQUEST`）、與 001 `Outcome` 同形的 `Result[T]`（`ok`、`value`、`rejection`）。服務不拋業務錯誤。`ACTIVITY_GONE`（410）不是獨立列舉值：它是 `ACTIVITY_NOT_FOUND` 在 HTTP 層、請求帶 token 時依 001 慣例的對外代碼與狀態碼，由 `<web>` 的錯誤轉換決定（見 [contracts/http-api.md](contracts/http-api.md)）。
- [X] T011 [P] 在 `<app>/ports.py` 以 `typing.Protocol` 定義 `AuthGateway`（`start_authorization`、`complete_authorization`、`is_authorized`、`picker_credentials`）與 `SheetsReader`（`inspect`、`read`），簽章照 [contracts/service-interfaces.md](contracts/service-interfaces.md)；所有跨出應用層的 I/O 為 `async`（`ActivityGateway` 除外：依已合併的 001 `src/lecture_quiz/app/activity/ports.py`，`stage`、`is_teacher` 是**同步**方法，只有 `replace_questions` 是 `async`；002 的 Fake 與呼叫端照此，不得 `await` 同步方法）。`Clock` 與 `ActivityGateway`（`stage`、`is_teacher`、`replace_questions`）沿用 001，不重複定義。
- [X] T012 [P] 在 `<app>/store.py` 建立 `ImportStore`：依活動代碼為 key 的 `sessions`、`selections`、`records`、`locks`（每個活動一把 `asyncio.Lock`，與 001 活動鎖分開）；只在記憶體，不持久化（原則 VII）。
- [X] T013 在 `<app>/messages.py` 建立固定中文訊息對照表（每個 `ImportRejection` 一則，`IssueKind` 的修正建議於 T053 補齊），儲存格引用截斷在 40 字元；在 `tests/unit/app/guided_notes_import/test_messages.py` 測試每個代碼都有訊息，且訊息不含 token、授權碼、`state`、client secret、檔案路徑、堆疊字樣（FR-022、SC-005；`Edge: 輸入驗證失敗`）。（依賴 T010）
- [X] T014 [P] 建立 `tests/unit/app/guided_notes_import/fakes.py`：`FakeAuthGateway`、`FakeSheetsReader`（可注入快照、授權狀態、各種拒絕）、`FakeActivityGateway`（行為依 001 契約：`stage`、`is_teacher`、`replace_questions` 只允許老師在 `PREPARING` 與 `JOINING`（第一輪開始前）、成功回傳新 `version`、被拒時題目不變；可注入「解析後、寫入前階段改變」）。檔頭標明為測試替身。
- [X] T015 [P] 在 `<google>/config.py` 讀取五個環境變數，**空字串視為未設定**，缺任何一項時匯入相關操作回 `GOOGLE_NOT_CONFIGURED`，不退回離線路徑、不假裝成功；`config.py` 只讀 `os.environ`，`.env` 由 `python -m lecture_quiz` 載入：在 001 的 `src/lecture_quiz/__main__.py` 的 `uvicorn.run(...)` **只追加** `env_file=".env"`（已查證 uvicorn 0.54.0 的 `Config` 有此參數並呼叫 `load_dotenv`；`.env` 不存在時的行為實作時實測，不憑記憶）；**不要**改用 `uvicorn ... --env-file`，因為會繞過 `__main__.py` 的 `log_config=None`、`access_log=False`，uvicorn 預設 access log 會把 `/api/oauth/callback?code=…&state=…` 的授權碼與 `state` 寫進日誌（FR-022、技術限制 3）；授權範圍常數（`drive.file`）與 `state` 有效期限各只定義在這個檔案。在 `tests/unit/adapters/google/test_config.py` 測試：缺值、空字串、全部齊備三種情況；在 `tests/unit/adapters/google/test_launch.py` 以替身取代 `uvicorn.run`，斷言 `__main__.main()` 傳入 `env_file=".env"`、`log_config=None`、`access_log=False`（防止啟動方式退回會記錄授權碼的設定；`Edge: 輸入驗證失敗`、FR-022）。
- [X] T016 擴充 `tests/conftest.py`（只追加）：新增預設為 Fake 的 `fake_auth_gateway`、`fake_sheets_reader` fixture，並讓契約測試透過既有的 `make_app(**kwargs)`（001 會把多餘參數轉給 `create_app`）傳入 `import_auth_gateway=`、`import_sheets_reader=`，使用 001 的真實 `ActivityService`、`teacher` fixture 與 `FakeClock`，只替換 Google 相關連接埠。不改 001 既有 fixture 的預設行為。（依賴 T014；`create_app` 的參數由 T026 加入）

**Checkpoint**: 型別、連接埠、Fake 與測試輔助就緒，可以開始 User Story

---

## Phase 3: User Story 1 - 老師授權並選取 Google 試算表與工作表 (Priority: P1) 🎯 MVP

**Goal**: 老師授權、用 Google Picker 選試算表、選定工作表；任何失敗都有看得懂的訊息且活動題目不變。

**Independent Test**: 用含多張工作表的真實 Google 試算表走完「授權 → 選檔 → 選工作表」，再逐一製造取消、拒絕、過期、權限不足、非試算表。

### Tests for User Story 1 (REQUIRED — one or more per Acceptance Scenario) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US1] 在 `tests/unit/adapters/google/test_auth.py` 測試 `GoogleAuthGateway`（以 `FakeClock` 與假的 token 交換）：`state` 只能用一次、超過有效期限失敗、不符或重複使用時**不交換 token** 並導回 `auth=error`；使用者取消或拒絕 → `auth=denied`；token 只在記憶體、不出現在任何回傳值或日誌（`Scenario: US1-AS3`、`US1-AS4`）。
- [X] T018 [P] [US1] 在 `tests/unit/adapters/google/test_sheets_inspect.py` 用 `HttpMockSequence`（手寫回應 JSON，標明手寫）測試 `inspect`：先以 Drive `mimeType` 判斷，非 Google 試算表（Google 文件、PDF、XLSX）→ `NOT_A_SPREADSHEET`；是試算表才以欄位遮罩 `properties.title,sheets.properties(sheetId,title,hidden,gridProperties)` 取得工作表清單；多張與單張兩種；回應含 `hidden: true` 的工作表時，清單與張數都不含它（一可見加一隱藏 → 視為一張；全部隱藏 → 空清單）；並驗證 `SpreadsheetInfo` 能提供工作表數量判斷所需資料（`Scenario: US1-AS1`、`US1-AS2`、`US1-AS6`）。
- [X] T019 [P] [US1] 在 `tests/unit/adapters/google/test_errors.py` 測試 `HttpError` → `ImportRejection` 對應：401 → `AUTH_EXPIRED`、403／404 → `PERMISSION_DENIED`、429／逾時／5xx → `READ_FAILED`；對應結果的訊息不含憑證與內部細節（`Scenario: US1-AS4`；`Edge: 選檔後檔案消失或失去權限`）。
- [X] T020 [P] [US1] 在 `tests/unit/app/guided_notes_import/test_service_source.py` 以 Fake 連接埠測試：`inspect_spreadsheet` 不改任何狀態，且 `auto_select_sheet_id` 在恰好一張工作表時為該張識別、兩張以上為 `None`、零張（含全部隱藏）時回 `SHEET_NOT_FOUND`；隱藏工作表不列入也不計張數，`select_source` 選到隱藏工作表 → `SHEET_NOT_FOUND`、舊選擇不變（`Scenario: US1-AS2`，單一工作表自動選用的判斷在後端）；`select_source` 驗證 `sheet_id` 屬於該試算表後才保存、失敗時舊的選擇不變；沒有授權 → `NOT_AUTHORIZED`；取消選檔（沒有任何呼叫）不留下半途來源；授權在流程中途失效時，已選來源保留、重新授權後可直接重試（`Scenario: US1-AS1`、`US1-AS3`、`US1-AS4`、`US1-AS5`；`Edge: 授權在流程中途失效`）。
- [X] T021 [P] [US1] 在 `tests/contract/guided_notes_import/test_auth_source_api.py` 以 `TestClient` 依 [contracts/http-api.md](contracts/http-api.md) 驗證端點 #1～#6（#2 即 `/oauth/callback`）：狀態碼、回應形狀（含 #5 的 `autoSelectSheetId`：單張為該張的 `sheetId`、多張為 `null`；一可見加一隱藏仍為單張）與 302 導回 `auth=ok|denied|error`；`picker-config` 帶 `Cache-Control: no-store` 且只限該活動老師；學生 token、其他活動老師、無 token 一律被拒；`GOOGLE_NOT_CONFIGURED` → 503 且訊息不含變數名稱；**路由表中沒有任何本機檔案上傳端點**（FR-005，`Scenario: US1-AS6`）；格式錯誤的請求（`spreadsheetId` 為空字串或不是字串、`sheetId` 不是整數、缺欄位、多餘欄位）一律回 400 `INVALID_REQUEST`、訊息指出欄位、不更動任何狀態，且未驗證的值不會被送進 Google 呼叫（FR-021，`Edge: 輸入驗證失敗`）。

### Implementation for User Story 1

**應用層**

- [X] T022 [US1] 在 `<app>/service.py` 建立 `ImportService`（建構子注入 `AuthGateway`、`SheetsReader`、`ActivityGateway`、`ImportStore`、`Clock`），實作 `start_auth`、`inspect_spreadsheet`（計算 `auto_select_sheet_id`）、`select_source`：每個入口先以 `stage(code)`、`is_teacher(code, requester)` 判斷（錯誤代碼依 research R8），`select_source` 驗證 `sheet_id` 屬於該試算表才寫入 `selections`。（依賴 T010～T014）

**轉接層**

- [X] T023 [P] [US1] 在 `<google>/errors.py` 實作 `HttpError`／逾時 → `ImportRejection` 的對應（T019 的規則）。
- [X] T024 [US1] 在 `<google>/auth.py` 實作 `GoogleAuthGateway`：授權碼流程（`google-auth-oauthlib`）、一次性且有期限的 `state`、token 只存記憶體（`ImportStore.sessions`）、`picker_credentials` 只回短效 `drive.file` token；不記錄 token、授權碼、`state`、client secret。（依賴 T015、T023）
- [X] T025 [P] [US1] 在 `<google>/sheets_reader.py` 實作 `GoogleSheetsReader.inspect`：Drive `files.get` 取 `mimeType`，再以 `spreadsheets.get` 與欄位遮罩取工作表清單；以 `asyncio.to_thread` 呼叫同步的 Google 程式庫；只用讀取方法（FR-023）。
- [X] T026 [US1] 在 `<web>` 實作端點 #1～#6（含 #2 `/oauth/callback`）、錯誤轉換（依 http-api 的錯誤碼與狀態碼表，訊息取自 `messages.py`）與請求日誌（只記活動代碼、端點名稱、結果代碼）；在 `<web>` 提供 `create_router(app)`（依 `docs/DEVELOPMENT.md` 的約定，寫法參考 `adapters/web/system.py`），並在 `main.py` 做兩個最小追加：`api.include_router(guided_notes_import.create_router(app))` 一行，以及 `create_app` 新增兩個選用參數 `import_auth_gateway=None`、`import_sheets_reader=None`（省略時以 `<google>/config.py` 建立真實轉接器並存入 `app.state`，測試傳入 Fake；這是對共用檔案比「一行 router」多一點的追加，PR 描述註明）。（依賴 T022、T024、T025）

**前端**

- [X] T027 [US1] 在 `<static>/teacher.html` **只加一個**「匯入學習單」區塊，並建立 `<static>/js/import.js`：按鈕 → `auth/start` → 導向 Google → 回來後依 `?auth=ok|denied|error` 顯示狀態與重新授權入口 → `picker-config` → Google Picker（只允許 Google 試算表 MIME，取消時維持原狀）→ `inspect` → `autoSelectSheetId` 有值時自動 `PUT source` 並顯示名稱，為 `null` 時要求老師明確選一張；前端不自己數工作表。所有後端與試算表來的文字一律以 `textContent` 輸出。

**真實驗證里程碑**

- [X] T028 [US1] **里程碑 0（待驗證假設 1）**：以真實 Google 帳號與一份真實試算表，依 [quickstart.md](quickstart.md) 前置條件設定好 `.env`，用 `python -m lecture_quiz`（001 的啟動方式；埠號預設 8000）啟動後走完「授權 → Picker 選檔 → `inspect`」，確認 `drive.file` 足以讀取 Picker 選到的試算表。把日期、操作與結果填入 quickstart 紀錄表；若讀取失敗，依 [research.md](research.md) R1 的 fallback 評估改用敏感範圍，並在 plan「待真實驗證的假設」註明；**未做之前不得宣稱授權範圍成立**。（依賴 T026、T027）
    - **紀錄（2026-11-23）**：EricC430 回報已用真實帳號與試算表完成，`drive.file` 足以讀取 Picker 選到的試算表，**細節依其決定不記錄**。過程中發現 `GOOGLE_APP_ID` 必須是 Cloud 專案編號（純數字），填錯時 Drive 回 404 `notFound`，已加入診斷日誌（狀態碼與原因代碼）。

**Checkpoint**: 老師可以授權、選檔並選定工作表；失敗時題目不變

---

## Phase 4: User Story 2 - 匯入單題學習單並不依賴固定位置 (Priority: P1)

**Goal**: 依「題號」「作答」表頭與合併範圍動態定位單題學習單，不依賴固定列欄或工作表名稱。

**Independent Test**: 六題、作答格橫向合併的單題學習單，與整體移位且工作表更名後的同內容版本，兩份都得到 6 題 6 格，位置各自正確。

### Tests for User Story 2 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [X] T029 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_numbers.py` 表格驅動測試題號正規化（[research.md](research.md) R5）：接受 `numberValue` 的 1、1.0、`" 1 "`、`"01"`、`"1"`；拒絕 0、-1、1.5、`"1."`、`"第1題"`、`"Q1"`、全形 `"１"`、布林與錯誤值；用明確 ASCII 規則，不使用 `isdigit`（`Scenario: US2-AS4`；`Edge: 題號格式`）。
- [X] T030 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_parse_single.py` 測試：單題範本 → 6 題 6 格，每題答案位置為橫向合併範圍的左上角（`Scenario: US2-AS1`）；同樣內容以不同 `origin` 平移並更換工作表名稱 → 題數與格數不變、位置對應新位置，且結果不含任何固定座標假設（`Scenario: US2-AS2`；原則 III）。
- [X] T031 [P] [US2] 在 `tests/unit/core/guided_notes_import/test_parse_header_values.py` 測試：「題號」「作答」前後帶半形與全形空白仍可辨識（`Scenario: US2-AS3`）；題號值為數值 1.0 與文字 `"1"` 都得到題號 1（`Scenario: US2-AS4`）；工作表含題目敘述欄時，`ParseResult` 與其中任何欄位的字串化內容都不含題目敘述文字（`Scenario: US2-AS5`；FR-008）。
- [X] T032 [P] [US2] 在 `tests/unit/adapters/google/test_sheets_read.py` 用 `HttpMockSequence`（手寫回應 JSON）測試 `read`：欄位遮罩字串為 `sheets(properties(sheetId,title,gridProperties),merges,data(startRow,startColumn,rowData(values(effectiveValue,formattedValue))))`；`startRow`／`startColumn` 位移還原成絕對座標；`rowData` 省略結尾空儲存格；`GridRange` 結束索引「不含」轉成 `MergeRange` 的「含」；`numberValue` 與 `stringValue` 正確區分；工作表標題含單引號時的 `ranges` 跳脫；全程只送出讀取請求（FR-023；`Edge: 同一個格子被兩題指到` 前提）。
- [X] T033 [P] [US2] 在 `tests/unit/app/guided_notes_import/test_service_import.py` 測試 `import_sheet` 的順序與原子性（[research.md](research.md) R6）：階段與身分 → 讀取 → 解析 → 001 `replace_questions` → 才保存；讀取失敗、解析失敗、001 拒絕三種情況下都不保存、不改既有記錄；成功時只傳題號清單給 001；兩個並行的匯入依序執行，最後成功的一次整份取代（`Edge: 連續快速重複匯入`、`Edge: 解析後、寫入前階段或身分改變`）；另測：快照讀取後，Fake 讀取器的來源內容被改動，已匯入的結果與記錄不變、也不自動更新（`Edge: 讀取期間老師編輯試算表`，以一次讀取為準）；多個活動同時存在互不影響。
- [X] T034 [P] [US2] 在 `tests/contract/guided_notes_import/test_import_api.py` 驗證 `POST /activities/{code}/import`：200 的 `ImportResult` 形狀（含 001 回傳的 `version`）、`SOURCE_NOT_SELECTED`、同一個 `Idempotency-Key` 重送回傳第一次的結果而不重複匯入。

### Implementation for User Story 2

**核心**

- [X] T035 [P] [US2] 在 `<core>/numbers.py` 實作題號正規化（T029 的規則，明確 ASCII 規則運算式，不用 `isdigit`／寬鬆 `int()`）。
- [X] T036 [P] [US2] 在 `<core>/headers.py` 實作「找表頭」：文字以 `strip()` 正規化（含全形空白）後與「題號」「作答」完全相同才算；取得題號欄、作答欄範圍（含合併）與資料起始列；不接受同義詞，不以結構猜測。表頭缺少與歧義的回報在 T051 補齊。
- [X] T037 [US2] 在 `<core>/rows.py` 實作單題路徑：有題號值且作答欄範圍內沒有子編號的列，取作答欄範圍第一欄的儲存格（屬合併範圍則取左上角）為答案位置。（依賴 T035、T036）
- [X] T038 [US2] 在 `<core>/parser.py` 實作 `GuidedNotesParser.parse(snapshot) -> ParseResult`：串起表頭、逐列分類、組成 `Question`／`Blank` 與 `StructureSnapshot`（表頭位置、`answer_cols`、`data_start_row`、與表頭列及資料區相交的合併範圍、各列題號、答案格映射）；題目敘述欄完全不讀取。（依賴 T037）

**轉接層**

- [X] T039 [P] [US2] 在 `<google>/sheets_reader.py` 實作 `read`：依 T032 的規則先以輕量請求取得工作表標題（組 `ranges` 用），再發出一次欄位遮罩請求並轉成 `SheetSnapshot`（保存列欄總數；實作時共兩次唯讀 GET）；轉接層型別不得外洩到核心與應用層。（依賴 T025）

**應用層**

- [X] T040 [US2] 在 `<app>/service.py` 實作 `import_sheet`：持有該活動的匯入鎖，順序固定為「`stage`／`is_teacher` → `read` → `parse` → `replace_questions`（只傳題號清單）→ 以新的 `ImportRecord` 整份取代舊的」；任何失敗都不寫入。（依賴 T038、T039）

**轉接層**

- [X] T041 [US2] 在 `<web>` 新增端點 #7 `POST /activities/{code}/import`：處理 `Idempotency-Key`、回傳 `ImportResult`；驗證失敗的 422 格式在 T053 補齊。（依賴 T040）

**Checkpoint**: 單題學習單可匯入，不依賴固定位置

---

## Phase 5: User Story 3 - 匯入題組與單題混合的學習單 (Priority: P1)

**Goal**: 題組算一個競賽題目，每個子空格有精確答案位置，不漏續列、不指向編號格。

**Independent Test**: 原始題組範例得到 4 題 6 格；相鄰重複題號與夾間隔列的變體各匯入一次。

### Tests for User Story 3 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [X] T042 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_parse_groups.py` 測試：原始題組範例 → 4 題 6 格，第二個子空格被辨識、答案位置為「（n）」右側的作答格而非編號格、編號位於作答表頭涵蓋的欄範圍內（`Scenario: US3-AS1`）；相鄰重複題號與縱向合併得到相同的題數與格數（`Scenario: US3-AS2`）；沒有題號也沒有子空格的間隔列被忽略、不繼承題號（`Scenario: US3-AS3`）；空白題號只在縱向合併範圍內繼承（`Scenario: US3-AS4`）；單題與題組混合，題組只算一題（`Scenario: US3-AS5`）；同一題的兩個子空格之間夾完全空白的列（縱向合併與逐列重複兩種，含合併範圍把間隔列包進去）→ 忽略該列、格數不變（`Scenario: US3-AS6`；FR-026）。另測：作答格已有佔位文字（例如「請填寫」）仍視為作答格、位置不變（`Edge: 作答格已有佔位文字`）。
- [X] T043 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_structure_snapshot.py` 以版面 A、版面 B 測試 `StructureSnapshot` 內容：表頭位置、`answer_cols`、`data_start_row`、僅含相交者的合併範圍、各列題號、答案格映射（FR-024；供 005 寫回前比對）。
- [X] T044 [P] [US3] 在 `tests/unit/core/guided_notes_import/test_sub_index_format.py` 測試子編號被接受的格式：「（1）」「(1)」（半形或全形括號、半形數字），且必須位於作答表頭涵蓋的欄範圍內（`Edge: 子編號與作答格的位置`；拒絕的變體在 T048 測試）。

### Implementation for User Story 3

**核心**

- [X] T045 [US3] 擴充 `<core>/rows.py`：空白題號在縱向合併範圍內繼承左上角的值、範圍外不繼承；在作答欄範圍內以 `^[（(][0-9]+[）)]$` 辨識子編號；作答格為編號儲存格（含其合併範圍）**右側緊鄰**的格子，屬合併範圍取左上角，右側超出工作表列欄範圍視為缺少答案格；沒有題號值也沒有子編號的列一律略過（FR-026）。（依賴 T037）
- [X] T046 [US3] 建立 `<core>/validator.py` 的分組：忽略空白列後，**相鄰**且題號值相同的列歸為同一題（涵蓋縱向合併與逐列重複兩種表示），產生 `Question`（`blank_count`、`is_group`）與帶 `sub_index` 的 `Blank`。（依賴 T045）
- [X] T047 [US3] 擴充 `<core>/parser.py`：串接 `validator`，並讓 `StructureSnapshot` 涵蓋題組的子空格答案格映射。（依賴 T046）

**Checkpoint**: 單題與題組混合的學習單可以正確匯入

---

## Phase 6: User Story 4 - 學習單有問題時整份拒絕並指出位置 (Priority: P2)

**Goal**: 缺陷學習單整份拒絕、指出列欄與原因；先前成功匯入的資料不變。

**Independent Test**: 每種缺陷各一份負面學習單，先成功匯入合法的，再依序匯入負面的，確認每次都被拒絕且既有資料不變。

### Tests for User Story 4 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [X] T048 [P] [US4] 在 `tests/unit/core/guided_notes_import/test_parse_defects.py` 測試（**先寫、先確認失敗並記錄**）：缺「題號」、缺「作答」、兩者皆缺、空工作表（`Scenario: US4-AS1`）；兩個表頭區塊、同列重複表頭、「題號」「作答」不在同一列（`Scenario: US4-AS2`；`Edge: 兩組表頭但只有一組有合法題目`）；題號跳號、非相鄰重複題號、子編號缺漏、子編號重複、非數字題號（`Scenario: US4-AS3`）；孤立子空格、缺少答案格（含右側無儲存格與題號存在卻找不到任何作答格）、目標格重疊（`Scenario: US4-AS4`）；被拒絕的子編號變體：全形數字「（１）」、括號內夾空白；**近似錯誤對照**（格式與關鍵字都對、內容有缺陷，例如表頭存在但題號跳號）必須被拒絕；多個缺陷同時存在時**全部收集**回報；`ok` 為假時 `questions`、`blanks`、`structure` 為空（FR-016）。（SC-004）另測：表頭同義詞不被接受，「題目編號」「編號」「Answer」等一律視為缺表頭並拒絕，不猜結構（`Edge: 表頭同義詞不支援`；FR-006）。
- [X] T049 [P] [US4] 在 `tests/unit/app/guided_notes_import/test_import_rejection.py` 測試：先成功匯入一份合法學習單，再匯入各種缺陷學習單，每次都被整份拒絕，`FakeActivityGateway.replace_questions` 沒有被呼叫，既有的 `ImportRecord` 與題號清單完全不變（`Scenario: US4-AS5`）；解析成功但 001 拒絕（`GATEWAY_REJECTED`）時，002 保存的資料也不變（`Edge: 解析後、寫入前階段或身分改變`）。
- [X] T050 [P] [US4] 在 `tests/contract/guided_notes_import/test_validation_api.py` 驗證 422 `VALIDATION_FAILED` 的 `issues` 形狀：`kind`、`row`、`col`（1 起算，欄以 A、B… 字母表示，無位置時為 `null`）、`quoted`（≤40 字元）、`hint`；回應不含堆疊、檔案路徑或憑證；含 `<script>` 之類字樣的儲存格文字原樣當純文字回傳（FR-022、SC-004；`Edge: 不可信的儲存格文字`）。

### Implementation for User Story 4

**核心**

- [X] T051 [US4] 補完 `<core>/headers.py` 的問題回報：缺「題號」、缺「作答」、歧義（多個表頭區塊、同列重複、不在同一列）各回對應的 `ValidationIssue`（`MISSING_HEADER_NUMBER`、`MISSING_HEADER_ANSWER`、`AMBIGUOUS_HEADER`）。
- [X] T052 [US4] 補完 `<core>/validator.py` 的整體檢查：`NON_NUMERIC_NUMBER`（只檢查題號欄的資料列，題號欄空白不算）、`NUMBER_GAP`（依出現順序必須是 1, 2, 3…）、`NON_ADJACENT_DUPLICATE`、`SUB_INDEX_MISSING`、`SUB_INDEX_DUPLICATE`（題組子編號從 1 連續不重複）、`ORPHAN_SUB_BLANK`、`MISSING_ANSWER_CELL`、`TARGET_OVERLAP`（指出兩處）；錯誤全部收集，任何問題都讓 `ok = False` 且不產生任何題目。（依賴 T046、T051）

**應用層與轉接層**

- [X] T053 [US4] 在 `<app>/messages.py` 每個 `IssueKind` 的修正建議放在核心 `<core>/hints.py`（單一來源，`messages.py` 的測試逐項檢查它們）；在 `<web>` 把 `ValidationIssue` 轉成 http-api 的 `issues`（1 起算列號、欄字母、`quoted` 截斷 40 字元）。（依賴 T052）

**前端**

- [X] T054 [US4] 在 `<static>/js/import.js` 以表格呈現錯誤清單（列、欄、原因、修正建議），全部以 `textContent` 輸出；授權與讀取類錯誤顯示固定訊息與下一步。

**Checkpoint**: 每種缺陷都被整份拒絕並指出位置，既有資料不變

---

## Phase 7: User Story 5 - 老師看到匯入預覽並可在準備中重新匯入 (Priority: P2)

**Goal**: 匯入成功後顯示題號、各題空格數、總題數與總空格數；準備中可整份替換；保存來源映射與匯入時結構供 005。

**Independent Test**: 匯入混合範例得到「4 題、6 格」與每題空格數；再匯入另一份合法學習單，舊結果整份被取代。

### Tests for User Story 5 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [X] T055 [P] [US5] 在 `tests/unit/app/guided_notes_import/test_preview.py` 測試：混合範例 → 「4 題、6 格」，`blanks_per_question` 為 {1: 2, 2: 2, 3: 1, 4: 1}（`Scenario: US5-AS1`）；題組有多個子空格時總題數只算一題、總格數按子空格累計（`Scenario: US5-AS3`；FR-018）。
- [X] T056 [P] [US5] 在 `tests/unit/app/guided_notes_import/test_reimport.py` 測試：準備中改選另一份合法學習單 → 新結果整份取代舊結果，`ImportRecord` 與傳給 001 的題號清單都沒有舊題目的殘餘（`Scenario: US5-AS2`）；重新匯入同一份試算表且內容已修正 → 依新內容更新（`Scenario: US5-AS4`）；兩個活動各自的 `ImportRecord` 互不影響（FR-024）。
- [X] T057 [P] [US5] 在 `tests/contract/guided_notes_import/test_import_summary_api.py` 驗證 `GET /activities/{code}/import`：沒有匯入過回 `{"imported": false}`，有則回與 `POST` 相同形狀的 `ImportResult`（頁面重新整理恢復預覽）；`get_import_record` 為唯讀，修改回傳物件不影響 `ImportStore`；學生看不到來源映射與結構（原則 V）。

### Implementation for User Story 5

**應用層**

- [X] T058 [US5] 在 `<app>/service.py` 實作 `ImportPreview` 的建立、`get_import_summary(code, requester)`、`get_import_record(code)`（給 005，唯讀，回傳不可變物件）。（依賴 T040）

**轉接層**

- [X] T059 [US5] 在 `<web>` 新增端點 #8 `GET /activities/{code}/import`。（依賴 T058）

**前端**

- [X] T060 [US5] 在 `<static>/js/import.js` 顯示預覽（題號清單、各題空格數、總題數、總空格數）、頁面重新整理時以 #8 恢復、準備中可改選並重新匯入。

**給 003 的介面（PR #11 審查追加，編號接在 T079 之後以免重編既有任務）**

- [X] T083 [US5] 在 `src/lecture_quiz/app/guided_notes_import/service.py` 的 `ImportService` 新增 `blanks_per_question(code) -> Mapping[int, int] | None`，實作 [contracts/service-interfaces.md](contracts/service-interfaces.md)「給 003」一節：由最後一次成功匯入的 `ImportRecord.blanks` 依題號計數（單題為 1），沒有成功匯入（或活動不存在）回 `None`；回傳新字典、唯讀、不需要請求者身分、不呼叫 Google；不得匯入 003 的任何型別。**先寫測試**於 `tests/unit/app/guided_notes_import/test_blanks_per_question.py` 並確認紅燈：未匯入回 `None`；單題與題組混合（4 題 6 格 → `{1: 2, 2: 2, 3: 1, 4: 1}`）；重新匯入成功後格數更新；重新匯入失敗（整份被拒）時維持舊格數；回傳字典被修改不影響下次結果。（依賴 T040、T058）

**Checkpoint**: 老師可核對匯入結果，005 可取得來源映射與結構

---

## Phase 8: User Story 6 - 第一輪開始後鎖定題目來源 (Priority: P3)

**Goal**: 第一輪開始後拒絕更換來源、重新匯入與修改題目定義；身分與階段的閘門一致。

**Independent Test**: 讓活動進入第一輪開始後的狀態，嘗試更換試算表與重新匯入，兩者都被拒絕，來源映射與既有提交不變。

### Tests for User Story 6 (REQUIRED — one or more per Acceptance Scenario) ⚠️

- [X] T061 [P] [US6] 在 `tests/unit/app/guided_notes_import/test_lock_after_round.py` 測試：001 階段為搶答中、結果未定案、結果已定案、已結束時，`select_source` 與 `import_sheet` 都回 `ROUND_STARTED`，`ImportRecord` 與既有提交不變（`Scenario: US6-AS1`）；002 不提供任何修改題號、空格數、答案位置的端點（對 `main.py` 路由表掃描），且透過 001 `replace_questions` 的修改被拒、題目定義不變（`Scenario: US6-AS2`）；已取消回 `ACTIVITY_CANCELLED`，`STAGE_NOT_PREPARING` 只保留給無法辨識的階段（防禦用）；**`PREPARING` 與 `JOINING` 兩個階段都允許** `select_source` 與 `import_sheet`，兩者各測一次成功與重新匯入（`Scenario: US5-AS2`；`Edge: 活動不在「準備中」`；alignment 2026-11-23「開放加入」）。
- [X] T062 [P] [US6] 在 `tests/contract/guided_notes_import/test_identity_gate.py` 測試每個端點（#1、#3～#8）：非老師、其他活動的老師、不存在的活動代碼都被拒絕且不更動任何題目（`Edge: 非老師的請求`、`Edge: 活動代碼不存在`；FR-025）；活動不存在時依 001 慣例，無 token 回 404 `ACTIVITY_NOT_FOUND`、帶 token 回 410 `ACTIVITY_GONE`；解析成功但 001 因階段剛好改變而拒絕 → `GATEWAY_REJECTED`、001 題目與 002 保存的資料都不變。

### Implementation for User Story 6

**應用層**

- [X] T063 [US6] 檢查 `<app>/service.py` 每個入口（`start_auth`、`inspect_spreadsheet`、`select_source`、`import_sheet`、`get_import_summary`、`get_import_record`）都先查 `stage`／`is_teacher` 並依 research R8 回對應代碼；缺漏補上。不需要 002 自己維護「已鎖定」狀態，鎖定完全由 001 的 `stage()` 與 `replace_questions` 決定。（依賴 T058）

**前端**

- [X] T064 [US6] 在 `<static>/js/import.js` 依 001 的活動快照在階段不是「準備中」或「開放加入」時停用匯入區塊，並顯示「搶答已開始，題目不可更動」（已取消時顯示「活動已取消」）。

**Checkpoint**: 所有 User Story 完成

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事的驗證、真實路徑與品質關卡

- [X] T065 [P] 在 `tests/integration/test_logging_guided_notes_import.py` 以 `caplog` 檢查日誌（技術限制 3）：走完授權、匯入成功與各種失敗後，日誌只含活動代碼、端點名稱、結果代碼、題數與格數、001 版本；**不含** token、授權碼、`state`、client secret、試算表標題與儲存格內容；程式碼中沒有 `print` 日誌。
- [X] T066 [P] 在 `tests/unit/core/guided_notes_import/test_parse_scale.py` 測試 50 題、數百列學習單的解析結果正確（SC-006 的前提；不以 mock 的耗時冒充真實耗時，真實秒數在 T071 記錄）。
- [X] T067 [P] 在 `tests/integration/test_import_two_layouts.py` 以版面 A、版面 B（原則 III、SC-003）走入口：`TestClient` → 真實 `GoogleSheetsReader`（`HttpMockSequence` 餵入手寫的 `spreadsheets.get` 回應 JSON，標明手寫）→ `parse` → 001 `ActivityService`，驗證兩份版面都得到正確題數、格數與答案位置、整體移位後結果一致（`Scenario: US2-AS2`、`US3-AS1`、`US5-AS1`）。
- [X] T068 [P] 建立 `scripts/capture_real_fixture.py`：把真實 `spreadsheets.get` 回應去識別化（刪除標題、帳號、檔案 ID）後存成 `tests/fixtures/real/*.json`；憑證與輸出只在本機，不入版控的內容不得提交。
- [X] T069 [P] 建立 `tests/real_google/test_real_import.py`，標記 `@pytest.mark.real_google`，明確指定真實轉接器（不跟隨預設的 Fake）；缺少任何 Google 環境變數時**明確失敗**並說明缺什麼，不跳過、不退回離線路徑；pytest 不會自動讀 `.env`，環境變數由執行者在 shell 設定。預設 `pytest` 不執行它。
- [X] T070 在 [quickstart.md](quickstart.md) B 區補一步「選只有一張工作表的試算表 → 自動選用並顯示名稱」（`Scenario: US1-AS2`；自動選用的判斷已由 T020、T021 自動測試，這裡人工確認畫面顯示名稱），並把 US1-AS5「選檔取消」對應到 B-3。
- [X] T071 **真實路徑驗證（SC-009，合併前必做）**：EricC430 以兩份版面不同的真實 Google 試算表，依 quickstart B-1～B-13 各走一次，記錄日期、操作、結果數字與 SC-006 的「確認工作表到看見預覽」秒數（**超過 10 秒記為未通過**，並記錄當時題數與網路狀況），填入 quickstart 紀錄表；憑證只在本機，不貼進 repo、Issue、PR。（依賴 T074）
    - **紀錄（2026-11-23）**：EricC430 回報 B-1～B-13 全數通過，**細節（秒數、題數、逐步結果）依其決定不記錄**；SC-006 的實測秒數因此沒有數字可對照，只有「回報通過」。非實作者的 T076 驗證仍待 jacky0407。
- [ ] T072 T071 通過後執行 T068 擷取兩份版面的真實回應，新增「JSON → 轉接層 → 解析」的入口測試，確認 `GridRange` 結束索引「不含」的假設，並把假設 1～4 的驗證結果寫回 plan「待真實驗證的假設」。擷取之前不得宣稱入口路徑已驗證。（依賴 T071）
    - **不做（2026-11-23，EricC430 決定）**：未擷取真實回應，**沒有「JSON → 轉接層 → 解析」的真實 fixture 入口測試**，維持未勾選。`GridRange` 的假設改以官方 API 參考文件確認（見 plan），T071 回報通過與之一致；入口路徑只有手寫 JSON 的 `HttpMockSequence` 測試與使用者回報的真實驗證。`scripts/capture_real_fixture.py` 保留供日後使用。
- [X] T073 程式碼與圖表一致性驗證：逐一比對 `diagrams/002-guided-notes-import-{component,class,sequence}.puml` 與實作（`ImportService` 的方法、`AuthGateway`／`SheetsReader` 的方法、`ImportRecord` 的欄位、`SpreadsheetInfo.autoSelectSheetId`、時序圖的 inspect／`PUT source`／匯入步驟；`IssueKind` 的值。類別圖與時序圖已於 2026-11-22 依 plan 同步，這裡驗證實作沒有再偏離）。有差異時先更新圖表並重新轉出 PNG（原則 II）。
- [X] T074 執行全部自動化測試 `pytest -m "not real_google and not perf"`，並以 `-v` 確認核心、應用層、轉接層（`HttpMockSequence`）、HTTP 契約、架構純度、日誌各自有項目、沒有任何一類是 0 筆；記錄日期、指令與通過／失敗／略過數字（原則 VI）。
- [X] T075 執行 `ruff check .`、`ruff format --check .`、`mypy src`，全部通過並記錄結果（技術限制 2）。
- [ ] T076 由非實作者（jacky0407）依 [quickstart.md](quickstart.md) B 區做人工驗證，記錄日期、每一步操作與結果於 quickstart 紀錄表並簽名（原則 VI）。
- [X] T077 追蹤 001 的開發用 seed API（`adapters/web/dev_seed.py`、`LECTURE_QUIZ_DEV_SEED`、`tests/integration/test_dev_seed.py`、前端「放入假題目」按鈕）：依 001 plan 在 002 合併後的第一個 PR 移除；因檔案屬 001，先與 jacky0407 協調是在本 PR 一併移除還是另開 PR，並在 PR 描述記錄結論。
    - **完成（2026-11-23）**：依 EricC430 指示直接在本 PR 移除：刪除 `adapters/web/dev_seed.py`、`tests/integration/test_dev_seed.py`；`main.py` 的 `dev_seed` 參數與 `LECTURE_QUIZ_DEV_SEED`、`teacher.html`／`teacher.js` 的「放入假題目」按鈕、`tests/conftest.py` 與 `tests/perf` 的相關參數。驗證：`ruff check .` 通過、`mypy` 通過、`pytest -m "not real_google and not perf"` 706 passed。**jacky0407 尚未確認**（檔案屬 001），請在 PR 描述註明。
- [ ] T078 更新 `CLAUDE.md`「專案現況」：補上 `pytest -m real_google` 的手動執行方式與 002 的三層路徑；再用全新 clone 在乾淨的 venv 重跑安裝與 `pytest`，確認不依賴任何本機未提交的檔案（規章第 9 節）。
- [ ] T079 開 PR 前確認：文末 Scenario 對照表的 28 個項目都有已通過的測試；spec 的 Traceability 與 `docs/alignment.md` 沒有新增偏離項；quickstart 紀錄表沒有空白的已執行項目；PR 描述列出尚未驗證的假設（若有），並註明已知限制：US1-AS5「取消選檔」是前端行為，沒有自動化測試，僅以人工驗證 B-3 涵蓋（2026-11-23 接受）；品質關卡 7：`git status` 與 `git diff` 確認沒有夾帶 `.env`、憑證、token、`期末專題說明.md`、`project_proposal_draft.md` 或其他不追蹤的檔案。

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
2. 每個故事完成後都跑 `pytest -m "not real_google and not perf"`，不得破壞前一個故事。
3. 最後做 Polish 與真實路徑驗證；真實驗證通過後才擷取真實 fixture。

### Parallel Team Strategy

- 實作者 EricC430 負責全部任務；jacky0407 負責 T001 的前置（骨架 PR）、T076 非實作者人工驗證與 T077 的協調。
- 與 005 的介面：`ImportRecord`（`blanks`、`structure`、`source`）與 `get_import_record` 在 US5 完成後穩定，通知 005 的實作者。

---

## Scenario 對照表

| Scenario | 對應測試任務 |
|---|---|
| US1-AS1 | T018、T020、T067（人工 T071） |
| US1-AS2 | T018、T020、T021（`autoSelectSheetId` 由後端決定；前端只依它呼叫 `PUT source` 並顯示名稱，該顯示部分以人工 T070、T071 涵蓋） |
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

**Edge Case 對照**：授權中途失效 → T020；選檔後檔案消失 → T019；子編號與作答格位置 → T044、T048；題號格式 → T029；同一格被兩題指到 → T048；非相鄰重複 → T048；非老師、活動不存在、非準備中 → T061、T062；解析後寫入前階段改變 → T033、T049、T062；連續快速重複匯入 → T033；輸入驗證失敗與訊息不含內部細節 → T013、T021、T050；作答格已有佔位文字 → T042；表頭同義詞不支援 → T048；不可信的儲存格文字 → T050、T054；讀取期間老師編輯試算表（以一次讀取為準，匯入後不自動更新）→ T033（已補測試描述）。

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 實作前先確認測試是失敗的；負面案例（T048）與負對照（T007）要真的會失敗，才能相信測試。
- 預設測試不得呼叫真實 Google；任何真實呼叫都必須明確標記並指定真實轉接器。
- 沒有實際執行過的指令，不得在 quickstart 紀錄表、PR 或任務清單寫成已通過。
- Commit after each task or logical group；`docs/alignment.md` 只追加。

## Phase 10: Convergence

- [X] T080 更新 `CLAUDE.md` 的 002 段落：T028、T071 已由 EricC430 回報通過（細節未記錄）、T072 不做、T076 待 jacky0407，並移除「尚未執行」的過時描述 per tasks T078、plan: 待真實驗證的假設 (contradicts)
- [X] T081 在 `src/lecture_quiz/adapters/google/config.py` 驗證 `GOOGLE_APP_ID` 為純數字（Cloud 專案編號），非數字時視為設定錯誤並明確失敗（匯入端點回未設定類拒絕、日誌只記變數名稱不記值），並在 `tests/unit/adapters/google/test_config.py` 與 `tests/contract/guided_notes_import/` 補測試（先確認紅燈）per FR-022、US1 (partial)
- [X] T082 在 `.env.example` 與 `quickstart.md` 前置條件說明 `GOOGLE_APP_ID` 是 Cloud「專案編號」（純數字、與 `GOOGLE_CLIENT_ID` 開頭數字一致），填錯時 Drive 回 404 `notFound`；並確認 quickstart 已列出啟用 Drive、Sheets、Picker 三個 API 的步驟 per plan: 待真實驗證的假設 (partial)

## Phase 11: PR #17 審查修正（jacky0407，2026-11-24）

- [X] T084 修正 `core/guided_notes_import/numbers.py` 的 `normalize_number`：改為 `float(value.number).is_integer()`（`int.is_integer()` 要到 Python 3.12 才有，憲章規定 3.11 以上），超大整數 `OverflowError` 視為非題號；`tests/unit/core/guided_notes_import/test_numbers.py` 新增以模擬 3.11 的 int 子類測試（先確認紅燈）。**以 Python 3.11.17 全新環境重跑全部測試**（修正前 3 failed、723 passed）。
- [X] T085 `ImportService.import_sheet` 的 `Idempotency-Key`：先確認活動存在與請求者是老師才查快取；只快取成功與驗證失敗，身分／階段被拒、授權過期、讀取失敗不快取。`tests/unit/app/guided_notes_import/test_idempotency_gate.py` 5 個測試（3 個先紅燈）。
- [X] T086 與 003（PR #16）的合併順序與衝突處理、移除 dev seed 後 003～005 的人工驗證方式，寫入 PR #17 說明；「給 003」介面為 T083。
