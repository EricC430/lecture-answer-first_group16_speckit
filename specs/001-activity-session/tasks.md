---

description: "001-activity-session 任務清單"
---

# Tasks: 活動建立、組別加入與階段同步

**Input**: Design documents from `/specs/001-activity-session/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（專案覆寫，憲章原則 VI）。

- spec 共有 44 個 Acceptance Scenario，每一個至少對應一個自動化測試；測試的 docstring 第一行寫 `Scenario: USn-ASm`。
- 測試先寫，並確認在實作前是失敗的。
- 本子功能不使用 Google，不需要 mock，也不需要真實路徑驗證。

**Diagrams**: REQUIRED（原則 II）。實作前先確認 `diagrams/001-activity-session-*.puml` 與 PNG 存在（T004）；實作後有一致性驗證任務（T082）。

**Architecture**: REQUIRED（技術限制 4，NON-NEGOTIABLE）。每個 Phase 的實作任務分三組，依序列出，相依方向為「轉接層 → 服務層 → 核心」：

- **核心**：`src/lecture_quiz/core/activity/`，只能是純函式。
- **服務層**：`src/lecture_quiz/app/activity/`。
- **轉接層**：`src/lecture_quiz/adapters/`。

**⚠ 提案相依**：標示的任務受 `docs/alignment.md` 2026-11-21 尚待確認的提案影響（Q-04、Q-06、Q-08、Q-09／Q-33、離開本組、刪除空組）。組內開會或 OpenSpec 組回覆後，依 [plan.md](plan.md)「受待確認提案影響的設計點」調整；這些任務在對方確認前不得合併。

**Organization**: 依 User Story 分組。P1 依 US1 → US2 → US3 → US4 → US6 的順序（後面的故事需要前面的狀態），接著是 P2 的 US5、US7。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立專案骨架、相依套件與品質工具

- [ ] T001 建立 `pyproject.toml`：
  - 套件名 `lecture-quiz`，src 佈局 `src/lecture_quiz`，`requires-python = ">=3.11"`。
  - 執行相依：`fastapi`、`uvicorn[standard]`。
  - `[project.optional-dependencies].dev`：`pytest`、`pytest-timeout`、`httpx`、`websockets`、`ruff`、`mypy`。
  - `[tool.pytest.ini_options]`：`testpaths = ["tests"]`，註冊 marker `perf`，`addopts = "-m 'not perf'"`，`timeout = 30`。
- [ ] T002 在 `pyproject.toml` 設定 Ruff 與 mypy（憲章 v1.0.1 技術限制 2）：
  - `[tool.ruff.lint] select = ["E","F","W","I","N","UP","B","D","ANN"]`，`pydocstyle.convention = "google"`，`per-file-ignores` 讓 `tests/**` 排除 `D`、`ANN`。
  - `[tool.ruff] target-version = "py311"`。
  - `[tool.mypy] files = ["src"]`，`disallow_untyped_defs = true`，`python_version = "3.11"`。
- [ ] T003 [P] 建立套件與測試目錄，各放空的 `__init__.py`：
  - 套件：`src/lecture_quiz/`、`src/lecture_quiz/core/`、`src/lecture_quiz/core/activity/`、`src/lecture_quiz/app/`、`src/lecture_quiz/app/activity/`、`src/lecture_quiz/adapters/`、`src/lecture_quiz/adapters/web/`。
  - 測試目錄：`tests/unit/core/`、`tests/unit/app/`、`tests/architecture/`、`tests/contract/`、`tests/integration/`、`tests/perf/`。
- [ ] T004 [P] 確認 `diagrams/001-activity-session-{component,class,sequence}.puml` 與對應 PNG 都存在，且 PNG 比 `.puml` 新；不符合時，先執行 `java -jar plantuml.jar "./diagrams/*.puml"`（原則 II）。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有 User Story 共用的資料型別、服務骨架、HTTP／WebSocket 基礎與前端共用模組

**⚠️ CRITICAL**: 本階段完成前不得開始任何 User Story

### 測試基礎

- [ ] T005 建立 `tests/conftest.py`，內容包括：
  - `FakeClock`：`now()` 回傳可手動 `advance(seconds)` 的有時區 `datetime`，起點 `2026-11-21T09:00:00+08:00`。
  - `ManualScheduler`：記錄 `schedule(code, deadline)`，`fire(code)` 時以 `deadline` 呼叫回呼。
  - `make_app(clock, scheduler, dev_seed=False)` 工廠。
  - fixture：`client`（`TestClient`）、`teacher`（建立活動並回傳 code、token 的 helper）。
- [ ] T006 [P] 建立 `tests/architecture/test_core_is_pure.py`，用 `ast` 掃描 `src/lecture_quiz/core/**/*.py`：
  - 匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`lecture_quiz.app`、`lecture_quiz.adapters` 時失敗。
  - 呼叫 `datetime.now`、`datetime.utcnow`、`date.today` 時失敗。
  - 依據：研究 R4、技術限制 4。

### 核心（純函式）

- [ ] T007 [P] 在 `src/lecture_quiz/core/activity/models.py` 建立 frozen dataclass，欄位與規則照 [data-model.md](data-model.md) 原文：
  - `Stage`（`PREPARING`、`ROUND_OPEN`、`RESULT_PENDING`、`RESULT_FINAL`、`ENDED`、`CANCELLED`；`is_terminal` 屬性）。
  - `TeacherIdentity(token_hash)`、`Group(name, join_credential, success_count, has_submissions)`、`DeviceIdentity(token_hash, group_name)`。
  - `RoundRules(question_numbers, fair_mode, countdown_seconds, deadline)`。
  - `Round(number, rules, opened_at, baseline, closed, closed_at, close_cause)`。
  - `Activity(code, stage, version, changed_at, teacher, question_numbers, solved_questions, groups, devices, rounds)`，含 `current_round`、`unsolved_questions` 衍生屬性。
  - 集合欄位一律使用 `tuple`、`frozenset`、`MappingProxyType`。
  - 每個公開類別都有 Google 風格 docstring。
- [ ] T008 [P] 在 `src/lecture_quiz/core/activity/commands.py` 建立：
  - Actor 型別：`Teacher(token_hash)`、`Device(token_hash)`、`System`、`Anonymous`。
  - Command 型別：`CreateActivity`、`JoinGroup(name_raw, credential_raw)`、`LeaveGroup`、`DeleteGroup(name)`、`OpenRound(question_numbers, fair_mode, countdown_raw)`、`CloseRound`、`Finalize(outcome)`、`EndActivity`、`CancelActivity`、`ReplaceQuestions(question_numbers)`、`MarkGroupSubmitted(group_name)`。
  - `FinalizeOutcome(solved_questions: frozenset[int], success_increments: Mapping[str, int])`。
- [ ] T009 [P] 在 `src/lecture_quiz/core/activity/results.py` 建立：
  - `RejectionReason` 列舉，11 個值，每個值附 HTTP 狀態碼與 [data-model.md](data-model.md) 表中的中文訊息；`STAGE_NOT_ALLOWED` 的訊息由「階段 × 操作」產生。
  - `IssuedSecrets(group_credential, device_token_hash)`，由服務層傳入。
  - `Transition(ok, activity, changed, rejection, issued)`。
- [ ] T010 在 `src/lecture_quiz/core/activity/state_machine.py` 建立 `ActivityStateMachine.apply(activity, command, now, issued=None) -> Transition` 的分派骨架：
  - 依序檢查：活動已終止、老師權限、「階段 × 操作」相容表。表格照 spec「活動階段狀態機」與「不改變階段的組別操作」兩張表。
  - 尚未實作的操作回傳 `STAGE_NOT_ALLOWED`。
  - 成功且 `changed` 時，`version + 1`，`changed_at = now`。
- [ ] T011 [P] 在 `src/lecture_quiz/core/activity/snapshot_view.py` 建立 `ActivitySnapshot` 與 `SnapshotView.for_teacher`、`SnapshotView.for_group` 的共同欄位：`code`、`version`、`changedAt`、`stage`、`roundNumber`、`openQuestions`、`deadline`、`fairMode`、`unsolvedQuestions`，格式照 [contracts/sync-websocket.md](contracts/sync-websocket.md)。

### 服務層

- [ ] T012 [P] 在 `src/lecture_quiz/app/activity/ports.py` 定義：
  - Protocol：`Clock`、`CountdownScheduler(schedule, cancel)`、`SyncPublisher(publish)`、`ActivityGateway`（`stage`、`is_teacher`、`replace_questions`，都有 `code` 參數）。
  - 型別：`Requester`、`Outcome[T]`。
  - 依據：[contracts/service-interfaces.md](contracts/service-interfaces.md)。
- [ ] T013 [P] 在 `src/lecture_quiz/app/activity/secrets_gen.py` 實作：
  - `new_code(existing)` 與 `new_credential()`：6 碼，字元集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`，用 `secrets.choice`；活動代碼不與 `existing` 重複。
  - `new_token()`：`secrets.token_urlsafe(32)`。
  - `hash_token()`：SHA-256。
  - `tokens_match()`：`secrets.compare_digest`。
  - `normalize_code_input()`：去除首尾空白並轉成大寫。
