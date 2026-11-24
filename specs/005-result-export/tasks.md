---

description: "005-result-export 任務清單"
---

# Tasks: 定案成果寫回 Google Sheets 與 CSV 匯出（Result Export）

**Input**: Design documents from `/specs/005-result-export/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（憲章原則 VI）。每個 Acceptance Scenario 與對應的 OpenSpec Scenario 至少一個自動化測試；測試函式 docstring 第一行寫 `Scenario: USn-ASm`（與 001、003、004 相同慣例，供 `tests/SCENARIO_MAP.md` 掃描）。**先寫測試、執行並確認失敗（記錄失敗數），再寫實作。** 自動化測試**不得呼叫真實 Google**：Google 一律用 mock（`HttpMockSequence`、假的 `SheetsReader`／`SheetsWriter`／`AuthGateway`）；真實路徑只在 `real_google` 標記的手動測試與人工驗證（T094、T095）。

**Diagrams**: REQUIRED（憲章原則 II）。`diagrams/005-result-export-{component,class,sequence}.puml` 與 PNG 已存在（plan 2026-11-24 版）；Polish 有「程式碼與圖表一致性驗證」任務，實作偏離時先改圖並重新轉出 PNG。

**Architecture**: REQUIRED（NON-NEGOTIABLE）。`src/lecture_quiz/core/result_export/` 只匯入標準函式庫與 `lecture_quiz.core` 內的模組，不讀時鐘、不匯入 app／adapters／Google 套件；時間資料只來自已保存的 `received_at`，`started_at`／`finished_at` 由服務層從 `Clock` 取得。Google 讀寫、OAuth、畫面與 API 放外層，相依只能由外層指向核心。核心任務與轉接層任務分開列出。

**慣例**：路徑以 repo 根目錄為準；`<core>` = `src/lecture_quiz/core/result_export`，`<app>` = `src/lecture_quiz/app/result_export`，`<web>` = `src/lecture_quiz/adapters/web`，`<google>` = `src/lecture_quiz/adapters/google`，`<static>` = `src/lecture_quiz/adapters/static`。每個公開函式、類別、方法都要有型別提示與 Google 風格 docstring；日誌只用 `logging`，不用 `print`，**不記錄答案、原儲存格內容、試算表網址與標題、token、授權碼**（FR-033）。**不修改 001～004 的任何程式**（plan R16）；`main.py`、`teacher.html`、`app.css`、`tests/conftest.py`、`tests/SCENARIO_MAP.md` 只依 `docs/DEVELOPMENT.md` 的擴充約定追加。

**前置條件**：005 從 main 切出並已合併 main（001～004 已在其上）；真實驗證（T094、T095）需要兩份真實 Google 試算表與老師帳號。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行（不同檔案、沒有未完成的相依）
- **[Story]**: 所屬 User Story（US1～US6）；Setup、Foundational、Polish 不加

---

## Phase 1: Setup

**Purpose**: 建立目錄、確認基準、準備測試資料與替身

- [X] T001 建立套件目錄與空的 `__init__.py`（含模組 docstring）：`<core>/__init__.py`、`<app>/__init__.py`、`tests/unit/core/result_export/__init__.py`、`tests/unit/app/result_export/__init__.py`、`tests/contract/result_export/__init__.py`；另建 `specs/005-result-export/verification.md` 骨架（標題「基準」「先寫測試的失敗紀錄」「自動化結果」「效能」「真實路徑」「人工驗證」「R17 假設驗證結果」「問題紀錄」）
- [X] T002 記錄基準：在目前分支執行 `ruff check .`、`ruff format --check .`、`mypy`、`pytest -m "not real_google and not perf"`，把指令與通過／失敗／略過數寫入 `specs/005-result-export/verification.md` 的「基準」段落，作為「既有測試不退步」的比較依據（全域規則：證據只能來自這次真的執行過的指令）
- [X] T003 [P] 在 `tests/unit/core/result_export/helpers.py` 建立核心測試資料：`parsed(layout)`（以 `tests/fixtures/guided_notes_layouts.py` 的 `layout_a()`／`layout_b()` 取得 `SheetSnapshot`，用 `GuidedNotesParser.parse` 取得 `ParseResult`，回傳 `(snapshot, blanks, structure)`）、`entry(round, q, group, rank, wrong=False)`（`FinalizedEntry`）、`fq(round, q, success_group)`（`FinalizedQuestion`）、`fact(round, q, group, answers, second)`（`SubmissionFact`，`received_at` 以固定含時區的起點加 `second` 秒）、`cur_empty()`、`cur_text(s)`、`cur_other(display)`（`CurrentCell`）；另提供 `MIXED_WORLD`（一個兩格題組＋一個單題＋一題無人成功，兩輪）與 `MULTI_ROUND_WORLD`（某題第一輪全被判錯、第二輪由另一組成功）
- [X] T004 [P] 在 `tests/unit/app/result_export/fakes.py` 建立服務層替身：`FakeSheetsWriter`（以記憶體格子表實作 `read_cells`、`write_text_cells`；**與 002 的 `FakeSheetsReader` 共用同一份試算表狀態**：建構時接收讀取器，寫入成功（含「待確認但已套用」）時同步以新的 `SheetSnapshot`（只更新目標格的 `CellValue`，其餘儲存格與合併範圍不變）替換 `FakeSheetsReader.snapshots[(試算表識別, 工作表識別)]`，所以寫入後的再讀取與再辨識看得到新內容；寫入結果為「未套用」時不更新；可設定下一次寫入結果為 `SUCCESS`／`FAILED(reason)`／`PENDING`（寫入已套用或未套用兩種）；記錄呼叫次數與每次寫入的內容；可在寫入前 `block()` 以測試併發）、`FakeImportRecords`（`get_import_record(code)` 回傳 `ImportRecord`）、`FakeRankingReader`（`finalized_rounds`）、`FakeSubmissionReader`（`all_submissions`，含未定案輪次的提交，用來證明被過濾）、`RecordingPublisher`（記錄 `publish` 次數與呼叫當下 005 的鎖是否被持有）；重用 `tests/unit/app/guided_notes_import/fakes.py` 的 `FakeSheetsReader`、`FakeAuthGateway`
- [X] T005 [P] 在 `tests/unit/app/result_export/conftest.py` 建立 `export_env` fixture：真 `ActivityService` + `FakeClock` + `ManualScheduler`，建立活動並匯入題號、開放加入、開輪與關輪到所需階段（可指定停在搶答中、結果未定案、已定案、已結束、已取消），組出 `ExportService`（尚未實作時 fixture 以 `pytest.skip` 之外的方式失敗：缺 `ExportService` 就明確 ImportError，不得跳過）；回傳活動代碼、老師身分與各替身

---

## Phase 2: Foundational（型別、訊息、存放區、連接埠、組裝）

**Purpose**: 所有 User Story 共用的基礎；完成前不能開始任何 User Story

**⚠️ CRITICAL**: 本階段不修改任何既有檔案的行為；完成後 001～004 既有測試必須全部通過（T018）

### 測試（先寫、確認失敗）

- [X] T006 [P] 在 `tests/unit/core/result_export/test_models.py` 測試核心型別（共用基礎，`Scenario` 不適用）：全部是 `frozen` dataclass，修改欄位拋 `FrozenInstanceError`；`OverwriteImpact`、`DiffKind`、`OutcomeStatus`、`CellKind` 的成員與 data-model 逐項一致；`WritePlanItem`、`ResultSnapshot` 的集合欄位是 `tuple`
- [X] T007 [P] 在 `tests/unit/app/result_export/test_messages.py` 測試 `ExportRejection`：每個成員在訊息對照表都有訊息與 HTTP 狀態（http-api.md 的錯誤表逐項）；每則訊息不含 `token`、`Bearer`、`client_secret`、`/`、`\\`、`Traceback`、`.py`（FR-031、SC 逐項檢查）；`ACTIVITY_CANCELLED` 訊息為「活動已取消，不提供寫回與 CSV 下載。」
- [X] T008 [P] 在 `tests/unit/app/result_export/test_store.py` 測試 `ExportStore`：未知活動 `attempts` 為空；`add_attempt` 後依序取回；同一活動代碼永遠回同一把 `asyncio.Lock`、不同活動不同把；不同活動互不影響；`latest(code)` 回最後一次嘗試
- [X] T009 [P] 在 `tests/unit/app/result_export/test_extension_registration.py` 測試：建立 `ExportService` 後 `ActivityService` 恰多一個快照擴充；沒有任何嘗試時擴充對老師與學生都回傳空 mapping，快照與未註冊前**完全相同**（既有快照測試不需修改）
- [X] T010 [P] 在 `tests/contract/result_export/test_wiring.py` 測試：`create_app()` 之後 `app.state.export_service` 是 `ExportService`；`create_app(export_sheets_writer=<假>)` 會使用注入的寫入器；`/api` 之下沒有尚未實作的 005 路徑被意外註冊（只有各 Story 的端點任務完成後才會出現 X1～X7）

### 實作

- [X] T011 在 `<core>/models.py` 實作型別，逐欄位照 data-model.md「核心層」，限制逐字：`FinalizedEntry`（`round_number`、`question_number`、`group_number`、`rank: int | None`、`judged_wrong: bool`；被判錯者 `rank` 為 `None`）、`FinalizedQuestion`、`SubmissionFact`（`answers[i]` 是第 i+1 格；`received_at` 含時區）、`BlankTarget`（單題 `sub_index` 為 `None`）、`CellKind`（`EMPTY`／`TEXT`／`OTHER`）、`CurrentCell`（`text` 只在 `TEXT` 有值）、`OverwriteImpact`（`EMPTY`／`REPLACE`／`SAME`）、`WritePlanItem`（`current_display` 在 `REPLACE` 時為原內容，純文字、已截斷至 40 字元）、`ResultSnapshot`（`items` 依（題號, 子編號）排序）、`DiffKind`（`IDENTITY`／`UNRECOGNIZED`／`HEADER_POSITION`／`QUESTION_NUMBER`／`SUB_BLANK`／`ANSWER_CELL`／`MERGE_RANGE`）、`StructureDifference`（`detail` 是固定的類別說明，不含試算表文字）、`StructureCheck`（`ok` 為真時 `differences` 為空；依位置排序）、`CellCheck`、`OutcomeStatus`（`SUCCESS`／`FAILED`／`PENDING`）、`Reconciliation`、`ExportRow`；全部 `@dataclass(frozen=True)`（依賴 T006 先失敗）
- [X] T012 [P] 在 `<app>/models.py` 實作：`AttemptKind`（`WRITE`／`RETRY`）、`AttemptStatus`（`IN_PROGRESS`／`SUCCESS`／`FAILED`／`PENDING`）、`AttemptReason`（`NOT_AUTHORIZED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`REJECTED`、`RATE_LIMITED`、`STRUCTURE_CHANGED`、`NOT_CONFIGURED`、`NOT_WRITTEN`、`UNKNOWN`）、`ExportRejection`（`StrEnum`，成員與 http-api.md 錯誤表逐項一致）、`Result[T]`（與 001／002 同形：`ok`、`value`、`rejection`）、`WriteAttempt`（`attempt_id`、`kind`、`snapshot_id`、`items`、`status`、`reason`、`differences`、`cell_checks`、`started_at`、`finished_at: datetime | None`）、`PreviewView`
- [X] T013 [P] 在 `<app>/messages.py` 實作訊息與狀態碼對照表（http-api.md 錯誤表逐項；`STALE_SNAPSHOT`：「成果已更新，請重新預覽後再確認。」；`NO_RESULTS`：「目前沒有可寫回的結果。」；授權類訊息指引重新授權或調整權限；`GOOGLE_NOT_CONFIGURED`：只說「尚未設定 Google 連線」，不含變數名稱），另提供 `AttemptReason` 的老師可讀說明（依賴 T007 先失敗）
- [X] T014 [P] 在 `<app>/ports.py` 定義 `SheetsWriter`（Protocol：`read_cells(code, source, targets) -> Result[Mapping[CellRef, CurrentCell]]`、`write_text_cells(code, source, cells) -> WriteResult`，皆 `async`）與 `WriteResult`（`outcome: OutcomeStatus`、`reason: AttemptReason | None`）；另定義服務依賴的唯讀 Protocol：`ExportActivityGateway`（`export_view`、`get`、`resolve_requester`、`add_snapshot_extension`）、`ImportRecords`（`get_import_record`）、`SubmissionReader`（`all_submissions`）、`RankingReader`（`finalized_rounds`），型別沿用 001～004 的既有定義
- [X] T015 在 `<app>/store.py` 實作 `ExportStore`（記憶體）：`attempts: dict[str, list[WriteAttempt]]`、`lock(code)`（每活動一把 `asyncio.Lock`）、`add_attempt`、`replace_latest`、`latest`、`next_id`（每活動從 1 遞增）（依賴 T008）
- [X] T016 在 `<app>/service.py` 建立 `ExportService` 骨架：建構子接收 `activity`、`imports`、`auth`（`AuthGateway`）、`reader`（`SheetsReader`）、`writer`（`SheetsWriter`）、`submissions`、`ranking`、`store`、`publisher`、`clock`；建構時呼叫 `activity.add_snapshot_extension(self.snapshot_extension)`；`snapshot_extension` 先回傳 `{}`；其餘方法先留 `NotImplementedError`；模組 docstring 寫明「Google I/O 與推送在鎖外、日誌只記活動代碼／嘗試編號／快照識別／格數／結果與原因類別」（依賴 T009、T014、T015）
- [X] T017 在 `<web>/result_export.py` 建立 `create_router(app: FastAPI) -> APIRouter`（先回傳空 router，端點由各 Story 加入）；在 `src/lecture_quiz/main.py` 新增 `_wire_export(app, sheets_writer)`（建立 `ExportService(...)` 並設 `app.state.export_service`；**本任務的預設寫入器為 `None`**：服務在第一次需要寫入器時才取用，沒有時回明確錯誤，**模組載入時（`main.py` 底部的 `app = create_app()`）不得建立任何 Google 物件**；真實 `GoogleSheetsWriter` 由 T046 實作、T047 才接上，共用 002 的 `GoogleAuthGateway`）、`create_app` 新增參數 `export_sheets_writer: SheetsWriter | None = None`，以及「子功能 router」區塊的**一行** `api.include_router(result_export.create_router(app))  # 005`；組裝順序在 004 之後（依賴 T010、T016）
- [X] T018 執行 `pytest -m "not real_google and not perf"`（含 `tests/architecture/test_core_is_pure.py`，確認它掃到新的 `core/result_export/`）：T006～T010 通過，T002 的基準測試全部維持通過；把結果數字寫入 `verification.md`