- [ ] T014 在 `src/lecture_quiz/app/activity/registry.py` 實作 `ActivityRegistry`：
  - 存放：`code → Activity`、每個活動一把 `asyncio.Lock`、活動內的「(身分雜湊, Idempotency-Key) → 原回應」（每個活動最多 1000 筆，超過時淘汰最舊的）、全域的「建立活動 key → (code, teacher token)」。
  - 只存在記憶體（原則 VII）。
- [ ] T015 在 `src/lecture_quiz/app/activity/service.py` 建立 `ActivityService._execute(code, requester, command, idempotency_key)`，流程照研究 R6：
  1. 查詢去重表。
  2. 取得鎖。
  3. 呼叫 `ActivityStateMachine.apply(..., now=clock.now())`。
  4. 成功時替換 `Activity`。
  5. 釋放鎖。
  6. `changed` 時呼叫 `SyncPublisher.publish`。
  7. 記錄去重結果。
  - 另外實作 `resolve_requester(code, bearer_token)`，把 token 轉成 `Teacher`、`Device` 或 `Anonymous`。
- [ ] T016 [P] 在 `tests/unit/app/test_secrets_registry.py` 測試：代碼字元集與長度、不與既有代碼重複、`compare_digest` 比對、去重表上限 1000 筆與淘汰順序。

### 轉接層

- [ ] T017 [P] 在 `src/lecture_quiz/adapters/clock.py` 實作 `SystemClock.now()`，回傳有時區的現在時間。
- [ ] T018 [P] 在 `src/lecture_quiz/adapters/countdown.py` 實作 `AsyncioCountdownScheduler`：`schedule(code, deadline)` 建立 asyncio 任務，到期時呼叫回呼；`cancel(code)` 取消任務。
- [ ] T019 在 `src/lecture_quiz/adapters/web/http_api.py` 建立 APIRouter `/api` 的共用基礎：
  - 解析 `Authorization: Bearer` 與 `Idempotency-Key`。
  - `RejectionReason` 轉成 HTTP 狀態碼與 `{"error": {"code", "message"}}`；請求驗證錯誤統一成 `INVALID_REQUEST`，訊息指出欄位。
  - 全域例外處理器：未預期的錯誤回 500 與通用訊息，不含堆疊追蹤。
  - 請求 log 中介層：每個請求一行 `INFO`，只記錄方法、路徑樣板、活動代碼、結果代碼、`version`、耗時。
  - 依據：[contracts/http-api.md](contracts/http-api.md)、技術限制 3。
- [ ] T020 在 `src/lecture_quiz/adapters/web/ws_sync.py` 實作 `WebSocketHub`（`SyncPublisher` 的實作）：
  - 路徑 `/ws/activities/{code}`。
  - 第一則訊息必須是 `auth`，5 秒內沒收到就關閉連線。
  - 每 10 秒送一次 `ping`。
  - 活動不存在時送 `gone` 並以 4410 關閉；token 無效時送 `unauthorized`（附 `reason`）並以 4401 關閉。
  - 每條連線依角色以 `SnapshotView` 裁切後推送；單一連線送出失敗時只關閉該連線。
  - 依據：[contracts/sync-websocket.md](contracts/sync-websocket.md)。
- [ ] T021 在 `src/lecture_quiz/main.py` 建立 `create_app(clock, scheduler, dev_seed)` 與模組層級的 `app`：
  - `logging.basicConfig(level=logging.INFO, stream=sys.stdout)`。
  - 掛載 HTTP router、WebSocket 與靜態檔 `adapters/static`。
  - 從環境變數 `LECTURE_QUIZ_DEV_SEED` 讀取 `dev_seed`。
  - 在 docstring 註明啟動方式為 `uvicorn lecture_quiz.main:app --host 127.0.0.1`。
- [ ] T022 [P] 建立前端共用模組，都放在 `src/lecture_quiz/adapters/static/`：
  - `css/app.css`：狀態列與「同步中斷」橫幅樣式。
  - `js/api.js`：fetch 包裝，自動帶 `Authorization` 與每次操作的 `Idempotency-Key`（UUID），重試時沿用同一個 key；錯誤時顯示 `error.message`。
  - `js/identity.js`：老師 token 存在 `localStorage["teacher:{code}"]`，裝置 token 存在 `sessionStorage["device:{code}"]`（⚠ 提案相依 Q-04）。
  - `js/sync.js`：
    - 先送 `auth`。
    - 重連依序等 0.5、1、2、4 秒，之後每次 4 秒。
    - 超過 25 秒沒收到訊息，視為中斷。
    - 丟棄版本較舊的快照。
    - `gone` 時清除身分並顯示「活動已失效，請重新建立或加入活動」。
    - 斷線期間顯示「同步中斷，正在重新連線」。
    - 右下角顯示 `v{version}` 與延遲（畫面更新完成的時間 − `changedAt`）。
  - 所有不可信文字都用 `textContent` 輸出（原則 V）。

**Checkpoint**: 基礎完成，可以開始 User Story

---

## Phase 3: User Story 1 - 老師建立活動並獨占控制權 (Priority: P1) 🎯 MVP

**Goal**: 老師建立活動、取得 6 碼代碼，只有該老師（同一瀏覽器的各分頁）能控制活動

**Independent Test**: 建立兩個活動，確認代碼不同、都在準備中；以學生身分、其他活動的老師身分、沒有身分的請求，分別呼叫 10 種老師專用操作，全部被拒絕且狀態不變

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T023 [P] [US1] 在 `tests/unit/core/test_state_machine_create_and_permissions.py` 測試：
  - `Scenario: US1-AS1`：`CreateActivity` 後為 `PREPARING`、`version == 1`、沒有題目也沒有輪次。
  - `Scenario: US1-AS4, US1-AS5, US1-AS6`：`Device`、別的活動的 `Teacher`、`Anonymous` 對 10 種老師專用操作（開輪、關輪、判錯與撤銷判錯的預留入口、定案、結束、取消、匯入、匯出、刪除組別）都回傳 `NOT_TEACHER`，且 `activity` 完全不變（SC-002）。
- [ ] T024 [P] [US1] 在 `tests/contract/test_http_activities.py` 測試契約：
  - `POST /api/activities` 回 `201 {"code", "teacherToken", "version"}`。
  - 代碼不存在時回 404 與 `error.code`、`error.message`。
  - 錯誤回應不含 `Traceback`、檔案路徑或 token。
- [ ] T025 [P] [US1] 在 `tests/integration/test_us1_teacher.py` 測試：
  - `Scenario: US1-AS1`：已有一個活動時再建立一個，兩個代碼都是 6 碼，字元都在字元集內，而且互不相同。
  - `Scenario: US1-AS2` ⚠ 提案相依 Q-04：用同一個 token 建立新的 client（模擬重新整理或新分頁），仍可取得老師快照並操作。
  - `Scenario: US1-AS3` ⚠ 提案相依 Q-04：沒有 token 的 client 操作時回 403 `NOT_TEACHER`。
  - `Scenario: US1-AS4`：學生裝置 token 操作時回 403，回應中不含任何 credential 或 token。
  - `Scenario: US1-AS5`：活動 B 的老師 token 操作活動 A 時回 403，A 的 `version` 不變。
  - `Scenario: US1-AS6`：只帶活動代碼、不帶 token 時回 403，訊息為「需要這個活動的老師身分才能操作。」

### Implementation for User Story 1

- [ ] T026 [US1] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `CreateActivity`（產生 `PREPARING` 的 `Activity`；代碼與 `teacher.token_hash` 由 `issued` 傳入），以及老師權限檢查（`actor` 是 `Teacher` 且 `token_hash` 相同）。
- [ ] T027 [US1] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `create(idempotency_key)`：產生代碼與 token；同一個 key 回傳同一組結果。
  - `stage(code)`、`is_teacher(code, requester)`（`ActivityGateway`）。
  - `snapshot(code, requester)`。