**Checkpoint**: 型別、訊息、存放區、連接埠與組裝就緒；001～004 既有測試全部通過

---

## Phase 3: User Story 1 - 預覽定案成果並手動確認寫回 (Priority: P1) 🎯 MVP 起點

**Goal**: 老師看到預覽（只含已定案、有搶答成功者的題；欄位完整；覆寫影響）並手動確認；確認綁定成果快照；沒有成果、取消、非老師都拒絕；活動中與結束後皆可；系統不自動寫回

**Independent Test**: 兩輪資料（第一輪已定案、第二輪搶答中）預覽只含第一輪；確認後只寫第一輪答案；再定案第二輪後用舊預覽確認被拒絕

### Tests for User Story 1（先寫、確認失敗）⚠️

- [X] T019 [P] [US1] 在 `tests/unit/core/result_export/test_snapshot.py` 測試 `build_snapshot`：只依傳入的已定案成果產生項目（`Scenario: US1-AS1` ↔ OpenSpec「活動中匯出歷史成果」）；單題一列、題組每個子空格一列，欄位含題號、子空格、搶答成功者組號、答案、目標位置、覆寫影響（`Scenario: US1-AS2`）；`unwritten_questions` 含無人提交、全被判錯、尚未成功的題且依題號排序（`Scenario: US1-AS2`）；覆寫影響：`EMPTY`／`REPLACE`（附原內容、截斷至 40 字元）／`SAME`（`TEXT` 且逐字相同；數字、公式、布林一律 `REPLACE`）；一題跨多輪只寫成功那一筆（`MULTI_ROUND_WORLD`）；找不到搶答成功者的提交、`answers` 長度不等於格數、同一題兩個搶答成功者時明確失敗（拋 `ValueError`，不略過）；相同輸入重複呼叫輸出逐項相同（確定性）
- [X] T020 [P] [US1] 在 `tests/unit/core/result_export/test_snapshot_id.py` 測試 `snapshot_id_of`：輪次集合 `{1, 2}` → `"1.2"`、順序無關；空集合 → `""`；新增輪次後識別改變，重複呼叫相同（`Scenario: US1-AS3` ↔ OpenSpec「預覽後新增定案結果」）
- [X] T021 [P] [US1] 在 `tests/unit/app/result_export/test_preview.py` 用 `export_env` 測試 `ExportService.preview`：搶答中的第二輪不進預覽、只含第一輪（`Scenario: US1-AS1`）；預覽欄位與純文字原內容（含 HTML 標記的答案原樣保留，不跳脫成其他字元，前端以 `textContent` 顯示）（`Scenario: US1-AS2`）；沒有已定案且有搶答成功者的題 → `NO_RESULTS`，`FakeSheetsWriter` 的寫入呼叫數為 0（`Scenario: US1-AS4` ↔ OpenSpec「沒有可寫回答案」）；學生、其他活動老師、匿名 → `NOT_TEACHER`，回傳不含老師專用資料（`Scenario: US1-AS5`）；已取消 → `ACTIVITY_CANCELLED`，不呼叫任何 Google 連接埠（`Scenario: US1-AS7`）；準備中與開放加入 → `NO_RESULTS`
- [X] T022 [P] [US1] 在 `tests/unit/app/result_export/test_confirm_gate.py` 測試 `confirm_write` 閘門：預覽後又有新輪次定案，用舊 `snapshot_id` 確認 → `STALE_SNAPSHOT`、寫入呼叫數 0、不擴大範圍（`Scenario: US1-AS3`）；非老師 → `NOT_TEACHER`（`Scenario: US1-AS5`）；已取消 → `ACTIVITY_CANCELLED`（`Scenario: US1-AS7`）；活動已結束且已有定案成果時預覽與確認照常（`Scenario: US1-AS6`）；定案、結束事件發生時 `FakeSheetsWriter` 寫入呼叫數始終為 0（不自動寫回）（`Scenario: US1-AS6`）
- [X] T023 [P] [US1] 在 `tests/contract/result_export/test_http_preview_write.py` 測試 X1、X2：回應形狀符合 http-api.md（`snapshotId`、`canConfirm`、`structure`、`items[].target` 為 A1 顯示位置、`impact`、`unwrittenQuestions`、`sheetTitle`）；`target` 由列欄換算（0 起算 → `C7` 形式）；`INVALID_REQUEST`（缺 `snapshotId`、非字串）400；`NOT_TEACHER` 403；帶 token 但活動不存在 410 `ACTIVITY_GONE`；`NO_RESULTS`、`STALE_SNAPSHOT`、`ACTIVITY_CANCELLED` 409；所有錯誤回應通過 T007 的訊息安全檢查
- [X] T024 [US1] 在 `tests/integration/test_export_us1_two_rounds.py` 用 `import_client`（002 真實 `ImportService` + `FakeSheetsReader`，版面 A）＋ 003 真實提交 ＋ 004 真實順位，建立兩輪世界（第一輪已定案、第二輪搶答中，含題組、單題與一題無人成功），經 HTTP 預覽與確認：只寫入第一輪搶答成功者答案，第二輪暫時提交不在其中（`Scenario: US1-AS1`、`US1-AS6`）