- [ ] T028 [US1] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities` 與 `GET /activities/{code}/snapshot`。snapshot 在活動不存在時：帶 token 回 410 `ACTIVITY_GONE`，不帶 token 回 404。
- [ ] T029 [US1] **轉接層**：建立 `src/lecture_quiz/adapters/static/teacher.html` 與 `js/teacher.js`：
  - 「建立活動」按鈕，建立後顯示代碼，token 存到 `identity.js`（⚠ 提案相依 Q-04）。
  - 網址帶 `?code=` 時，從 `localStorage` 取 token 並連線同步；沒有 token 時顯示「需要該活動的老師身分」。

**Checkpoint**: US1 可以獨立測試

---

## Phase 4: User Story 2 - 學生以組別加入，多裝置同組並可恢復身分 (Priority: P1)

**Goal**: 學生用代碼加組名加入；既有組要附上憑證；本組裝置看得到憑證；重新整理後恢復身分

**Independent Test**: 兩個 client 加入同一組（第二個附憑證），第三個加入另一組；確認同組身分與憑證一致、他組看不到；再測錯誤代碼、空白組名、錯誤憑證、重新整理與中途加入

### Tests for User Story 2 (REQUIRED) ⚠️

- [ ] T030 [P] [US2] 在 `tests/unit/core/test_input_rules_group_name.py` 測試 `normalize_group_name`：
  - `" 第一組 "` 會變成 `"第一組"`。
  - 空字串與純空白（含全形空白 `"　"`）回傳 `INVALID_GROUP_NAME`。
  - 含 `\n`、`\t` 等 Unicode `Cc` 類別字元時回傳 `INVALID_GROUP_NAME`。
  - 長度 500 的組名可以接受（不設長度上限，Q-07）。
  - `"ABC"` 與 `"abc"` 視為不同組名。
- [ ] T031 [P] [US2] 在 `tests/unit/core/test_state_machine_join.py` 測試：
  - `Scenario: US2-AS1`：新組名建立 `Group`，並為該裝置建立 `DeviceIdentity`。
  - `Scenario: US2-AS2`：既有組名加上正確憑證時，新增裝置，不新增組。
  - `Scenario: US2-AS4`：既有組名不附憑證或憑證錯誤時，回傳 `BAD_CREDENTIAL`，`activity` 不變。
  - `Scenario: US2-AS5`：空白組名、含控制字元的組名被拒，`activity` 不變。
  - `Scenario: US2-AS6`：`ENDED`、`CANCELLED` 時拒絕加入，訊息依階段寫成「活動已結束／已取消」。
  - `Scenario: US2-AS7`：在 `ROUND_OPEN` 加入新組，`success_count == 0`，`stage` 不變。
- [ ] T032 [P] [US2] 在 `tests/unit/core/test_snapshot_view_groups.py` 測試：
  - `Scenario: US2-AS3` ⚠ 提案相依 Q-06：`for_group` 只含 `ownGroup`（名稱、憑證、成功次數）；`for_teacher` 的 `groups` 含每一組的憑證。
  - FR-030：`for_group` 的序列化 JSON 不含任何其他組的名稱、憑證，也不含組數。
- [ ] T033 [P] [US2] 在 `tests/contract/test_http_join.py` 測試契約：
  - `POST /groups/join` 回 `200 {"deviceToken", "groupName", "credential", "version"}`。
  - 代碼輸入 `" k7qh2m "` 視為 `K7QH2M`。
  - 已帶有效裝置 token 再加入時，回 409「請先離開本組」。
- [ ] T034 [P] [US2] 在 `tests/integration/test_us2_join.py` 以 HTTP 加 WebSocket 測試 `Scenario: US2-AS1`～`US2-AS8`：
  - AS2：兩個裝置的快照中，`ownGroup` 相同。
  - AS3 ⚠ Q-06：其他組的快照中沒有第一組的憑證。
  - AS4：錯誤訊息含「向同組同學查看本組加入憑證」，而且不含憑證本身。
  - AS8：用同一個裝置 token 重新連 WebSocket，取得原組別。

### Implementation for User Story 2

- [ ] T035 [P] [US2] **核心**：在 `src/lecture_quiz/core/activity/input_rules.py` 實作 `InputRules.normalize_group_name`（去除首尾空白、不可為空、不可含 `unicodedata.category == "Cc"` 的字元、不設長度上限）。
- [ ] T036 [US2] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `JoinGroup`：
  - 允許的階段：非終止階段。
  - 新組名：使用 `issued.group_credential`。
  - 既有組名：用 `hmac.compare_digest` 比對憑證。
  - 新增 `DeviceIdentity`，`token_hash` 來自 `issued`。
- [ ] T037 [US2] **核心**：在 `src/lecture_quiz/core/activity/snapshot_view.py` 補上 `for_group` 的 `ownGroup`（含憑證）與 `for_teacher` 的 `groups`（`name`、`credential`、`successCount`、`hasSubmissions`、`deviceCount`）及 `questionNumbers`（⚠ 提案相依 Q-06）。
- [ ] T038 [US2] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `join(code, name_raw, credential_raw, requester, idempotency_key)`：產生憑證與裝置 token，回傳原始 token 一次。
  - `resolve_device(code, device_token)`：給 003 使用。
- [ ] T039 [US2] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/groups/join`，讓 `GET snapshot` 支援裝置 token；`ws_sync.py` 的學生連線改用 `for_group` 裁切。
- [ ] T040 [US2] **轉接層**：建立 `src/lecture_quiz/adapters/static/student.html` 與 `js/student.js`：
  - 加入表單：代碼、組名、選填的憑證。
  - 成功後把裝置 token 存到 `sessionStorage`，並常駐顯示「本組加入憑證」（⚠ 提案相依 Q-06）。
  - 重新整理時自動恢復身分。

**Checkpoint**: US1 與 US2 都能獨立運作

---

## Phase 5: User Story 3 - 老師依條件開輪並固定本輪規則 (Priority: P1)

**Goal**: 已有題目時才能開輪；預設全選未成功題；公平模式預設關閉；倒數 1～3600 秒；規則在開輪時固定

**Independent Test**: 放入 4 題後，分別測試合法開輪、零題、選了已成功題、未定案就開輪、輪中修改規則、倒數超出範圍

### Tests for User Story 3 (REQUIRED) ⚠️

- [ ] T041 [P] [US3] 在 `tests/unit/core/test_input_rules_round.py` 測試：
  - `Scenario: US3-AS6` ⚠ 提案相依 Q-08：`validate_countdown` 接受 `None`、`1`、`3600`；拒絕 `0`、`-1`、`3601`、`2.5`、`"10"`、`""`、`True`，回傳 `INVALID_COUNTDOWN`，訊息為「倒數秒數須為 1～3600 的整數。」
  - `validate_selection` 拒絕空清單、重複題號、不存在的題號、已成功的題號，回傳 `INVALID_SELECTION`。
- [ ] T042 [P] [US3] 在 `tests/unit/core/test_state_machine_open_round.py` 測試：
  - `Scenario: US3-AS1`：`question_numbers=None` 時選取全部未成功題，`fair_mode` 預設為 `False`，`deadline` 為 `None`。
  - `Scenario: US3-AS2`：選 2 題，建立 `Round(number=1)`，`baseline` 等於各組 `success_count`，`stage == ROUND_OPEN`。
  - `Scenario: US3-AS3`：沒有題目時回傳 `NO_QUESTIONS`。
  - `Scenario: US3-AS4`：零題、已成功題、在 `RESULT_PENDING` 時開輪，全部被拒。
  - `Scenario: US3-AS5`：在 `ROUND_OPEN` 再送 `OpenRound` 時回傳 `RULES_LOCKED`，規則不變。
  - 倒數 60 秒時，`deadline == opened_at + 60s`。
- [ ] T043 [P] [US3] 在 `tests/unit/core/test_replace_questions.py` 測試：
  - `ReplaceQuestions` 只允許老師在 `PREPARING` 時呼叫，成功時整份取代題號。
  - 被拒時（例如在 `ROUND_OPEN`），既有題號完全不變（原則 III）。
- [ ] T044 [P] [US3] 在 `tests/contract/test_http_rounds.py` 測試契約：
  - `POST /rounds` 回 `201 {"roundNumber", "deadline", "version"}`。
  - `countdownSeconds: 2.5` 回 400 `INVALID_COUNTDOWN`。
- [ ] T045 [P] [US3] 在 `tests/integration/test_us3_open_round.py` 以 HTTP 加 `ManualScheduler` 測試 `Scenario: US3-AS1`～`US3-AS7`：
  - AS2：所有 WebSocket 連線都收到 `stage == "ROUND_OPEN"`。
  - AS7：同一個 `Idempotency-Key` 重送開輪，只產生一個輪次，回應相同（SC-004）。

### Implementation for User Story 3

- [ ] T046 [P] [US3] **核心**：在 `src/lecture_quiz/core/activity/input_rules.py` 實作：
  - `validate_countdown(raw)`：`None` 或 1～3600 的 `int`，排除 `bool`（⚠ 提案相依 Q-08）。
  - `validate_selection(selected, imported, solved)`：`selected` 為 `None` 時回傳全部未成功題；其餘照 T041 的規則。
- [ ] T047 [US3] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作：
  - `OpenRound`：允許 `PREPARING`（必須有題目）與 `RESULT_FINAL`；建立 `RoundRules` 與 `Round`，`deadline = now + countdown_seconds`。
  - `ReplaceQuestions`：只允許 `PREPARING`。
- [ ] T048 [US3] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `open_round(...)`：成功且有 `deadline` 時，呼叫 `scheduler.schedule(code, deadline)`。
  - `replace_questions(code, requester, question_numbers)`（`ActivityGateway`）。
  - `current_round(code)`：給 004 使用。
- [ ] T049 [US3] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/rounds`。
- [ ] T050 [US3] **轉接層**：建立 `src/lecture_quiz/adapters/web/dev_seed.py`：
  - 端點 `POST /api/dev/activities/{code}/seed-questions`，只在 `dev_seed=True` 時掛載，只限老師，呼叫 `replace_questions(1..count)`。
  - 在 `tests/integration/test_dev_seed.py` 測試：預設不存在（404）、啟用後學生呼叫時回 403。
  - 依據：研究 R8、Complexity Tracking。
- [ ] T051 [US3] **轉接層**：在 `src/lecture_quiz/adapters/static/teacher.html` 與 `js/teacher.js` 加入：
  - 開輪面板：題目核取方塊預設全選未成功題、公平模式預設關閉、倒數輸入選填（⚠ 提案相依 Q-08）。
  - 「放入假題目」按鈕：只在 seed 端點存在時顯示。

**Checkpoint**: US1～US3 可以獨立運作

---

## Phase 6: User Story 4 - 關輪只發生一次，並先定案才能往下走 (Priority: P1)

**Goal**: 手動關輪或倒數截止都只關一次；必須由老師定案後才能開下一輪或結束

**Independent Test**: 同時送出手動關輪與倒數截止 50 次，每次都只有 1 份結果；未定案時開輪與結束都被拒

### Tests for User Story 4 (REQUIRED) ⚠️

- [ ] T052 [P] [US4] 在 `tests/unit/core/test_state_machine_close_finalize.py` 測試：
  - `Scenario: US4-AS1`：`CloseRound(Teacher)` 後為 `RESULT_PENDING`，`closed=True`，`close_cause="teacher"`。
  - `Scenario: US4-AS2`：`CloseRound(System)` 在 `now >= deadline` 時生效；`now < deadline` 時回傳成功但 `changed=False`。
  - `Scenario: US4-AS3`：已關輪後再收到 `CloseRound`，`changed=False`，`version` 不變。
  - `Scenario: US4-AS4`：`RESULT_PENDING` 不會自行轉移。
  - `Scenario: US4-AS5`：在 `RESULT_PENDING` 開輪時回傳 `STAGE_NOT_ALLOWED`。
  - `Scenario: US4-AS6`：`Finalize(outcome)` 後為 `RESULT_FINAL`，`solved_questions` 與 `success_count` 依 `outcome` 更新；再開輪時 `number=2`，只能選未成功題。
  - `is_deadline_passed` 的邊界：截止前 1 微秒為 `False`、剛好截止時為 `True`。
- [ ] T053 [P] [US4] 在 `tests/unit/app/test_concurrent_close.py` 測試 SC-003：
  - 用 `asyncio.gather(service.close_round(teacher), scheduler.fire(code))`，重複 50 次，每次都新建活動。
  - 每次只有一個呼叫產生變更，`version` 只加 1，`SyncPublisher` 只被呼叫一次。
- [ ] T054 [P] [US4] 在 `tests/contract/test_http_close_finalize.py` 測試契約：
  - `POST /rounds/current/close` 回 `{"roundNumber", "version", "alreadyClosed"}`，第二次呼叫 `alreadyClosed == true`，而且 `version` 不變。
  - `POST /rounds/current/finalize` 回 `{"version"}`。
- [ ] T055 [P] [US4] 在 `tests/integration/test_us4_close_finalize.py` 以 HTTP、WebSocket、`FakeClock`、`ManualScheduler` 測試 `Scenario: US4-AS1`～`US4-AS6`。

### Implementation for User Story 4

- [ ] T056 [US4] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作：
  - `CloseRound`：`Teacher` 與 `System` 都可以；`System` 只有在 `now >= deadline` 時才生效；已關輪時 `changed=False`。
  - `Finalize(outcome)`：`outcome` 的題號必須是本輪所選題目的子集，否則拒絕。
  - `is_deadline_passed(round, now)`。
- [ ] T057 [US4] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `close_round(code, requester)`：成功時呼叫 `scheduler.cancel(code)`。
  - `finalize(code, requester, outcome=FinalizeOutcome(frozenset(), {}))`。
  - 給 003 的 `accepts_submission(code, now)`。
  - 倒數回呼：`close_round(System)`。
- [ ] T058 [US4] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /rounds/current/close`（含 `alreadyClosed`）與 `POST /rounds/current/finalize`；在 `main.py` 把 `AsyncioCountdownScheduler` 的回呼接到服務層。
- [ ] T059 [US4] **轉接層**：在 `teacher.html`、`teacher.js`、`student.html`、`student.js` 加入「關輪」「確認定案」按鈕，以及兩邊的倒數剩餘秒數（依 `deadline` 計算）。