### Implementation for User Story 1 — 核心

- [X] T025 [P] [US1] 在 `<core>/snapshot.py` 實作 `snapshot_id_of(round_numbers) -> str`（遞增排序後以點連接，空集合為空字串）與 `build_snapshot(...)`（演算法逐步照 data-model「成果快照」：找搶答成功者的 `SubmissionFact`、依 `BlankTarget` 展開、算覆寫影響、算 `unwritten_questions`、資料不一致時 `ValueError`）；純函式，無 I/O、無時間參數（依賴 T019、T020）

### Implementation for User Story 1 — 服務層

- [X] T026 [US1] 在 `<app>/service.py` 實作閘門 `_gate(code, requester)`（`export_view`：活動不存在、非老師、已取消依序判定，轉成 `ExportRejection`）與 `_collect(code)`（取 004 `finalized_rounds`、003 `all_submissions` 只留已定案輪次、002 `get_import_record`；轉成核心輸入型別）；**判定順序固定**：先看有沒有已定案輪次，沒有、或已定案但沒有任何搶答成功者 → 直接 `NO_RESULTS`（此時不需要匯入記錄，準備中與開放加入的活動也走這條，CSV 同理直接回只含表頭的結果）；只有確定有已定案且有搶答成功者的成果卻取不到匯入記錄時才回 `NO_IMPORT_RECORD`（依賴 T021、T025）
- [X] T027 [US1] 在 `<app>/service.py` 實作 `preview(code, requester)`：閘門 → `_collect` → 以 002 `SheetsReader.read` 與 `SheetsWriter.read_cells` 取目前內容 → `build_snapshot` → 回傳 `PreviewView`（`structure` 在 US2 加入，本任務先回 `ok=true`）；不改變任何狀態、不寫 Google
- [X] T028 [US1] 在 `<app>/service.py` 實作 `confirm_write(code, requester, snapshot_id)` 的 US1 部分：閘門 → 重新計算目前 `snapshot_id`，不相等 → `STALE_SNAPSHOT` → 以 `build_snapshot` 的項目呼叫 `SheetsWriter.write_text_cells` → 記錄 `WriteAttempt` 並回傳（進行中控制、結構檢查、狀態分類在 US4、US2 加入；本任務保證「沒有成果不寫入」「陳舊快照不寫入」）（依賴 T022、T027）

### Implementation for User Story 1 — 外層

- [X] T029 [US1] 在 `<web>/result_export.py` 實作 X1（`POST /activities/{code}/export/preview`）與 X2（`POST /activities/{code}/export/writes`）：老師 token 由 001 `resolve_requester` 解析；`ExportRejection` 轉成 http-api.md 的狀態碼與 `{"error": {"code", "message"}}`；`items[].target` 用列欄換算 A1 字串（在 web 層做，核心只回 `CellRef`）；以 `annotate_request_log` 補活動代碼與結果碼；**同時建立集中的 `Attempt` JSON 序列化函式**（欄位依 http-api.md 的 `Attempt`：`status`、`reason`、`totalCells`、`confirmedCells`、`notWrittenCells`、`pendingCells`、`differences`、`cellChecks`、`startedAt`、`finishedAt`、`alreadyInProgress`），US4 的 X3、X4、X5 與老師快照的 `export` 摘要共用它，不另寫（依賴 T023、T028）
- [X] T030 [US1] 在 `<static>/teacher.html` 加 `<section id="export-section" data-feature="005-result-export">` 與一行 `<script type="module" src="js/result-export.js">`（只加在「子功能區塊／子功能 script」標記內）；在 `<static>/js/result-export.js` 實作預覽表格與「確認寫回」按鈕（確認帶預覽拿到的 `snapshotId`）、`STALE_SNAPSHOT` 時提示「請重新預覽」並自動隱藏舊預覽；**所有答案、原內容、組號一律 `textContent`**；`<static>/css/app.css` 末端追加樣式（依賴 T029）

**Checkpoint**: 老師能預覽並手動確認；沒有成果、陳舊快照、取消、非老師都不會寫入；US1 的測試通過

---

## Phase 4: User Story 2 - 寫入前重新檢查來源結構，不符就整次停止 (Priority: P1)

**Goal**: 每次預覽、寫入與重試前重新讀取並以 002 的規則重新辨識、逐項比對；不符整次停止、指出差異、零寫入；作答文字與工作表改名不算變更；授權問題屬明確失敗並有重新授權入口（任何非取消階段）

**Independent Test**: `layout_a`、`layout_b` 各做「插入列使答案格位移但表頭仍在」「題號被改」「合併被改」「表頭被刪」「工作表被刪」，全部零寫入；「只改作答文字」「只改工作表名稱」照常寫入

### Tests for User Story 2（先寫、確認失敗）⚠️