**Checkpoint**: 搶答主流程（建立 → 加入 → 開輪 → 關輪 → 定案）可以運作

---

## Phase 7: User Story 6 - 所有畫面兩秒內同步，斷線與重啟有明確提示 (Priority: P1)

**Goal**: 狀態變更在 2 秒內推送到所有頁面；斷線時顯示中斷；重連後取得完整快照；重啟後提示活動失效

**Independent Test**: 老師加 2 組連線，關輪後都收到相同版本；斷線重連取得最新快照；建立新的 app 實例（模擬重啟）後，舊 token 收到 `gone`

### Tests for User Story 6 (REQUIRED) ⚠️

- [ ] T060 [P] [US6] 在 `tests/contract/test_ws_sync.py` 測試契約：
  - 第一則訊息不是 `auth`，或 5 秒內沒送，會被關閉。
  - 老師版與學生版的 `snapshot` 欄位符合 [contracts/sync-websocket.md](contracts/sync-websocket.md)。
  - 每 10 秒收到 `ping`（測試可縮短間隔）。
  - 活動不存在時收到 `gone` 與 close code 4410。
  - token 無效時收到 `unauthorized`、`reason == "INVALID_TOKEN"`，close code 4401。
- [ ] T061 [P] [US6] 在 `tests/integration/test_us6_sync.py` 測試：
  - `Scenario: US6-AS1`：老師與兩組共 3 條連線，關輪後都收到相同的 `version` 與 `roundNumber`，而且有 `changedAt`。
  - `Scenario: US6-AS2`：伺服端在斷線期間不會因為推送失敗而影響其他連線或狀態。前端「同步中斷」的畫面行為由 quickstart 第 17 步人工驗證補足（純前端行為，沒有自動化瀏覽器測試）。
  - `Scenario: US6-AS3`：斷線期間發生變更，重連後第一則 `snapshot` 就是最新版本。
  - `Scenario: US6-AS4`：建立新的 `create_app()`（模擬重啟）後，舊老師 token 與舊裝置 token 的 WebSocket 都收到 `gone`，HTTP snapshot 回 410（SC-007）。
  - `Scenario: US6-AS5`：在 `ROUND_OPEN` 時，學生收到的每一則訊息都不含其他組的組名、憑證或 `hasSubmissions`（SC-009）。
- [ ] T062 [P] [US6] 在 `tests/perf/test_sync_latency.py` 撰寫 `@pytest.mark.perf` 效能測試（SC-001、研究 R2）：
  - 在背景執行緒以 `127.0.0.1` 啟動真實 uvicorn，連上老師 1 條與 6 組各 2 條，共 13 條 WebSocket。
  - 開輪、關輪、定案、結束各做 10 次，量測「送出 HTTP → 13 條連線都收到新版本」的時間。
  - 每項的最大值都要小於 2000 ms，並把每項的最大值與平均值印成報表。

### Implementation for User Story 6

- [ ] T063 [US6] **轉接層**：在 `src/lecture_quiz/adapters/web/ws_sync.py` 完成：
  - 只有 `changed` 時才推送。
  - 推送時逐一連線送出，任一連線失敗時只關閉該連線，並記錄 `INFO`（不含 token）。
  - 支援 `disconnect_device(code, token_hash, reason)`，給離開本組與刪除組別使用。
  - 重啟後找不到活動時，送 `gone`。
- [ ] T064 [US6] **轉接層**：在 `src/lecture_quiz/adapters/static/js/sync.js`、`teacher.js`、`student.js` 串接：
  - 「同步中斷，正在重新連線」橫幅。
  - 斷線期間停用所有成功提示。
  - 收到 `gone` 時清除身分並顯示「活動已失效，請重新建立或加入活動」。
  - 狀態列顯示版本與延遲。

**Checkpoint**: 所有 P1 故事完成，MVP 可以展示

---

## Phase 8: User Story 5 - 老師結束或取消活動並看到未成功題 (Priority: P2)

**Goal**: 定案後可以結束活動（即使還有未成功題）；準備中可以取消活動；終止後拒絕新加入與新提交

**Independent Test**: 定案後在還有 1 題未成功時結束活動，確認未成功題清單、仍可匯出、加入被拒；搶答中或未定案時結束被拒；準備中取消活動

### Tests for User Story 5 (REQUIRED) ⚠️

- [ ] T065 [P] [US5] 在 `tests/unit/core/test_state_machine_end_cancel.py` 測試：
  - `Scenario: US5-AS1`：在 `RESULT_FINAL` 結束後為 `ENDED`，`unsolved_questions` 含第 3 題。
  - `Scenario: US5-AS3`：在 `ROUND_OPEN`、`RESULT_PENDING` 結束時回傳 `STAGE_NOT_ALLOWED`，訊息含「請先關輪並確認定案」。
  - `Scenario: US5-AS4` ⚠ 提案相依 Q-09：在 `PREPARING` 取消後為 `CANCELLED`，之後任何操作都被拒。
  - `Scenario: US5-AS5`：`ENDED` 時加入被拒，`accepts_submission` 為 `False`。
  - `Scenario: US5-AS6`：在 `PREPARING` 送 `EndActivity` 被拒，訊息為「準備中只能取消活動」。