- [X] T031 [P] [US2] 在 `tests/unit/core/result_export/test_structure.py` 對 `layout_a`、`layout_b` 各測試 `compare_structure`：相同快照 → `ok`（`Scenario: US2-AS3` ↔ OpenSpec「只有原答案內容改變」）；只改作答格文字 → `ok`（`Scenario: US2-AS3`）；只改工作表名稱（`SheetSnapshot.sheet_name`）→ `ok`；改動與表頭列及資料區無關的區域（資料區之上的說明合併）→ `ok`（FR-009）；在表頭與資料之間插入列、表頭文字仍在 → `HEADER_POSITION`／`QUESTION_NUMBER`／`ANSWER_CELL` 至少一類且 `ok=False`（`Scenario: US2-AS1` ↔ OpenSpec「表頭不變但答案列移動」）；題號被改 → `QUESTION_NUMBER`；子編號被刪 → `SUB_BLANK`；合併被拆開或合併 → `MERGE_RANGE`；表頭被刪（`reparsed.ok` 為假）→ 單一 `UNRECOGNIZED`（`Scenario: US2-AS2`）；差異依位置排序、相同輸入輸出逐項相同；`StructureDifference.detail` 不含試算表文字
- [X] T032 [P] [US2] 在 `tests/unit/app/result_export/test_structure_gate.py` 用 `export_env` 測試服務層：結構不符時 `confirm_write` 回 `Attempt(status=FAILED, reason=STRUCTURE_CHANGED)` 且 `FakeSheetsWriter` 寫入呼叫數為 0、任何格都沒被改（`Scenario: US2-AS1`、`US2-AS2`；SC-003）；`SheetsReader.read` 回 `SHEET_NOT_FOUND`（工作表被刪或換掉）→ `IDENTITY` 差異、零寫入（`Scenario: US2-AS2`）；結構相符但作答格已有其他文字 → 照常寫入（`Scenario: US2-AS3`）；寫入前的檢查涵蓋**全部**目標格才送出，不會先寫一部分（`Scenario: US2-AS4`）；預覽時結構不符 → `structure.ok=false`、`canConfirm=false` 且項目仍以匯入時位置顯示（FR-007）；預覽的差異最多回 20 筆並附 `moreDifferences`
- [X] T033 [P] [US2] 在 `tests/unit/app/result_export/test_auth_failures.py` 測試授權與讀取失敗：`SheetsReader.read` 回 `NOT_AUTHORIZED`／`AUTH_EXPIRED`／`PERMISSION_DENIED`／`READ_FAILED`／`GOOGLE_NOT_CONFIGURED` 時，預覽回對應的 401／401／403／502／503 錯誤碼；`confirm_write` 在**送出任何寫入之前**停止並記為 `FAILED` 與對應 `AttemptReason`（`Scenario: US2-AS5`）；訊息指引重新授權或調整權限、不含憑證（`Scenario: US2-AS5`）；此失敗屬明確失敗（寫入呼叫數 0）
- [X] T034 [P] [US2] 在 `tests/unit/app/result_export/test_reauthorization.py` 測試 `start_authorization`：在準備中、開放加入、搶答中、結果未定案、結果已定案、已結束都可取得授權網址（`Scenario: US2-AS5`；clarify Q1）；已取消 → `ACTIVITY_CANCELLED`；非老師 → `NOT_TEACHER`；`AuthGateway.is_configured()` 為假 → `GOOGLE_NOT_CONFIGURED`；回傳的網址由 `FakeAuthGateway` 產生、日誌不含網址與 `state`；**不呼叫 002 `ImportService` 的任何方法**（plan R8：以 mock 斷言）
- [X] T035 [P] [US2] 在 `tests/contract/result_export/test_http_authorization.py` 測試 X6：`POST /activities/{code}/export/authorization` 回 `200 {"authUrl"}`；階段與身分錯誤的狀態碼符合 http-api.md；授權完成後沿用 002 的 `GET /api/oauth/callback`（以 `FakeAuthGateway` 驗證導回 `/teacher.html?code=…&auth=ok`，005 沒有新增回呼端點）

### Implementation for User Story 2 — 核心

- [X] T036 [US2] 在 `<core>/structure.py` 實作 `compare_structure(imported: StructureSnapshot, reparsed: ParseResult) -> StructureCheck`（演算法逐步照 data-model「結構比對」：`reparsed.ok` 為假 → `UNRECOGNIZED`；比對 `header_number`／`header_answer`／`answer_cols`／`data_start_row` → `HEADER_POSITION`、`row_numbers` → `QUESTION_NUMBER`、`answer_cells` 鍵 → `SUB_BLANK`、同鍵不同位置 → `ANSWER_CELL`、`merges` → `MERGE_RANGE`；收集全部差異、依（列, 欄, 類別）排序；`detail` 為固定類別說明）；純函式（依賴 T031）

### Implementation for User Story 2 — 服務層

- [X] T037 [US2] 在 `<app>/service.py` 實作 `_check_source(code, record)`：`SheetsReader.read(code, record.source)` → 失敗時依 `ImportRejection` 轉成 `AttemptReason`／`ExportRejection`（`SHEET_NOT_FOUND` → `IDENTITY` 差異；`NOT_AUTHORIZED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`READ_FAILED`、`GOOGLE_NOT_CONFIGURED` 各自對應）→ 成功時 `GuidedNotesParser.parse(snapshot)` → `compare_structure`；回傳 `StructureCheck` 與目前 `SheetSnapshot`（供覆寫影響與標題使用）（依賴 T032、T033、T036）
- [X] T038 [US2] 把 `_check_source` 接進 `preview`（`structure` 欄位、`canConfirm`、差異最多 20 筆並附 `moreDifferences`）與 `confirm_write`（在寫入前；不符或讀取失敗 → 記為 `FAILED` 且**不呼叫** `write_text_cells`；日誌只記結果類別與原因代碼）
- [X] T039 [US2] 在 `<app>/service.py` 實作 `start_authorization(code, requester)`：閘門（活動存在、老師、非已取消）→ `AuthGateway.is_configured()` → `AuthGateway.start_authorization(code, requester)`；不經過 `ImportService`；日誌只記活動代碼與結果（依賴 T034）

### Implementation for User Story 2 — 外層

- [X] T040 [US2] 在 `<web>/result_export.py` 實作 X6（`POST /activities/{code}/export/authorization`）；X1 的回應加入 `structure` 與 `moreDifferences`，`differences[]` 的 `row`、`col` 轉成 1 起算顯示值（欄以字母）（依賴 T035、T039）
- [X] T041 [US2] 在 `<static>/js/result-export.js` 加入：結構不符時顯示差異清單並停用「確認寫回」；授權錯誤時顯示訊息與「重新授權」按鈕（呼叫 X6、`window.location.assign(authUrl)`）；頁面載入時若網址帶 `auth=ok` 自動重新預覽並清掉參數——**注意 002 的 `import.js` 會在收到第一份快照後自己刪除 `auth` 參數並 `replaceState`**，所以 `result-export.js` 必須在**模組載入時同步**讀取並記住 `auth` 的值（早於任何快照事件），不得等快照或 WebSocket 事件之後才讀；清除參數時不得影響 002 的處理（只在自己已讀取後才可能清除，且不修改 `import.js`）；此行為由 quickstart 第 10、11 步人工驗證，並在 `tests/architecture/test_static_text_safety.py` 旁加一個靜態檢查，確認 `result-export.js` 在模組頂層讀取 `window.location.search`；一律 `textContent`

**Checkpoint**: 結構不符與授權失敗都零寫入；任何非取消階段都能重新授權；US2 測試通過

---

## Phase 5: User Story 3 - 答案精確寫入目標格，其他內容完全保留 (Priority: P1)

**Goal**: 單一 `batchUpdate`、每格一個 `updateCells`、`stringValue` 逐字寫入、`fields="userEnteredValue"`；題組編號格不寫；成功題取代原內容、未成功題保留；兩份版面皆正確

**Independent Test**: `layout_a`、`layout_b` 各以含兩格題組與單題的成果寫回後逐格比對：三個答案格正確、其他儲存格的值、格式、合併與寫回前完全相同；公式字樣、前導零、類日期、換行、前後空白逐字相同

### Tests for User Story 3（先寫、確認失敗）⚠️

- [X] T042 [P] [US3] 在 `tests/unit/adapters/google/test_sheets_writer_request.py` 以 `HttpMockSequence` 測試 `GoogleSheetsWriter.write_text_cells` 的請求形狀：只送**一個** `spreadsheets.batchUpdate`；每個目標格一個 `updateCells`，`range` 為 `sheetId` 與 `startRowIndex=r`、`endRowIndex=r+1`、`startColumnIndex=c`、`endColumnIndex=c+1`（`Scenario: US3-AS1`、`US3-AS6`：合併作答格只寫左上角）；`rows[0].values[0].userEnteredValue` 只有 `stringValue`、內容與答案逐字相同（`=1+1`、`00123`、`1/2`、`3.0`、含換行、前後空白、以單引號開頭）（`Scenario: US3-AS3`、`US3-AS4` ↔ OpenSpec「類似公式的答案」）；`fields` 恰為 `"userEnteredValue"`（不更動格式與合併）；答案不被加上保護前綴（FR-013）；不含 `valueInputOption`；使用 `sheetId` 而非工作表名稱（工作表改名不影響）
- [X] T043 [P] [US3] 在 `tests/unit/adapters/google/test_sheets_writer_read.py` 以 `HttpMockSequence` 測試 `read_cells`：`userEnteredValue` 為 `stringValue` → `TEXT`、無值 → `EMPTY`、`numberValue`／`boolValue`／`formulaValue` → `OTHER`（`display` 為純文字）；請求只要 `sheets(properties(sheetId),data(startRow,startColumn,rowData(values(userEnteredValue))))` 欄位；`rowData` 省略結尾空格時正確還原絕對座標；目標格不在回應範圍內 → `EMPTY`
- [X] T044 [P] [US3] 在 `tests/integration/test_export_us3_two_layouts.py` 對 `layout_a`、`layout_b` 各以 `FakeSheetsWriter`（記憶體格子表，由版面快照初始化）端到端：預覽 → 確認寫回後，**逐格**比對——目標格內容與預期相同、其餘所有儲存格的值與合併範圍與寫回前相同（差異數 0，SC-002）；題組的子編號格與題號未被寫入（`Scenario: US3-AS1` ↔ OpenSpec「混合題型寫回」、`US3-AS2`：縱向合併與相鄰重複題號兩種題組表示、起始列欄與工作表名稱不同，沒有寫死位置）；**寫入後立即再預覽，結構仍「相符」且覆寫影響變成 `SAME`**（research R5 風險）——並斷言寫入前後 `FakeSheetsReader.read` 讀到的目標格內容確實不同（證明替身共用狀態、這個測試不會空轉通過；T004）；成功題的作答格原有佔位文字被取代、未成功題的佔位文字保留（`Scenario: US3-AS5`）
- [X] T045 [P] [US3] 在 `tests/unit/app/result_export/test_exact_write.py` 測試服務層組出的寫入內容：從快照到 `write_text_cells` 的 `cells` 引數，每格 `(CellRef, 答案原文)` 與 003 保存的答案逐字相同（含換行與前後空白，不 `strip`、不正規化）（`Scenario: US3-AS4`）；單題只有一格、題組每個子空格一格、位置全部來自 002 的 `Blank.target`（`Scenario: US3-AS1`）；沒有成功的題沒有任何目標格（`Scenario: US3-AS5`）

### Implementation for User Story 3 — 轉接層

- [X] T046 [US3] 在 `<google>/sheets_writer.py` 實作 `GoogleSheetsWriter`（建構子接收 `CredentialsProvider`（沿用 002 `GoogleAuthGateway.valid_credentials`）與 `service_factory`，測試傳入 `HttpMockSequence` 建的資源；呼叫一律 `asyncio.to_thread`）：`read_cells`（research R4：`spreadsheets.get` 以欄位遮罩只取 `userEnteredValue`，轉成 `CurrentCell`）與 `write_text_cells`（research R3：單一 `batchUpdate`、每格一個 `updateCells`、`stringValue`、`fields="userEnteredValue"`、`execute()` 不自動重試）；回應分類先只處理 200 → `SUCCESS`，4xx／5xx／例外的完整分類由 T060 完成；Google 的型別與例外不得外洩到應用層；模組 docstring 寫明「依據：已安裝 google-api-python-client 2.202.0 內附的 sheets.v4 文件（revision 20261019）」與 R17 的待真實驗證項目（依賴 T042、T043）
- [X] T047 [US3] 在 `src/lecture_quiz/main.py` 的 `_wire_export` 接上真實 `GoogleSheetsWriter`（共用 002 的 `GoogleAuthGateway`，與 002 讀取器相同的組裝方式）；測試仍可由 `export_sheets_writer` 注入假的（依賴 T046）

### Implementation for User Story 3 — 服務層

- [X] T048 [US3] 在 `<app>/service.py` 的 `confirm_write` 把「快照項目 → `cells`」落實：目標位置只取快照項目的 `target`，答案逐字傳入 `write_text_cells`；寫入成功時記為 `SUCCESS`、三個格數依 data-model「狀態與格數對照」填入（已確認寫入＝項目數）（依賴 T045、T046）

**Checkpoint**: 兩份版面都寫入正確、其他內容完全保留；寫入後結構仍相符；US3 測試通過。**US1～US3 合起來是寫回的 MVP**

---

## Phase 6: User Story 4 - 寫回結果明確區分成功、失敗與待確認，可安全重試 (Priority: P2)

**Goal**: 三種結果誠實呈現；無法證實時為待確認；重新核對只讀取；重試冪等且每次重新檢查結構；寫回不改變活動結果；同活動一次一個寫入；狀態 2 秒內推送給老師

**Independent Test**: 模擬成功、結構失敗、授權失效、請求後連線中斷；待確認狀態分別在「實際已寫入」「實際未寫入」「只寫入一部分」三種實況下核對，並重試 ≥ 5 次，內容相同且活動結果不變

### Tests for User Story 4（先寫、確認失敗）⚠️

- [X] T049 [P] [US4] 在 `tests/unit/adapters/google/test_sheets_writer_outcomes.py` 以 `HttpMockSequence` 與例外替身測試回應分類（research R6 表逐列）：200 → `SUCCESS`；401 → `FAILED(AUTH_EXPIRED)`；403、404 → `FAILED(PERMISSION_DENIED)`；400 → `FAILED(REJECTED)`；429 → `FAILED(RATE_LIMITED)`；500、503、`socket.timeout`、`TimeoutError`、`httplib2.HttpLib2Error`、`OSError` → `PENDING(UNKNOWN)`；憑證取得失敗（`valid_credentials` 回失敗）→ `FAILED` 且**未送出請求**；程式錯誤（例如 `KeyError`）照常往上拋、不被吞掉；日誌只記狀態碼與原因代碼，不含例外訊息本文
- [X] T050 [P] [US4] 在 `tests/unit/core/result_export/test_reconcile.py` 測試 `reconcile`：全部 `TEXT` 且逐字相同 → `SUCCESS`；全部不符（含 `EMPTY`、`OTHER`）→ `FAILED`；部分符合 → `PENDING` 並在 `checks` 標出不符的格（`Scenario: US4-AS2`）；`checks` 逐格含預期與目前內容（純文字）；數字 `123` 與預期 `"123"` 視為不符；相同輸入輸出逐項相同
- [X] T051 [P] [US4] 在 `tests/unit/app/result_export/test_pending_and_recheck.py` 測試：`FakeSheetsWriter` 寫入回 `PENDING` → `Attempt(status=PENDING)`，不宣稱成功也不宣稱未寫入，活動中任何定案結果不回滾（`Scenario: US4-AS1` ↔ OpenSpec「外部寫入後回應遺失」）；`recheck` 在三種實況（外部已寫入／未寫入／只寫入一部分）分別得 `SUCCESS`／`FAILED(NOT_WRITTEN)`／`PENDING`＋不符格清單，`FakeSheetsWriter` 寫入呼叫數維持不變、**`SheetsReader.read` 呼叫數為 0（不做結構檢查）**、回應含 `cellChecks`（`Scenario: US4-AS2`；clarify Q2）；核對時 `SheetsWriter.read_cells` 讀取失敗（授權失效、無權限、網路）→ 回對應錯誤（`NOT_AUTHORIZED`／`AUTH_EXPIRED` 401、`PERMISSION_DENIED` 403、`READ_FAILED` 502），**該嘗試的狀態與格數不變**；三個格數依 data-model「狀態與格數對照」逐情境斷言（FR-021）
- [X] T052 [P] [US4] 在 `tests/unit/app/result_export/test_retry_idempotent.py` 測試：對同一快照 `retry` 5 次，每次 `write_text_cells` 的 `cells` 與第一次逐項相同、`FakeSheetsWriter` 的格子表最終內容與第一次相同、沒有附加重複文字（`Scenario: US4-AS3` ↔ OpenSpec「重複寫回」、SC-005）；對已 `SUCCESS` 的嘗試重試也允許；重試前結構被改 → 本次 `FAILED(STRUCTURE_CHANGED)` 且零寫入（`Scenario: US4-AS5`）；`retry` 與 `recheck` 只作用在最新一次嘗試，否則 `NOT_LATEST_ATTEMPT`；嘗試不存在 → `ATTEMPT_NOT_FOUND`
- [X] T053 [P] [US4] 在 `tests/unit/app/result_export/test_read_only_for_activity.py` 測試：成功、失敗、待確認、核對、重試各情境前後，001 的活動（階段、成功題、成功次數、`version`）、004 的 `finalized_rounds()`、003 的 `all_submissions()` 以深度比較完全相同（`Scenario: US4-AS4`；SC-005：各組成功次數與搶答成功者差異數 0）；005 沒有呼叫任何 001～004 會改變狀態的方法（以 mock 斷言）
- [X] T054 [P] [US4] 在 `tests/unit/app/result_export/test_in_progress.py` 測試併發：`FakeSheetsWriter` 在 `block()` 時，同時送兩個 `confirm_write` → `write_text_cells` 恰被呼叫 1 次，第二個回傳同一個進行中的嘗試且 `alreadyInProgress=True`（`Scenario: US4-AS6`、FR-020）；進行中時 `recheck`／`retry` → `WRITE_IN_PROGRESS`；Google I/O 進行期間 005 的每活動鎖**未被持有**（用 `RecordingPublisher` 與 `lock.locked()` 斷言），期間 `preview`、`download_csv` 仍能完成（FR-022）；推送在鎖外
- [X] T055 [P] [US4] 在 `tests/unit/app/result_export/test_status_push.py` 測試：每次嘗試進入進行中與結束各推送一次；老師快照有 `export`（形狀依 sync-websocket.md，不含逐格答案、原內容與差異清單）；**學生快照永遠沒有 `export`**；沒有嘗試時快照與原本完全相同；內容沒變時不重複推送；`finished_at` 與 `started_at` 來自 `FakeClock`，核心沒有讀時鐘（FR-021）
- [X] T056 [P] [US4] 在 `tests/contract/result_export/test_http_attempts.py` 測試 X3、X4、X5：形狀符合 http-api.md（`status`、`reason`、`totalCells`、`confirmedCells`、`notWrittenCells`、`pendingCells`、`cellChecks` 只在核對回應有值）；X2／X4 遇授權、權限、結構、限流失敗回 `200 Attempt(status=FAILED)` 而非 4xx；`NOT_LATEST_ATTEMPT`、`WRITE_IN_PROGRESS`、`ATTEMPT_NOT_FOUND` 狀態碼；X5 沒有嘗試時 `{"attempt": null}`；非老師 403；錯誤訊息通過 T007 檢查

### Implementation for User Story 4

- [X] T057 [P] [US4] 在 `<core>/reconcile.py` 實作 `reconcile(expected, current) -> Reconciliation`（演算法照 data-model「核對判定」；純函式）（依賴 T050）
- [X] T058 [US4] 在 `<google>/sheets_writer.py` 完成回應分類（research R6 表）：`HttpError` 依狀態碼；`CAUGHT` 其餘例外 → `PENDING(UNKNOWN)`；`valid_credentials` 失敗 → `FAILED`（未送出請求）；只對應成代碼，不記例外訊息本文（依賴 T049）
- [X] T059 [US4] 在 `<app>/service.py` 實作進行中控制（research R1）：`confirm_write`／`retry` 先在鎖內「檢查有無進行中並建立 `IN_PROGRESS` 嘗試」（兩者之間沒有 `await`），**鎖外**做 Google I/O，再取鎖寫回最終狀態；已有進行中則回傳該嘗試並標 `alreadyInProgress`；結束後在鎖外 `publisher.publish(activity)`；`started_at`／`finished_at` 取自 `Clock`（依賴 T054、T058）
- [X] T060 [US4] 在 `<app>/service.py` 實作 `recheck`（讀取目標格 → `reconcile`，不呼叫 `SheetsReader`，結果更新該嘗試狀態與三個格數（依 data-model「狀態與格數對照」）並推送；`FAILED(NOT_WRITTEN)` 對應全不符；讀取失敗時不更新該嘗試，只回錯誤）、`retry`（沿用嘗試的 `items`，重新做 `_check_source` 與寫入，結果以新嘗試編號記錄、`kind=RETRY`）、`latest_attempt`（依賴 T051、T052、T057、T059）
- [X] T061 [US4] 在 `<app>/service.py` 實作 `snapshot_extension(activity, viewer)`：只對 `TeacherViewer` 回傳 `{"export": {...}}`（欄位依 sync-websocket.md，不含答案、原內容、差異清單、網址），學生或沒有嘗試時回 `{}`；同步、無副作用（依賴 T055）
- [X] T062 [US4] 在 `<web>/result_export.py` 實作 X3（`recheck`）、X4（`retry`）、X5（`GET .../writes/latest`）；沿用 T029 建立的 `Attempt` JSON 序列化函式（只補上 `cellChecks` 的輸出，不另寫第二份）；日誌只記活動、嘗試編號、快照識別、格數、狀態與原因（依賴 T056、T060）
- [X] T063 [US4] 在 `<static>/js/result-export.js` 加入寫回狀態面板（三種結果與進行中、已確認／未寫入／待確認格數、原因說明）、「重新讀取核對」「重試」按鈕與逐格預期／目前內容表（`textContent`）、固定提醒文字「核對只讀取匯入時記錄的位置，不檢查學習單結構是否被改動，若您修改過學習單請自行確認」；從老師快照的 `export` 欄位即時更新（沿用 `connectSync`），頁面重新整理時呼叫 X5 恢復（依賴 T062）

**Checkpoint**: 三種結果誠實、核對與重試正確、併發安全、狀態推送到所有老師分頁；US4 測試通過

---

## Phase 7: User Story 5 - 下載完整的搶答紀錄 CSV (Priority: P2)

**Goal**: 老師隨時下載已定案輪次的全部已接受提交（含搶答失敗與答錯），九欄固定順序、每提交子空格一列、題組共用順位與勝負、答錯列順位留空；未定案輪次不納入；無資料時只有表頭；不依賴 Google 與寫回

**Independent Test**: 一個已定案輪次（兩組各提交一個兩格題組、其中一組被判錯）、一題無人提交、一個未定案輪次：逐列比對欄位、列數、順位與是否成功；無定案輪次時只有表頭

### Tests for User Story 5（先寫、確認失敗）⚠️

- [X] T064 [P] [US5] 在 `tests/unit/core/result_export/test_build_rows.py` 測試 `build_rows`：兩組各提交兩格題組、其中一組被判錯 → 4 筆資料列，被判錯組兩列 `rank=None`、`succeeded=False`、`judged_wrong=True`，另一組兩列共用 `rank=1`、`succeeded=True`、`judged_wrong=False`（`Scenario: US5-AS1` ↔ OpenSpec「題組與判錯紀錄」）；三個候選排名 1、2、3 且都沒被判錯 → 三組各有資料列、只有順位 1 的 `succeeded=True`、`judged_wrong` 皆 `False`，列排序固定（輪次, 題號, 順位, 子空格）（`Scenario: US5-AS4`）；被判錯而無順位者排在該題有順位者之後、彼此依接收時間；無人提交的題不產生任何列、未定案輪次的提交不會進來（呼叫端已過濾，另測「傳入含未定案輪次提交仍不產生列」）（`Scenario: US5-AS2` ↔ OpenSpec「沒有提交與未定案輪次」）；單題 `sub_index=None`、題組 1..n；某題第一輪全被判錯、第二輪由另一組成功 → 兩輪各有列並以 `round_number` 區分（`Scenario: US5-AS6`）；找不到對應提交時明確失敗；確定性
- [X] T065 [P] [US5] 在 `tests/unit/app/result_export/test_download_csv.py` 測試 `download_csv`：只含已定案輪次（`FakeSubmissionReader` 含未定案輪次提交，證明被過濾）（`Scenario: US5-AS2`）；沒有已定案輪次（準備中、開放加入、第一輪尚未定案）→ 只含表頭列的有效 CSV（`Scenario: US5-AS3`）；Google 未授權、授權過期、`FakeSheetsWriter` 設為失敗或待確認時仍能下載且內容不變（`Scenario: US5-AS5`、FR-022）；已取消 → `ACTIVITY_CANCELLED`、非老師 → `NOT_TEACHER`；活動結束後照常
- [X] T066 [P] [US5] 在 `tests/contract/result_export/test_http_csv.py` 測試 X7：`200`、`Content-Type: text/csv; charset=utf-8`、`Content-Disposition: attachment; filename="quiz-results-<活動代碼>.csv"`、`Cache-Control: no-store`；本文以 UTF-8 BOM 開頭；已取消 409、非老師 403；沒有資料時只有表頭一列
- [X] T067 [US5] 在 `tests/integration/test_export_us5_csv.py` 用 `import_client` 世界（002 真實 `ImportService`、003 真實提交、004 真實順位與判錯、含題組與一筆被判錯、一題無人提交、一個未定案輪次）端到端下載並以 `csv.reader` 逐列比對（`Scenario: US5-AS1`～`US5-AS4`）

### Implementation for User Story 5

- [X] T068 [P] [US5] 在 `<core>/csv_export.py` 實作 `build_rows(entries, submissions, blanks) -> tuple[ExportRow, ...]`（演算法照 data-model「CSV 資料列」：展開子空格、`rank`／`succeeded`／`judged_wrong` 取自 004 結果不重算、排序鍵（輪次, 題號, 被判錯者排後, 順位, 接收時間, 子編號）、找不到對應提交明確失敗）；`render_csv` 與 `protect_text` 在 US6 完成（依賴 T064）
- [X] T069 [US5] 在 `<app>/service.py` 實作 `download_csv(code, requester)`：閘門（取消／非老師）→ 取 004 已定案輪次、003 全部提交**只留已定案輪次**、002 `ImportRecord.blanks` → `build_rows` → `render_csv` → 編碼為 UTF-8 加 BOM 的 `bytes`；沒有已定案輪次時**不讀取匯入記錄**，直接輸出只含表頭的結果（準備中與開放加入的活動可能還沒有匯入記錄）；不呼叫任何 Google 連接埠（依賴 T065、T068）
- [X] T070 [US5] 在 `<web>/result_export.py` 實作 X7（`GET /activities/{code}/export/csv`）：回應標頭依 http-api.md；以 `annotate_request_log` 記活動代碼與結果碼，不記內容（依賴 T066、T069）
- [X] T071 [US5] 在 `<static>/js/result-export.js` 加入「下載 CSV」按鈕：以 `fetch` 帶 `Authorization` 取得 blob，再以暫時網址觸發下載（`api.js` 只處理 JSON，不修改它）；失敗時以 `textContent` 顯示錯誤（依賴 T070）

**Checkpoint**: CSV 內容與列數正確、只含已定案輪次、不依賴 Google；US5 測試通過

---

## Phase 8: User Story 6 - CSV 在常見試算表軟體中可讀，且不會執行惡意公式 (Priority: P2)

**Goal**: UTF-8＋BOM、CRLF、逗號／引號／換行正確、時間含時區與毫秒、「是／否」、組別與答案文字保護、介面說明保護前綴只影響 CSV

**Independent Test**: 提交含逗號、引號、換行與以 `=`、`+`、`-`、`@`、tab 開頭的答案，下載後以嚴格 CSV 解析器還原欄位數與內容；原始提交與寫回的答案沒有保護前綴

### Tests for User Story 6（先寫、確認失敗）⚠️

- [X] T072 [P] [US6] 在 `tests/unit/core/result_export/test_render_csv.py` 測試 `render_csv`：表頭恰為 `輪次,題號,子空格,組別,答案,送出時間,順位,是否成功,是否被判錯`；至少 10 筆樣本（逗號、雙引號、換行、`\r\n`、各種公式開頭）以 `csv.reader` 解析後每列欄位數皆為 9、內容還原差異（保護前綴除外）為 0（`Scenario: US6-AS1`；SC-007）；`rank`、`sub_index` 為 `None` 輸出空字串；布林輸出「是」「否」（`Scenario: US6-AS5`）；時間輸出為 `isoformat(timespec="milliseconds")` 含時區位移，兩筆接收時間差 1 毫秒的提交輸出不同（`Scenario: US6-AS4`）；行結尾為 `\r\n`；相同輸入輸出逐位元組相同
- [X] T073 [P] [US6] 在 `tests/unit/core/result_export/test_protect_text.py` 測試 `protect_text`：以 `=`、`+`、`-`、`@`、`\t`、`\r` 開頭 → 前面加 `'`；其他字元或空字串原樣；只套用在「組別」與「答案」欄，輪次、題號、時間、順位、是／否欄**不**被加前綴（`Scenario: US6-AS2` ↔ OpenSpec「特殊文字匯出」）；答案 `-5` 也被保護（介面說明涵蓋）；保護後再以 `csv.reader` 解析，去掉第一個 `'` 即為原答案
- [X] T074 [P] [US6] 在 `tests/integration/test_export_us6_safety.py` 用世界資料提交 `=1+1`、含逗號與換行的答案：CSV 內容經保護但 003 保存的原始提交、004 結果、以及寫回時送給 `write_text_cells` 的答案**都沒有**保護前綴（`Scenario: US6-AS3`、FR-029）；CSV 位元組以 UTF-8 BOM 開頭、繁體中文表頭與答案可還原（`Scenario: US6-AS5`）
- [X] T075 [P] [US6] 在 `tests/architecture/test_static_text_safety.py` 擴充（追加，不改既有斷言）：`result-export.js` 不含 `innerHTML`、`outerHTML`、`insertAdjacentHTML`、`document.write`、`eval`；且頁面（`teacher.html` 的匯出區塊或 `result-export.js`）含保護前綴說明固定文字「文字保護前綴只為安全開啟，不代表原答案被修改」（`Scenario: US6-AS3`、FR-029）

### Implementation for User Story 6

- [X] T076 [US6] 在 `<core>/csv_export.py` 完成 `protect_text(value)`（`=`、`+`、`-`、`@`、`\t`、`\r` 開頭加 `'`）與 `render_csv(rows) -> str`（標準 `csv.writer`、`QUOTE_MINIMAL`、`lineterminator="\r\n"`、固定表頭、只對組別與答案欄套用 `protect_text`、時間 `isoformat(timespec="milliseconds")`、布林「是」「否」、`None` 輸出空字串）；`<app>/service.py` 的 `download_csv` 以 `"﻿" + text` 編成 UTF-8 位元組（依賴 T072、T073）
- [X] T077 [US6] 在 `<static>/teacher.html` 匯出區塊與 `<static>/js/result-export.js` 加入保護前綴說明固定文字（FR-029）；文字以固定字串設定，不由後端或使用者輸入產生（依賴 T074、T075）