- [ ] T066 [P] [US5] 在 `tests/integration/test_us5_end_cancel.py` 以 HTTP 加 WebSocket 測試 `Scenario: US5-AS1`～`US5-AS6`：
  - AS1：所有頁面的快照都有 `unsolvedQuestions`。
  - `Scenario: US5-AS2`：`export_view` 在 `ENDED` 時可以使用，未成功題標示為未成功。
  - AS4 ⚠ Q-09／Q-33：在 `CANCELLED` 時呼叫 `export_view`，回傳 `STAGE_NOT_ALLOWED`。

### Implementation for User Story 5

- [ ] T067 [US5] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `EndActivity`（只允許 `RESULT_FINAL`）與 `CancelActivity`（只允許 `PREPARING`，⚠ 提案相依 Q-09）；`snapshot_view.py` 在 `ENDED` 時填入 `unsolvedQuestions`。
- [ ] T068 [US5] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `end(code, requester)`、`cancel(code, requester)`：兩者都呼叫 `scheduler.cancel`。
  - 給 005 的 `export_view(code, requester)`：只限老師，`CANCELLED` 時拒絕（⚠ 提案相依 Q-09／Q-33）。
- [ ] T069 [US5] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/end`（回傳 `unsolvedQuestions`）與 `POST /activities/{code}/cancel`。
- [ ] T070 [US5] **轉接層**：在 `teacher.html`、`teacher.js`、`student.html`、`student.js` 加入：
  - 「結束活動」按鈕：只在已定案時可按。
  - 「取消活動」按鈕：只在準備中顯示。
  - 已結束畫面：顯示未成功題清單。
  - 已取消畫面：學生顯示「活動已取消」，不顯示匯出入口。

**Checkpoint**: 完整生命週期（含收尾）都可以運作

---

## Phase 9: User Story 7 - 學生改正選錯的組別，老師清除多建的空組 (Priority: P2) ⚠ 提案相依

**Goal**: 非搶答中可以離開本組並改加入其他組；老師可以刪除沒有提交紀錄的組別

**Independent Test**: 準備中離開並加入正確組別；搶答中離開被拒；刪除空組成功；刪除有提交紀錄的組被拒

### Tests for User Story 7 (REQUIRED) ⚠️

- [ ] T071 [P] [US7] 在 `tests/unit/core/test_state_machine_group_correction.py` 測試，以下全部 ⚠ 提案相依：
  - `Scenario: US7-AS1`：在 `PREPARING`、`RESULT_PENDING`、`RESULT_FINAL` 執行 `LeaveGroup`，只移除該裝置；組別、其他裝置與 `success_count` 不變。
  - `Scenario: US7-AS2`：離開後可以加入另一組。
  - `Scenario: US7-AS3`：在 `ROUND_OPEN` 離開時回傳 `NO_GROUP_SWITCH_DURING_ROUND`。
  - `Scenario: US7-AS4`：原組的 `has_submissions` 在裝置離開後仍為 `True`。
  - `Scenario: US7-AS5`：刪除 `has_submissions=False` 的組時，移除組與其所有裝置，組名可以再使用。
  - `Scenario: US7-AS6`：刪除 `has_submissions=True` 的組時回傳 `GROUP_HAS_SUBMISSIONS`，`activity` 不變。
  - 另外測試：`MarkGroupSubmitted` 只在 `ROUND_OPEN` 時生效。
- [ ] T072 [P] [US7] 在 `tests/integration/test_us7_group_correction.py` 以 HTTP 加 WebSocket 測試 `Scenario: US7-AS1`～`US7-AS6`，以下全部 ⚠ 提案相依：
  - 離開時，該裝置的 WebSocket 收到 `unauthorized`、`reason == "LEFT_GROUP"`。
  - 刪除組別時，原組裝置收到 `reason == "GROUP_DELETED"`。
  - 在 `ROUND_OPEN` 刪除空組成功。
  - 「刪除」與 `mark_group_submitted` 同時發生時，不會出現「答案已記錄但組別被刪除」。

### Implementation for User Story 7

- [ ] T073 [US7] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `LeaveGroup`、`DeleteGroup`、`MarkGroupSubmitted`，允許的階段照 spec「不改變階段的組別操作」表（⚠ 提案相依）。
- [ ] T074 [US7] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作，以下全部 ⚠ 提案相依：
  - `leave_group(code, requester)`。
  - `delete_group(code, requester, name)`：名稱先解碼再正規化。
  - 給 003 的 `mark_group_submitted(code, group_name)`。
  - 成功後呼叫 `SyncPublisher.disconnect_device`。
- [ ] T075 [US7] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/groups/leave` 與 `DELETE /activities/{code}/groups/{name}`（⚠ 提案相依）。
- [ ] T076 [US7] **轉接層**：在 `student.html`、`student.js` 加入「離開本組」按鈕（搶答中停用並說明原因）；在 `teacher.html`、`teacher.js` 的組別清單，對 `hasSubmissions == false` 的組顯示「刪除」按鈕（⚠ 提案相依）。

**Checkpoint**: 全部 User Story 完成

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T077 [P] 建立 `tests/SCENARIO_MAP.md`：列出 44 個 `USn-ASm` 與對應的測試函式。用 `grep -rn "Scenario:" tests/` 核對沒有遺漏（原則 VI）。
- [ ] T078 [P] 在 `tests/integration/test_idempotency.py` 測試 SC-004：建立活動、加入組別、開輪各用相同的 `Idempotency-Key` 重送 20 次，重複的活動、組別、輪次數都是 0，每次回應都相同。
- [ ] T079 [P] 在 `tests/contract/test_error_safety.py` 測試 SC-008：觸發每一種 `RejectionReason`、404、400 `INVALID_REQUEST`、500，確認回應都有中文 `message`，而且不含 `Traceback`、`File "`、`.py`、任何 token、任何憑證。
- [ ] T080 [P] 在 `tests/integration/test_logging.py` 檢查日誌（技術限制 3）：
  - 用 `caplog` 擷取一輪完整流程的 log，確認層級是 `INFO`，而且不含任何 `teacherToken`、`deviceToken`、`credential` 的值。
  - 在 `src/` 中用 grep 確認沒有 `print(`。