**Checkpoint**: CSV 嚴格解析無誤、公式字元被保護、說明文字存在；US6 測試通過

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 跨 Story 的整體驗證、文件、效能與人工驗證

- [ ] T078 [P] 更新 `tests/SCENARIO_MAP.md`：追加 `## 005-result-export` 段落，把 US1～US6 全部 Acceptance Scenario 對應到測試（以掃描 `Scenario:` docstring 產生，沿用 003／004 的產生方式）；OpenSpec result-export 的 12 個 Scenario 逐一確認至少一個測試（SC-001）
- [ ] T079 [P] 在 `tests/integration/test_export_logging.py` 測試日誌：預覽、寫入、核對、重試、CSV 下載、重新授權各情境的日誌**不含**答案內容、原儲存格內容、試算表網址與標題、token、授權碼、`state`、client secret；只含活動代碼、嘗試編號、快照識別、格數、結果與原因類別；使用 `logging`、無 `print`（FR-033、憲章技術限制 3）
- [ ] T080 [P] 在 `tests/contract/test_error_safety.py` 追加（不改既有斷言）005 的端點：各種錯誤回應不含堆疊、檔案路徑、憑證、授權碼；Google 例外訊息本文不出現在任何回應與日誌（FR-031）
- [ ] T081 [P] 在 `tests/integration/test_export_snapshot_visibility.py` 測試資料可見性：學生 WebSocket 與 `GET snapshot` 在任何階段都沒有 `export`；學生呼叫 X1～X7 全部 403；老師快照的 `export` 不含答案、原內容與網址（憲章原則 V）
- [ ] T082 [P] 在 `tests/perf/test_export_latency.py`（`@pytest.mark.perf`，真實 uvicorn）測量：50 題規模、每活動 99 組的預覽計算（Google 以假替身，不含往返）與 CSV 產生各不超過 3 秒（SC-008）；老師＋6 組學生連線、每組 2 條時，寫回狀態變更到各老師分頁收到推送不超過 2 秒；記錄量測數字到 `verification.md`
- [ ] T083 [P] 在 `tests/real_google/test_real_export.py`（`@pytest.mark.real_google`，手動執行）實作真實路徑：缺任一必要環境變數（沿用 `REAL_GOOGLE_BASE_URL`、`REAL_GOOGLE_ACTIVITY_CODE`、`REAL_GOOGLE_TEACHER_TOKEN`、`REAL_GOOGLE_SPREADSHEET_ID`、`REAL_GOOGLE_SHEET_ID`，另加第二份試算表的 `*_B` 與寫入開關）時**明確失敗並說明缺什麼**，不得 `skip`、不得退回 mock；預覽 → 確認寫回 → 讀回驗證 R17 第 3 項（公式字樣、前導零、類日期、換行、單引號開頭）→ 再預覽結構仍相符 → CSV
- [ ] T084 在 `CLAUDE.md` 的「專案現況」追加「005-result-export 已實作」段落（程式路徑、對 001～004 沒有修改、重新授權入口與核對不做結構檢查的決定、待驗證事項）；`docs/DEVELOPMENT.md` 若有子功能列表同步更新（只追加，依擴充約定）
- [ ] T085 在 `specs/005-result-export/verification.md` 補齊「先寫測試的失敗紀錄」（各 Story 實作前的失敗數）與「自動化結果」的日期、指令、通過／失敗／略過數（憲章原則 VI、全域規則：只寫真的執行過的指令與輸出）
- [ ] T086 程式碼與圖表一致性驗證：逐一比對 `diagrams/005-result-export-component.puml`、`-class.puml`、`-sequence.puml` 與實作（模組、類別名稱、方法、流程、相依方向）；有差異時**先更新圖表並重新轉出 PNG**（只轉 005 的三個檔），並把比對結果寫入 `verification.md`（憲章原則 II）
- [ ] T087 執行 `ruff check .`、`ruff format --check .`、`mypy`，全部通過並記錄結果（憲章技術限制 2）
- [ ] T088 執行 `pytest -m "not real_google and not perf"`，確認全數通過、既有 001～004 測試不退步（與 T002 基準比較），記錄指令與通過／失敗／略過數（憲章原則 VI）
- [ ] T089 [P] 執行 `pytest -m perf tests/perf/test_export_latency.py`，記錄數字（SC-008）
- [ ] T090 執行 `tests/architecture/test_core_is_pure.py` 並確認 `core/result_export/` 被掃描且無違規：只匯入標準函式庫與 `lecture_quiz.core`，不匯入 `fastapi`、`starlette`、`asyncio`、`time`、`googleapiclient`、`google`、`httpx`，不呼叫 `datetime.now`（憲章技術限制 4）
- [ ] T091 依 [quickstart.md](quickstart.md) A 節逐步執行並核對預期結果，把差異記入 `verification.md`「問題紀錄」
- [ ] T092 檢查日誌實際輸出（啟動 `python -m lecture_quiz`，走一次預覽、寫回、CSV）：只有 `logging`（INFO、stdout），無 `print`，未記錄答案、原內容、token、授權碼、client secret（憲章技術限制 3）
- [ ] T093 檢查 repo：沒有機敏資料、`.env`、憑證 JSON 或本機檔案被追蹤（`git status`、`git ls-files`），`pyproject.toml` 沒有新增套件（憲章原則 V、VII）
- [ ] T094 真實路徑驗證（涉及 Google 的子功能，憲章原則 VI）：用**兩份版面不同**的真實 Google 試算表各完成一次「匯入 → 搶答 → 定案 → 預覽 → 確認寫回 → 重新核對／重試 → 下載 CSV」，並執行 T083；**逐項確認並記錄 research R17 的五項假設**（`drive.file` 是否足以寫入、重新授權後是否仍能存取原檔、單引號開頭／公式字樣／前導零／類日期／換行的讀回、合併格只寫左上角、受保護範圍的狀態碼）；任何一項不成立就回報並調整 plan 的設計，不得以 mock 結果宣稱完成；憑證只放本機（SC-009）
- [ ] T095 非實作者依 [quickstart.md](quickstart.md) C 節 13 步在多個瀏覽器分頁（老師＋至少兩組學生）以真實後端完整驗證一次，記錄日期、操作、結果數字與試算表版面差異於 `verification.md`「人工驗證」（SC-009、憲章原則 VI）；沒有實際執行不得勾選

---

## FR／SC 對照

| 需求 | 任務 |
|---|---|
| FR-001 老師限定、已取消拒絕 | T021、T022、T026、T029 |
| FR-002、FR-003、FR-006 預覽、範圍、無成果 | T019、T021、T025～T027 |
| FR-004、FR-005 手動、快照綁定 | T020、T022、T028 |
| FR-007～FR-009 結構檢查 | T031、T032、T036～T038 |
| FR-010 授權失敗與重新授權 | T033、T034、T039～T041、T094 |
| FR-011～FR-014 精確寫入 | T042～T048 |
| FR-015～FR-019 狀態、核對、重試、冪等 | T049～T053、T057～T060 |
| FR-020 一次一個寫入 | T054、T059 |
| FR-021 狀態推送 | T055、T061、T063、T082 |
| FR-022～FR-026 CSV 內容 | T064～T070 |
| FR-027～FR-030 CSV 格式與文字安全 | T072～T077 |
| FR-031～FR-034 輸入驗證、純文字、日誌、記憶體 | T007、T079、T080、T081、T092 |
| SC-001 Scenario 測試 | T078 |
| SC-002、SC-003 兩份版面、結構檢查 | T031、T032、T044 |
| SC-004、SC-005 狀態與冪等 | T049～T053 |
| SC-006 陳舊快照、無成果、取消 | T021、T022 |
| SC-007 CSV 嚴格解析 | T072～T074 |
| SC-008 效能與 2 秒 | T082、T089 |
| SC-009 真實路徑與人工驗證 | T083、T094、T095 |

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：無相依，可立即開始（T003、T004、T005 可平行）
- **Foundational (Phase 2)**：依賴 Setup；**阻塞所有 User Story**
- **US1 → US2 → US3**：US2 在 US1 的 `preview`／`confirm_write` 加入結構檢查與授權處理；US3 的真實寫入器與逐字寫入建立在 US1 的確認流程之上。三者合起來是寫回的 MVP
- **US4（狀態、核對、重試）** 依賴 US1～US3 的 `confirm_write`；寫入器的回應分類（T058）修改 US3 建立的 `sheets_writer.py`
- **US5（CSV 內容）** 只依賴 Foundational，可在 US1～US4 之外獨立進行；**US6（CSV 格式與安全）** 依賴 US5 的 `build_rows`
- **Polish (Phase 9)**：依賴所有 User Story；T094、T095 需要兩份真實試算表與老師帳號，請提早安排