- [ ] T081 執行 `ruff check .`、`ruff format --check .`、`mypy src`，全部通過並記錄結果（憲章 v1.0.1 技術限制 2）。
- [ ] T082 程式碼與圖表一致性驗證：逐一比對 `diagrams/001-activity-session-*.puml` 的組件、類別、方法名稱、時序與實作（例如 `ActivityService` 的方法、`RejectionReason` 的值）。有差異時，先更新圖表並重新轉出 PNG（原則 II）。
- [ ] T083 執行 `pytest` 與 `pytest -m perf`，記錄日期、指令，以及通過、失敗、略過的數字；perf 記錄四種操作的最大延遲（原則 VI、品質關卡 4）。
- [ ] T084 由非實作者依 [quickstart.md](quickstart.md) 的 21 步人工驗證，記錄在 `specs/001-activity-session/verification.md`：日期、每一步的操作與結果、第 10、12 步的延遲 ms，以及 SC-005「1 分鐘內兩組加入」、SC-010「30 秒內換組」的實際時間（原則 VI）。
- [ ] T085 [P] 指令或流程與文件不同時，更新 `specs/001-activity-session/quickstart.md`；在 `CLAUDE.md` 的「專案現況」補上 build、lint、test 指令與 `src/lecture_quiz` 三層結構（現在已有程式碼）。
- [ ] T086 用全新 clone 在乾淨的 venv 重跑安裝與 `pytest`，確認不依賴任何本機未提交的檔案（規章第 9 節）。
- [ ] T087 追蹤開發用 seed API 的移除：在 Issue #6（002）留言，註明「002 合併後的第一個 PR 移除 `src/lecture_quiz/adapters/web/dev_seed.py`、`LECTURE_QUIZ_DEV_SEED` 與 `tests/integration/test_dev_seed.py`」。本子功能內不刪除。
- [ ] T088 確認 ⚠ 提案相依的任務狀態：若 `docs/alignment.md` 2026-11-21 的 6 列仍是「待確認」，在 PR 描述中列出並標明不得合併；若已確認且結論不同，依 plan「受待確認提案影響的設計點」修改後重跑 T081～T084。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**：沒有相依，可以立即開始。
- **Foundational (Phase 2)**：依賴 Setup，會阻擋所有 User Story。
- **US1 (Phase 3)**：依賴 Foundational。
- **US2 (Phase 4)**：依賴 US1，加入組別需要已建立的活動與老師身分。
- **US3 (Phase 5)**：依賴 US1；US2 可以並行，因為開輪的 `baseline` 在沒有組別時也成立。
- **US4 (Phase 6)**：依賴 US3，必須先開輪才能關輪。
- **US6 (Phase 7)**：
  - 契約測試 T060 在 Foundational 之後就可以開始。
  - 整合與效能測試 T061、T062 依賴 US4。
- **US5 (Phase 8)**：依賴 US4，結束活動需要已定案的狀態。
- **US7 (Phase 9)**：依賴 US2；在 `ROUND_OPEN`、`RESULT_*` 的測試依賴 US4。
- **Polish**：依賴所有 User Story 完成。

### Within Each User Story

- 先寫測試並確認失敗，再實作。
- 實作順序為核心 → 服務層 → 轉接層（HTTP、WebSocket）→ 前端。
- 每個 Story 完成時，執行該 Story 的整合測試，作為 Checkpoint。

### Parallel Opportunities

- Setup：T003、T004 可以並行。
- Foundational：T006、T007、T008、T009、T011、T012、T013、T016、T017、T018、T022 可以並行（不同檔案）。
- 每個 Story 的測試任務（標 [P]）可以同時撰寫。
- 核心的 `input_rules.py` 任務（T035、T046）可以和該 Story 的測試並行。
- US6 的契約測試 T060 可以和 US1～US4 並行。
- Polish：T077～T080、T085 可以並行。

---

## Parallel Example: User Story 2

```bash
# 同時撰寫 US2 的測試：
Task: "T030 tests/unit/core/test_input_rules_group_name.py"
Task: "T031 tests/unit/core/test_state_machine_join.py"
Task: "T032 tests/unit/core/test_snapshot_view_groups.py"
Task: "T033 tests/contract/test_http_join.py"
Task: "T034 tests/integration/test_us2_join.py"

# 測試失敗後，核心規則可以先並行實作：
Task: "T035 src/lecture_quiz/core/activity/input_rules.py normalize_group_name"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2（基礎，包含架構測試）。
2. 依序完成 US1 → US2 → US3 → US4 → US6（全部 P1），每完成一個 Story 就執行該 Story 的整合測試。
3. **STOP and VALIDATE**：完成 P1 後，跑 quickstart 第 1～14、17、19、20 步。

### Incremental Delivery

1. 加上 US5（結束與取消）→ 驗證 quickstart 第 18、21 步。
2. 加上 US7（組別更正，⚠ 提案相依）→ 驗證 quickstart 第 11、15、16 步。若 OpenSpec 組不同意這兩項新增行為，整個 Phase 9 可以單獨移除，不影響其他 Story。
3. 完成 Polish → 開 PR（`Closes #5`），由 EricC430 審查。

### 兩人分工建議

- Foundational 完成後：
  - jacky0407 負責 US1 → US2 → US3 → US4。
  - EricC430 可以先寫 US6 的契約測試（T060），以及 US2、US3 的核心單元測試。
- 實作者與審查者輪替（規章 2.2）；T084 的人工驗證必須由非實作者執行。

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 每個 Story 都可以單獨完成與測試
- 實作前先確認測試是失敗的
- 每完成一個任務或一組相關任務就 commit，訊息格式 `<type>: <summary>`，附 `Refs #5`
- 避免：模糊的任務、多個任務同時改同一個檔案造成衝突、破壞 Story 獨立性的跨 Story 相依