### Within Each User Story

- 測試先寫並確認失敗（失敗數記入 `verification.md`），再寫實作
- 核心（`<core>`）→ 服務層（`<app>`）→ 外層（`<google>`、`<web>`、`<static>`）
- 每個 Story 結束時（Checkpoint 前）執行 `ruff check .`、`ruff format --check .`、`mypy` 與全部測試，三者都通過再勾選、commit（憲章技術限制 2；T087 是最後的總檢查）

### Parallel Opportunities

- Setup：T003、T004、T005
- Foundational 測試：T006～T010；實作 T012、T013、T014 可平行（不同檔案）
- US1 測試 T019～T023 可平行；US2 測試 T031～T035；US3 測試 T042～T045；US4 測試 T049～T056；US5 測試 T064～T066；US6 測試 T072～T075
- **US5／US6 可與 US1～US4 由不同的人平行進行**（只共用 Foundational 的型別與 `<app>/service.py` 的 `download_csv` 方法）
- Polish：T078～T083、T089

---

## Parallel Example: User Story 4

```text
# 同時寫 US4 的測試：
Task: "T049 tests/unit/adapters/google/test_sheets_writer_outcomes.py"
Task: "T050 tests/unit/core/result_export/test_reconcile.py"
Task: "T051 tests/unit/app/result_export/test_pending_and_recheck.py"
Task: "T052 tests/unit/app/result_export/test_retry_idempotent.py"
Task: "T053 tests/unit/app/result_export/test_read_only_for_activity.py"
Task: "T054 tests/unit/app/result_export/test_in_progress.py"
Task: "T055 tests/unit/app/result_export/test_status_push.py"
Task: "T056 tests/contract/result_export/test_http_attempts.py"
```

## Parallel Example: Foundational

```text
Task: "T006 tests/unit/core/result_export/test_models.py"
Task: "T007 tests/unit/app/result_export/test_messages.py"
Task: "T008 tests/unit/app/result_export/test_store.py"
Task: "T009 tests/unit/app/result_export/test_extension_registration.py"
Task: "T010 tests/contract/result_export/test_wiring.py"
```

---

## Implementation Strategy

### MVP First（US1 → US2 → US3）

1. Phase 1 Setup → Phase 2 Foundational（既有測試全過）
2. Phase 3 US1：能預覽並手動確認，沒有成果、陳舊快照、取消、非老師都不寫入
3. Phase 4 US2：結構不符與授權失敗零寫入，任何階段可重新授權
4. Phase 5 US3：兩份版面精確寫入，其他內容完全保留
5. **停下驗證**：用 `FakeSheetsWriter` 與 `HttpMockSequence` 驗證完整寫回；再安排 T094 的真實驗證**盡早進行**，因為 R17 的五項假設若不成立（例如 `drive.file` 不足以寫入），要在其他 Story 完成前就調整設計

### Incremental Delivery

1. US1～US3：可靠寫回（MVP）
2. US4：誠實的狀態、核對與重試
3. US5～US6：完整 CSV 與文字安全（可由另一人平行）
4. Polish：SCENARIO_MAP、效能、圖表一致性、真實與人工驗證

### 時程提醒

內部凍結點 2026-11-29 晚上；繳交期限 2026-11-30 00:00。T094（兩份真實試算表）與 T095（非實作者人工驗證）需要排程與另一位組員，請在 US3 完成後立刻安排，不要留到最後。R17 的假設若失敗，修正的時間最長。

---

## Notes

- [P] = 不同檔案且沒有未完成的相依
- 每個 User Story 完成後勾選、commit（`feat:`／`test:`）、push
- **不得**修改 001～004 的程式與既有測試斷言；`main.py`、`teacher.html`、`app.css`、`tests/conftest.py`、`tests/SCENARIO_MAP.md`、`pyproject.toml`（本子功能不需要）只追加
- 寫入一律用 `sheetId` 與列欄索引、`stringValue`、`fields="userEnteredValue"`，**不得**使用 `valueInputOption` 或工作表名稱組 A1 範圍（憲章原則 III；research R3）
- 核對（`recheck`）**不做結構檢查**（clarify Q2、research R7）；寫入與重試**一律**先做結構檢查（FR-007）
- 保護前綴只存在於 CSV 的組別與答案欄；任何寫入 Google 的答案、003 的原始提交、004 的結果都不得出現（FR-013、FR-029）
- 自動化測試**不得呼叫真實 Google**；真實路徑只在 `real_google` 標記的測試與人工驗證，缺環境變數要明確失敗（全域規則）
- 驗證結果一律寫在 `specs/005-result-export/verification.md`，要有日期、指令與結果數字，沒有實際執行不得勾選
