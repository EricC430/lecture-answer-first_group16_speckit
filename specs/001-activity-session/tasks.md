---

description: "001-activity-session 任務清單"
---

# Tasks: 活動建立、組別加入與階段同步

**Input**: Design documents from `/specs/001-activity-session/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（專案覆寫，憲章原則 VI）。

- spec 共有 57 個 Acceptance Scenario（2026-11-23 clarify 後：US1 新增 AS7、AS8，US2 新增 AS9、AS10；後續決議新增 US8 的 AS1～AS7、US7 的 AS7、AS8），每一個至少對應一個自動化測試；測試的 docstring 第一行寫 `Scenario: USn-ASm`。
- 測試先寫，並確認在實作前是失敗的。
- 本子功能不使用 Google，不需要 mock，也不需要真實路徑驗證。

**Diagrams**: REQUIRED（原則 II）。實作前先確認 `diagrams/001-activity-session-*.puml` 與 PNG 存在（T004）；實作後有一致性驗證任務（T082）。

**Architecture**: REQUIRED（技術限制 4，NON-NEGOTIABLE）。每個 Phase 的實作任務分三組，依序列出，相依方向為「轉接層 → 服務層 → 核心」：

- **核心**：`src/lecture_quiz/core/activity/`，只能是純函式。
- **服務層**：`src/lecture_quiz/app/activity/`。
- **轉接層**：`src/lecture_quiz/adapters/`。

**2026-11-23 更新（`/speckit-clarify` 後重跑 `/speckit-tasks`）**：`docs/alignment.md` 2026-11-21 的提案已於 2026-11-23 全部獲 OpenSpec 組確認，原本的「⚠ 提案相依」標記全部解除。依 Clarifications 新增 US1 的組數上限與 C7 任務（T089～T094），改寫 US2（組號）、US7 任務，並新增 T095（在有 plantuml.jar 的環境重新產生 PNG）。已完成任務的 ID 不重排。

**Organization**: 依 User Story 分組。P1 依 US1 → US2 → US3 → US4 → US6 的順序（後面的故事需要前面的狀態），接著是 P2 的 US5、US7。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立專案骨架、相依套件與品質工具

- [x] T001 建立 `pyproject.toml`：
  - 套件名 `lecture-quiz`，src 佈局 `src/lecture_quiz`，`requires-python = ">=3.11"`。
  - 執行相依：`fastapi`、`uvicorn[standard]`。
  - `[project.optional-dependencies].dev`：`pytest`、`pytest-timeout`、`httpx`、`websockets`、`ruff`、`mypy`。
  - `[tool.pytest.ini_options]`：`testpaths = ["tests"]`，註冊 marker `perf`，`addopts = "-m 'not perf'"`，`timeout = 30`。
- [x] T002 在 `pyproject.toml` 設定 Ruff 與 mypy（憲章 v1.0.1 技術限制 2）：
  - `[tool.ruff.lint] select = ["E","F","W","I","N","UP","B","D","ANN"]`，`pydocstyle.convention = "google"`，`per-file-ignores` 讓 `tests/**` 排除 `D`、`ANN`。
  - `[tool.ruff] target-version = "py311"`。
  - `[tool.mypy] files = ["src"]`，`disallow_untyped_defs = true`，`python_version = "3.11"`。
- [x] T003 [P] 建立套件與測試目錄，各放空的 `__init__.py`：
  - 套件：`src/lecture_quiz/`、`src/lecture_quiz/core/`、`src/lecture_quiz/core/activity/`、`src/lecture_quiz/app/`、`src/lecture_quiz/app/activity/`、`src/lecture_quiz/adapters/`、`src/lecture_quiz/adapters/web/`。
  - 測試目錄：`tests/unit/core/`、`tests/unit/app/`、`tests/architecture/`、`tests/contract/`、`tests/integration/`、`tests/perf/`。
- [x] T004 [P] 確認 `diagrams/001-activity-session-{component,class,sequence}.puml` 與對應 PNG 都存在，且 PNG 比 `.puml` 新；不符合時，先執行 `java -jar plantuml.jar "./diagrams/*.puml"`（原則 II）。

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有 User Story 共用的資料型別、服務骨架、HTTP／WebSocket 基礎與前端共用模組

**⚠️ CRITICAL**: 本階段完成前不得開始任何 User Story

### 測試基礎

- [x] T005 建立 `tests/conftest.py`，內容包括：
  - `FakeClock`：`now()` 回傳可手動 `advance(seconds)` 的有時區 `datetime`，起點 `2026-11-21T09:00:00+08:00`。
  - `ManualScheduler`：記錄 `schedule(code, deadline)`，`fire(code)` 時以 `deadline` 呼叫回呼。
  - `make_app(clock, scheduler, dev_seed=False)` 工廠。
  - fixture：`client`（`TestClient`）、`teacher`（建立活動並回傳 code、token 的 helper）。
- [x] T006 [P] 建立 `tests/architecture/test_core_is_pure.py`，用 `ast` 掃描 `src/lecture_quiz/core/**/*.py`：
  - 匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`lecture_quiz.app`、`lecture_quiz.adapters` 時失敗。
  - 呼叫 `datetime.now`、`datetime.utcnow`、`date.today` 時失敗。
  - 依據：研究 R4、技術限制 4。

### 核心（純函式）

- [x] T007 [P] 2026-11-23 隨 US2 完成（`Activity.max_groups`、`Group.number`、`Group.join_credential`、`DeviceIdentity.group_number`、各 Mapping 以組號為 key，研究 R9）。在 `src/lecture_quiz/core/activity/models.py` 建立 frozen dataclass，欄位與規則照 [data-model.md](data-model.md) 原文：
  - `Stage`（`PREPARING`、`ROUND_OPEN`、`RESULT_PENDING`、`RESULT_FINAL`、`ENDED`、`CANCELLED`；`is_terminal` 屬性）。
  - `TeacherIdentity(token_hash)`、`Group(number, join_credential, success_count, has_submissions)`、`DeviceIdentity(token_hash, group_number)`。
  - `RoundRules(question_numbers, fair_mode, countdown_seconds, deadline)`。
  - `Round(number, rules, opened_at, baseline, closed, closed_at, close_cause)`。
  - `Activity(code, stage, version, changed_at, teacher, max_groups, question_numbers, solved_questions, groups, devices, rounds)`，含 `current_round`、`unsolved_questions` 衍生屬性。
  - 集合欄位一律使用 `tuple`、`frozenset`、`MappingProxyType`。
  - 每個公開類別都有 Google 風格 docstring。
- [x] T008 [P] 2026-11-23 隨 US2、US7 完成（`CreateActivity(max_groups_raw)`、`JoinGroup(number_raw, credential_raw)`、`LeaveGroup`、`DeleteGroup(number_raw)`、`MarkGroupSubmitted(group_number)`）。在 `src/lecture_quiz/core/activity/commands.py` 建立：
  - Actor 型別：`Teacher(token_hash)`、`Device(token_hash)`、`System`、`Anonymous`。
  - Command 型別：`CreateActivity(max_groups_raw)`、`JoinGroup(number_raw, credential_raw)`、`LeaveGroup`、`DeleteGroup(number_raw)`、`OpenRound(question_numbers, fair_mode, countdown_raw)`、`CloseRound`、`Finalize(outcome)`、`EndActivity`、`CancelActivity`、`ReplaceQuestions(question_numbers)`、`MarkGroupSubmitted(group_number)`。
  - `FinalizeOutcome(solved_questions: frozenset[int], success_increments: Mapping[int, int])`（key 為組號）。
- [x] T009 [P] 在 `src/lecture_quiz/core/activity/results.py` 建立：
  - `RejectionReason` 列舉，11 個值，每個值附 HTTP 狀態碼與 [data-model.md](data-model.md) 表中的中文訊息；`STAGE_NOT_ALLOWED` 的訊息由「階段 × 操作」產生。
  - `IssuedSecrets(group_credential, device_token_hash)`，由服務層傳入。
  - `Transition(ok, activity, changed, rejection, issued)`。
- [x] T010 在 `src/lecture_quiz/core/activity/state_machine.py` 建立 `ActivityStateMachine.apply(activity, command, now, issued=None) -> Transition` 的分派骨架：
  - 依序檢查：活動已終止、老師權限、「階段 × 操作」相容表。表格照 spec「活動階段狀態機」與「不改變階段的組別操作」兩張表。
  - 尚未實作的操作回傳 `STAGE_NOT_ALLOWED`。
  - 成功且 `changed` 時，`version + 1`，`changed_at = now`。
- [x] T011 [P] 在 `src/lecture_quiz/core/activity/snapshot_view.py` 建立 `ActivitySnapshot` 與 `SnapshotView.for_teacher`、`SnapshotView.for_group` 的共同欄位：`code`、`version`、`changedAt`、`stage`、`roundNumber`、`openQuestions`、`deadline`、`fairMode`、`unsolvedQuestions`，格式照 [contracts/sync-websocket.md](contracts/sync-websocket.md)。

### 服務層

- [x] T012 [P] 在 `src/lecture_quiz/app/activity/ports.py` 定義：
  - Protocol：`Clock`、`CountdownScheduler(schedule, cancel)`、`SyncPublisher(publish)`、`ActivityGateway`（`stage`、`is_teacher`、`replace_questions`，都有 `code` 參數）。
  - 型別：`Requester`、`Outcome[T]`。
  - 依據：[contracts/service-interfaces.md](contracts/service-interfaces.md)。
- [x] T013 [P] 在 `src/lecture_quiz/app/activity/secrets_gen.py` 實作：
  - `new_code(existing)` 與 `new_credential()`：6 碼，字元集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`，用 `secrets.choice`；活動代碼不與 `existing` 重複。
  - `new_token()`：`secrets.token_urlsafe(32)`。
  - `hash_token()`：SHA-256。
  - `tokens_match()`：`secrets.compare_digest`。
  - `normalize_code_input()`：去除首尾空白並轉成大寫。
- [x] T014 在 `src/lecture_quiz/app/activity/registry.py` 實作 `ActivityRegistry`：
  - 存放：`code → Activity`、每個活動一把 `asyncio.Lock`、活動內的「(身分雜湊, Idempotency-Key) → 原回應」（每個活動最多 1000 筆，超過時淘汰最舊的）、全域的「建立活動 key → (code, teacher token)」。
  - 只存在記憶體（原則 VII）。
- [x] T015 在 `src/lecture_quiz/app/activity/service.py` 建立 `ActivityService._execute(code, requester, command, idempotency_key)`，流程照研究 R6：
  1. 取得鎖。
  2. 查詢去重表。
  3. 呼叫 `ActivityStateMachine.apply(..., now=clock.now())`。
  4. 成功時替換 `Activity`。
  5. 記錄去重結果。
  6. 釋放鎖。
  7. `changed` 時呼叫 `SyncPublisher.publish`。
  - 查表、套用、記錄都在同一把鎖內（2026-11-23 依 PR #15 審查第 2 項修正，原本查表在鎖外）；以 `asyncio.gather` 同 key 並行建立的測試在 `tests/integration/test_us1_teacher.py`。
  - 另外實作 `resolve_requester(code, bearer_token)`，把 token 轉成 `Teacher`、`Device` 或 `Anonymous`。
- [x] T016 [P] 在 `tests/unit/app/test_secrets_registry.py` 測試：代碼字元集與長度、不與既有代碼重複、`compare_digest` 比對、去重表上限 1000 筆與淘汰順序。

### 轉接層

- [x] T017 [P] 在 `src/lecture_quiz/adapters/clock.py` 實作 `SystemClock.now()`，回傳有時區的現在時間。
- [x] T018 [P] 在 `src/lecture_quiz/adapters/countdown.py` 實作 `AsyncioCountdownScheduler`：`schedule(code, deadline)` 建立 asyncio 任務，到期時呼叫回呼；`cancel(code)` 取消任務。
- [x] T019 在 `src/lecture_quiz/adapters/web/http_api.py` 建立 APIRouter `/api` 的共用基礎：
  - 解析 `Authorization: Bearer` 與 `Idempotency-Key`。
  - `RejectionReason` 轉成 HTTP 狀態碼與 `{"error": {"code", "message"}}`；請求驗證錯誤統一成 `INVALID_REQUEST`，訊息指出欄位。
  - 全域例外處理器：未預期的錯誤回 500 與通用訊息，不含堆疊追蹤。
  - 請求 log 中介層：每個請求一行 `INFO`，只記錄方法、路徑樣板、活動代碼、結果代碼、`version`、耗時。
  - 依據：[contracts/http-api.md](contracts/http-api.md)、技術限制 3。
- [x] T020 在 `src/lecture_quiz/adapters/web/ws_sync.py` 實作 `WebSocketHub`（`SyncPublisher` 的實作）：
  - 路徑 `/ws/activities/{code}`。
  - 第一則訊息必須是 `auth`，5 秒內沒收到就關閉連線。
  - 每 10 秒送一次 `ping`。
  - 活動不存在時送 `gone` 並以 4410 關閉；token 無效時送 `unauthorized`（附 `reason`）並以 4401 關閉。
  - 每條連線依角色以 `SnapshotView` 裁切後推送；單一連線送出失敗時只關閉該連線。
  - 依據：[contracts/sync-websocket.md](contracts/sync-websocket.md)。
- [x] T021 在 `src/lecture_quiz/main.py` 建立 `create_app(clock, scheduler, dev_seed)` 與模組層級的 `app`：
  - `logging.basicConfig(level=logging.INFO, stream=sys.stdout)`。
  - 掛載 HTTP router、WebSocket 與靜態檔 `adapters/static`。
  - 從環境變數 `LECTURE_QUIZ_DEV_SEED` 讀取 `dev_seed`。
  - 在 docstring 註明啟動方式為 `uvicorn lecture_quiz.main:app --host 127.0.0.1`。
- [x] T022 [P] 建立前端共用模組，都放在 `src/lecture_quiz/adapters/static/`：
  - `css/app.css`：狀態列與「同步中斷」橫幅樣式。
  - `js/api.js`：fetch 包裝，自動帶 `Authorization` 與每次操作的 `Idempotency-Key`（UUID），重試時沿用同一個 key；錯誤時顯示 `error.message`。
  - `js/identity.js`：老師 token 存在 `localStorage["teacher:{code}"]`，裝置 token 存在 `sessionStorage["device:{code}"]`（alignment 2026-11-23 C6）。
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

- [x] T023 [P] [US1] 在 `tests/unit/core/test_state_machine_create_and_permissions.py` 測試：
  - `Scenario: US1-AS1`：`CreateActivity` 後為 `PREPARING`、`version == 1`、沒有題目也沒有輪次。
  - `Scenario: US1-AS4, US1-AS5, US1-AS6`：`Device`、別的活動的 `Teacher`、`Anonymous` 對 001 擁有的 6 種老師專用操作（開輪、關輪、定案、結束、取消、匯入題號 `ReplaceQuestions`）都回傳 `NOT_TEACHER`，且 `activity` 完全不變（SC-002）。
  - 範圍調整（2026-11-23，jacky0407 決定，回應 PR #15 審查 nit）：判錯、撤銷判錯、匯出、刪除組別不屬於 001 的 Command，由 004、005、US7 各自測試權限。
- [x] T024 [P] [US1] 在 `tests/contract/test_http_activities.py` 測試契約：
  - `POST /api/activities` 回 `201 {"code", "teacherToken", "version"}`。
  - 代碼不存在時回 404 與 `error.code`、`error.message`。
  - 錯誤回應不含 `Traceback`、檔案路徑或 token。
- [x] T025 [P] [US1] 在 `tests/integration/test_us1_teacher.py` 測試：
  - `Scenario: US1-AS1`：已有一個活動時再建立一個，兩個代碼都是 6 碼，字元都在字元集內，而且互不相同。
  - `Scenario: US1-AS2` （C6）：用同一個 token 建立新的 client（模擬重新整理或新分頁），仍可取得老師快照並操作。
  - `Scenario: US1-AS3` （C6）：沒有 token 的 client 操作時回 403 `NOT_TEACHER`。
  - `Scenario: US1-AS4`：學生裝置 token 操作時回 403，回應中不含任何 credential 或 token。
  - `Scenario: US1-AS5`：活動 B 的老師 token 操作活動 A 時回 403，A 的 `version` 不變。
  - `Scenario: US1-AS6`：只帶活動代碼、不帶 token 時回 403，訊息為「需要這個活動的老師身分才能操作。」

### Implementation for User Story 1

- [x] T026 [US1] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `CreateActivity`（產生 `PREPARING` 的 `Activity`；代碼與 `teacher.token_hash` 由 `issued` 傳入），以及老師權限檢查（`actor` 是 `Teacher` 且 `token_hash` 相同）。
- [x] T027 [US1] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `create(idempotency_key)`：產生代碼與 token；同一個 key 回傳同一組結果。
  - `stage(code)`、`is_teacher(code, requester)`（`ActivityGateway`）。
  - `snapshot(code, requester)`。
- [x] T028 [US1] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities` 與 `GET /activities/{code}/snapshot`。snapshot 在活動不存在時：帶 token 回 410 `ACTIVITY_GONE`，不帶 token 回 404。
- [x] T029 [US1] **轉接層**：建立 `src/lecture_quiz/adapters/static/teacher.html` 與 `js/teacher.js`：
  - 「建立活動」按鈕，建立後顯示代碼，token 存到 `identity.js`（alignment 2026-11-23 C6）。
  - 網址帶 `?code=` 時，從 `localStorage` 取 token 並連線同步；沒有 token 時顯示「需要該活動的老師身分」。

### US1 補充：組數上限與一位老師一個活動（2026-11-23 clarify，FR-036、FR-037）

- [x] T089 [P] [US1] 在 `tests/unit/core/test_input_rules_max_groups.py` 與 `tests/unit/core/test_state_machine_create_and_permissions.py` 測試：
  - `Scenario: US1-AS7`：`InputRules.validate_max_groups` 接受 `1`、`99`；拒絕 `0`、`-1`、`100`、`2.5`、`"6"`、`""`、`None`、`True`，回傳 `INVALID_MAX_GROUPS`；`CreateActivity(max_groups_raw=…)` 不合法時 `Transition.ok is False` 且沒有活動。
  - `Scenario: US1-AS1`：`CreateActivity(max_groups_raw=6)` 後 `activity.max_groups == 6`。
- [x] T090 [P] [US1] 在 `tests/contract/test_http_activities.py` 與 `tests/integration/test_us1_teacher.py` 測試：
  - 契約：`POST /api/activities {"maxGroups": 6}` 回 `201 {"code", "teacherToken", "maxGroups", "version"}`；`maxGroups` 不合法時回 `400 INVALID_MAX_GROUPS`；老師快照含 `maxGroups`。
  - `Scenario: US1-AS8`：帶著存續中活動 K 的老師 token 建立新活動時回 `409 TEACHER_HAS_ACTIVE_ACTIVITY`，訊息含 K，活動數不增加；K 結束或取消後，同一 token 可以建立；token 找不到活動（模擬重啟）時可以建立。
  - 同一個 `Idempotency-Key` 重送時，仍回傳同一個活動（不因 C7 檢查而拒絕重送）。
- [x] T091 [US1] **核心**：在 `input_rules.py` 實作 `validate_max_groups`（1～99 的 `int`，排除 `bool`）；在 `commands.py` 為 `CreateActivity` 加 `max_groups_raw`；在 `models.py` 為 `Activity` 加 `max_groups`；在 `results.py` 新增 `INVALID_MAX_GROUPS`、`TEACHER_HAS_ACTIVE_ACTIVITY`；`state_machine._create` 驗證後寫入 `max_groups`。
- [x] T092 [US1] **服務層**：在 `registry.py` 實作 `find_by_teacher(token_hash)`；在 `service.py` 把 `create` 改為 `create(max_groups_raw, teacher_token, idempotency_key) -> Outcome[CreatedActivity]`：建立鎖內先查重送表，再做 C7 檢查（研究 R10），最後呼叫狀態機。
- [x] T093 [US1] **轉接層**：`http_api.py` 的 `POST /activities` 接收本文 `maxGroups`（原樣交給核心）與選填的 `Authorization`，回應加上 `maxGroups`；`SnapshotView.for_teacher` 加上 `maxGroups`。
- [x] T094 [US1] **轉接層**：`teacher.html`、`teacher.js` 加入「組數上限」輸入（預設 6，`min=1 max=99`）；建立時附上 `localStorage["teacher:last"]` 那個活動的老師 token；建立成功後更新 `teacher:last`；畫面顯示組數上限。`identity.js` 新增 `getLastTeacherCode`／`setLastTeacherCode`。

**Checkpoint**: US1 可以獨立測試

---

## Phase 4: User Story 2 - 學生以組號加入，多裝置同組並可恢復身分 (Priority: P1)

> 2026-11-23 依 Clarifications 改寫：組號（1～N）取代組名；組別加入憑證已獲 OpenSpec 組確認（B3）。原本測試用的最小入口 `JoinGroup(group_name)`、`ActivityService.join(code, group_name)` 與 `tests/conftest.py` 的 `join_group` 要一併改成正式流程。

**Goal**: 學生用代碼加組號加入；既有組要附上憑證；本組裝置看得到憑證；重新整理後恢復身分

**Independent Test**: 兩個 client 加入同一組（第二個附憑證），第三個加入另一組；確認同組身分與憑證一致、他組看不到；再測錯誤代碼、超出範圍或格式錯誤的組號、錯誤憑證、重新整理、中途加入與重複加入

### Tests for User Story 2 (REQUIRED) ⚠️

- [x] T030 [P] [US2] 在 `tests/unit/core/test_input_rules_group_number.py` 測試 `normalize_group_number(raw, max_groups=6)`：
  - 接受 `3`、`"3"`、`" 3 "`、`"03"`、`"３"`、`"０３"`、`6`、`1`，都回傳整數。
  - 拒絕 `0`、`7`、`-1`、`2.5`、`"2.5"`、`"三"`、`"3組"`、`""`、`"　"`、`None`、`True`、`[3]`，回傳 `INVALID_GROUP_NUMBER`；訊息為「組號須為 1～6 的整數。」。
  - `normalize_credential`：`" q8mz3r "` 變成 `"Q8MZ3R"`；`None` 變成 `""`。
- [x] T031 [P] [US2] 在 `tests/unit/core/test_state_machine_join.py` 測試：
  - `Scenario: US2-AS1`：組號 `" ０３ "` 建立第 3 組，並為該裝置建立 `DeviceIdentity(group_number=3)`；憑證來自 `issued.group_credential`。
  - `Scenario: US2-AS2`：既有組號加上正確憑證（大小寫、首尾空白不影響）時，新增裝置，不新增組。
  - `Scenario: US2-AS4`：既有組號不附憑證或憑證錯誤時，回傳 `BAD_CREDENTIAL`，`activity` 不變，訊息含組號、不含憑證。
  - `Scenario: US2-AS5`：組號格式錯誤或超出 1～N 時回傳 `INVALID_GROUP_NUMBER`，`activity` 不變。
  - `Scenario: US2-AS6`：`ENDED`、`CANCELLED` 時拒絕加入，訊息依階段寫成「活動已結束／已取消」。
  - `Scenario: US2-AS7`：在 `ROUND_OPEN` 加入新組，`success_count == 0`，`stage` 不變。
  - `Scenario: US2-AS9`：`Device` 已在 `devices` 中時回傳 `ALREADY_IN_GROUP`，`activity` 不變。
- [x] T032 [P] [US2] 在 `tests/unit/core/test_snapshot_view_groups.py` 測試：
  - `Scenario: US2-AS3`：`for_group` 只含 `ownGroup`（`number`、`credential`、`successCount`）；`for_teacher` 的 `groups` 依組號排序，含每一組的 `credential`。
  - FR-030：`for_group` 的序列化 JSON 不含任何其他組的組號、憑證，也不含 `groups`、`maxGroups`。
- [x] T033 [P] [US2] 在 `tests/contract/test_http_join.py` 測試契約：
  - `POST /groups/join {"groupNumber": 3}` 回 `200 {"deviceToken", "groupNumber", "credential", "version"}`。
  - 代碼輸入 `" k7qh2m "` 視為 `K7QH2M`；代碼不存在且未帶 token 時回 404。
  - 已帶有效裝置 token 再加入時，回 `409 ALREADY_IN_GROUP`「請先離開本組」。
  - 錯誤回應不含任何憑證或 token。
- [x] T034 [P] [US2] 在 `tests/integration/test_us2_join.py` 以 HTTP 加 WebSocket 測試 `Scenario: US2-AS1`～`US2-AS9`：
  - AS2：兩個裝置的快照中，`ownGroup` 相同。
  - AS3：其他組的快照中沒有第 3 組的憑證；老師快照有每一組的憑證。
  - AS4：錯誤訊息含「向同組同學查看本組加入憑證」，而且不含憑證本身。
  - AS8：用同一個裝置 token 重新連 WebSocket，取得原組別。

### Implementation for User Story 2

- [x] T035 [P] [US2] **核心**：在 `src/lecture_quiz/core/activity/input_rules.py` 實作 `normalize_group_number(raw, max_groups)`（研究 R9：`int` 或半形／全形數字字串、前導零與首尾空白、1～N）與 `normalize_credential(raw)`；`results.py` 把 `INVALID_GROUP_NAME` 改為 `INVALID_GROUP_NUMBER`，新增 `ALREADY_IN_GROUP`，`BAD_CREDENTIAL` 訊息改為組號版；訊息需要帶入組號或 N 時由 `describe_rejection` 產生。
- [x] T036 [US2] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `JoinGroup(number_raw, credential_raw)`：
  - 允許的階段：非終止階段。
  - `Device` 已在 `devices` 中時拒絕（`ALREADY_IN_GROUP`）。
  - 新組號：使用 `issued.group_credential` 建立 `Group(number, join_credential)`。
  - 既有組號：用 `hmac.compare_digest` 比對正規化後的憑證。
  - 新增 `DeviceIdentity(token_hash, group_number)`，`token_hash` 來自 `issued`。
  - `models.py`：`Group.number`、`DeviceIdentity.group_number`，`groups`、`Round.baseline` 以組號為 key；`FinalizeOutcome.success_increments` 以組號為 key（T007、T008 一併完成）。
- [x] T037 [US2] **核心**：在 `src/lecture_quiz/core/activity/snapshot_view.py` 補上 `for_group(activity, group_number)` 的 `ownGroup`（`number`、`credential`、`successCount`）與 `for_teacher` 的 `groups`（依組號排序：`number`、`credential`、`successCount`、`hasSubmissions`、`deviceCount`）。
- [x] T038 [US2] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `join(code, number_raw, credential_raw, requester, idempotency_key) -> Outcome[JoinedDevice]`：產生憑證與裝置 token，回傳原始 token 一次與該組憑證。
  - `resolve_device(code, device_token) -> Outcome[DeviceContext]`：給 003 使用。
  - `ExportView.groups` 依組號排序。
- [x] T039 [US2] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/groups/join`（本文 `groupNumber`、`credential` 原樣交給核心）；`GET snapshot` 與 WebSocket 的學生連線已依裝置身分以 `for_group` 裁切，改用組號。
- [x] T040 [US2] **轉接層**：更新 `src/lecture_quiz/adapters/static/student.html` 與 `js/student.js`：
  - 加入表單：活動代碼（網址有 `?code=` 時預填）、組號、選填的憑證。
  - 成功後把裝置 token 存到 `sessionStorage`，網址改為 `?code=`，並常駐顯示「第 n 組」與「本組加入憑證」。
  - 重新整理時自動恢復身分。
  - 老師頁的組別清單顯示每一組的組號、憑證、裝置數、成功次數。
  - 更新 `tests/conftest.py` 的 `join_group(client, code, number)` 改走 HTTP，以及 `tests/perf/test_sync_latency.py`、`dev_seed` 相關測試的組別寫法。

**Checkpoint**: US1 與 US2 都能獨立運作

---

## Phase 5: User Story 3 - 老師依條件開輪並固定本輪規則 (Priority: P1)

**Goal**: 已有題目時才能開輪；預設全選未成功題；公平模式預設關閉；倒數 1～3600 秒；規則在開輪時固定

**Independent Test**: 放入 4 題後，分別測試合法開輪、零題、選了已成功題、未定案就開輪、輪中修改規則、倒數超出範圍

### Tests for User Story 3 (REQUIRED) ⚠️

- [x] T041 [P] [US3] 在 `tests/unit/core/test_input_rules_round.py` 測試：
  - `Scenario: US3-AS6` （C9）：`validate_countdown` 接受 `None`、`1`、`3600`；拒絕 `0`、`-1`、`3601`、`2.5`、`"10"`、`""`、`True`，回傳 `INVALID_COUNTDOWN`，訊息為「倒數秒數須為 1～3600 的整數。」
  - `validate_selection` 拒絕空清單、重複題號、不存在的題號、已成功的題號，回傳 `INVALID_SELECTION`。
- [x] T042 [P] [US3] 在 `tests/unit/core/test_state_machine_open_round.py` 測試：
  - `Scenario: US3-AS1`：`question_numbers=None` 時選取全部未成功題，`fair_mode` 預設為 `False`，`deadline` 為 `None`。
  - `Scenario: US3-AS2`：選 2 題，建立 `Round(number=1)`，`baseline` 等於各組 `success_count`，`stage == ROUND_OPEN`。
  - `Scenario: US3-AS3`：沒有題目時回傳 `NO_QUESTIONS`。
  - `Scenario: US3-AS4`：零題、已成功題、在 `RESULT_PENDING` 時開輪，全部被拒。
  - `Scenario: US3-AS5`：在 `ROUND_OPEN` 再送 `OpenRound` 時回傳 `RULES_LOCKED`，規則不變。
  - 倒數 60 秒時，`deadline == opened_at + 60s`。
- [x] T043 [P] [US3] 在 `tests/unit/core/test_replace_questions.py` 測試：
  - `ReplaceQuestions` 只允許老師在 `PREPARING` 時呼叫，成功時整份取代題號。
  - 被拒時（例如在 `ROUND_OPEN`），既有題號完全不變（原則 III）。
- [x] T044 [P] [US3] 在 `tests/contract/test_http_rounds.py` 測試契約：
  - `POST /rounds` 回 `201 {"roundNumber", "deadline", "version"}`。
  - `countdownSeconds: 2.5` 回 400 `INVALID_COUNTDOWN`。
- [x] T045 [P] [US3] 在 `tests/integration/test_us3_open_round.py` 以 HTTP 加 `ManualScheduler` 測試 `Scenario: US3-AS1`～`US3-AS7`：
  - AS2：所有 WebSocket 連線都收到 `stage == "ROUND_OPEN"`。
  - AS7：同一個 `Idempotency-Key` 重送開輪，只產生一個輪次，回應相同（SC-004）。
  - 註（2026-11-23）：AS4 的「選已成功題」「結果未定案時開新輪」需要關輪與定案，整合層改由 US4-AS5 涵蓋，核心層仍在 T042 測試；另補一個同 key 並行開輪只套用一次的測試（PR #15 審查第 2 項）。

### Implementation for User Story 3

- [x] T046 [P] [US3] **核心**：在 `src/lecture_quiz/core/activity/input_rules.py` 實作：
  - `validate_countdown(raw)`：`None` 或 1～3600 的 `int`，排除 `bool`（alignment 2026-11-23 C9）。
  - `validate_selection(selected, imported, solved)`：`selected` 為 `None` 時回傳全部未成功題；其餘照 T041 的規則。
- [x] T047 [US3] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作：
  - `OpenRound`：允許 `PREPARING`（必須有題目）與 `RESULT_FINAL`；建立 `RoundRules` 與 `Round`，`deadline = now + countdown_seconds`。
  - `ReplaceQuestions`：只允許 `PREPARING`。
- [x] T048 [US3] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `open_round(...)`：成功且有 `deadline` 時，呼叫 `scheduler.schedule(code, deadline)`。
  - `replace_questions(code, requester, question_numbers)`（`ActivityGateway`）。
  - `current_round(code)`：給 004 使用。
- [x] T049 [US3] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/rounds`。
- [x] T050 [US3] **轉接層**：建立 `src/lecture_quiz/adapters/web/dev_seed.py`：
  - 端點 `POST /api/dev/activities/{code}/seed-questions`，只在 `dev_seed=True` 時掛載，只限老師，呼叫 `replace_questions(1..count)`。
  - 在 `tests/integration/test_dev_seed.py` 測試：預設不存在（404）、啟用後學生呼叫時回 403。
  - 依據：研究 R8、Complexity Tracking。
- [x] T051 [US3] **轉接層**：在 `src/lecture_quiz/adapters/static/teacher.html` 與 `js/teacher.js` 加入：
  - 開輪面板：題目核取方塊預設全選未成功題、公平模式預設關閉、倒數輸入選填（alignment 2026-11-23 C9）。
  - 「放入假題目」按鈕：只在 seed 端點存在時顯示。

**Checkpoint**: US1～US3 可以獨立運作

---

## Phase 6: User Story 4 - 關輪只發生一次，並先定案才能往下走 (Priority: P1)

**Goal**: 手動關輪或倒數截止都只關一次；必須由老師定案後才能開下一輪或結束

**Independent Test**: 同時送出手動關輪與倒數截止 50 次，每次都只有 1 份結果；未定案時開輪與結束都被拒

### Tests for User Story 4 (REQUIRED) ⚠️

- [x] T052 [P] [US4] 在 `tests/unit/core/test_state_machine_close_finalize.py` 測試：
  - `Scenario: US4-AS1`：`CloseRound(Teacher)` 後為 `RESULT_PENDING`，`closed=True`，`close_cause="teacher"`。
  - `Scenario: US4-AS2`：`CloseRound(System)` 在 `now >= deadline` 時生效；`now < deadline` 時回傳成功但 `changed=False`。
  - `Scenario: US4-AS3`：已關輪後再收到 `CloseRound`，`changed=False`，`version` 不變。
  - `Scenario: US4-AS4`：`RESULT_PENDING` 不會自行轉移。
  - `Scenario: US4-AS5`：在 `RESULT_PENDING` 開輪時回傳 `STAGE_NOT_ALLOWED`。
  - `Scenario: US4-AS6`：`Finalize(outcome)` 後為 `RESULT_FINAL`，`solved_questions` 與 `success_count` 依 `outcome` 更新；再開輪時 `number=2`，只能選未成功題。
  - `is_deadline_passed` 的邊界：截止前 1 微秒為 `False`、剛好截止時為 `True`。
- [x] T053 [P] [US4] 在 `tests/unit/app/test_concurrent_close.py` 測試 SC-003：
  - 用 `asyncio.gather(service.close_round(teacher), scheduler.fire(code))`，重複 50 次，每次都新建活動。
  - 每次只有一個呼叫產生變更，`version` 只加 1，`SyncPublisher` 只被呼叫一次。
- [x] T054 [P] [US4] 在 `tests/contract/test_http_close_finalize.py` 測試契約：
  - `POST /rounds/current/close` 回 `{"roundNumber", "version", "alreadyClosed"}`，第二次呼叫 `alreadyClosed == true`，而且 `version` 不變。
  - `POST /rounds/current/finalize` 回 `{"version"}`。
- [x] T055 [P] [US4] 在 `tests/integration/test_us4_close_finalize.py` 以 HTTP、WebSocket、`FakeClock`、`ManualScheduler` 測試 `Scenario: US4-AS1`～`US4-AS6`。

### Implementation for User Story 4

- [x] T056 [US4] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作：
  - `CloseRound`：`Teacher` 與 `System` 都可以；`System` 只有在 `now >= deadline` 時才生效；已關輪時 `changed=False`。
  - `Finalize(outcome)`：`outcome` 的題號必須是本輪所選題目的子集，否則拒絕。
  - `is_deadline_passed(round, now)`。
- [x] T057 [US4] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `close_round(code, requester)`：成功時呼叫 `scheduler.cancel(code)`。
  - `finalize(code, requester, outcome=FinalizeOutcome(frozenset(), {}))`。
  - 給 003 的 `accepts_submission(code, now)`。
  - 倒數回呼：`close_round(System)`，`now = max(clock.now(), deadline)`（2026-11-23 依 PR #15 審查第 3 項修正）。
- [x] T058 [US4] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /rounds/current/close`（含 `alreadyClosed`）與 `POST /rounds/current/finalize`；在 `main.py` 把 `AsyncioCountdownScheduler` 的回呼接到服務層。
- [x] T059 [US4] **轉接層**：在 `teacher.html`、`teacher.js`、`student.html`、`student.js` 加入「關輪」「確認定案」按鈕，以及兩邊的倒數剩餘秒數（依 `deadline` 計算）。
  - 註（2026-11-23）：學生頁的顯示與倒數已完成，但加入表單待 US2，目前只能以本分頁已保存的裝置身分恢復。

**Checkpoint**: 搶答主流程（建立 → 加入 → 開輪 → 關輪 → 定案）可以運作

---

## Phase 7: User Story 6 - 所有畫面兩秒內同步，斷線與重啟有明確提示 (Priority: P1)

**Goal**: 狀態變更在 2 秒內推送到所有頁面；斷線時顯示中斷；重連後取得完整快照；重啟後提示活動失效

**Independent Test**: 老師加 2 組連線，關輪後都收到相同版本；斷線重連取得最新快照；建立新的 app 實例（模擬重啟）後，舊 token 收到 `gone`

### Tests for User Story 6 (REQUIRED) ⚠️

- [x] T060 [P] [US6] 在 `tests/contract/test_ws_sync.py` 測試契約：
  - 第一則訊息不是 `auth`，或 5 秒內沒送，會被關閉。
  - 老師版與學生版的 `snapshot` 欄位符合 [contracts/sync-websocket.md](contracts/sync-websocket.md)。
  - 每 10 秒收到 `ping`（測試可縮短間隔）。
  - 活動不存在時收到 `gone` 與 close code 4410。
  - token 無效時收到 `unauthorized`、`reason == "INVALID_TOKEN"`，close code 4401。
- [x] T061 [P] [US6] 在 `tests/integration/test_us6_sync.py` 測試：
  - `Scenario: US6-AS1`：老師與兩組共 3 條連線，關輪後都收到相同的 `version` 與 `roundNumber`，而且有 `changedAt`。
  - `Scenario: US6-AS2`：伺服端在斷線期間不會因為推送失敗而影響其他連線或狀態。前端「同步中斷」的畫面行為由 quickstart 第 17 步人工驗證補足（純前端行為，沒有自動化瀏覽器測試）。
  - `Scenario: US6-AS3`：斷線期間發生變更，重連後第一則 `snapshot` 就是最新版本。
  - `Scenario: US6-AS4`：建立新的 `create_app()`（模擬重啟）後，舊老師 token 與舊裝置 token 的 WebSocket 都收到 `gone`，HTTP snapshot 回 410（SC-007）。
  - `Scenario: US6-AS5`：在 `ROUND_OPEN` 時，學生收到的每一則訊息都不含其他組的組號、憑證或 `hasSubmissions`（SC-009）。
- [x] T062 [P] [US6] 2026-11-23 本機執行 `pytest -m perf`：1 passed；最大延遲 開輪 6.5 ms、關輪 5.1 ms、定案 5.0 ms、結束 5.4 ms（各 10 次、13 條連線）。在 `tests/perf/test_sync_latency.py` 撰寫 `@pytest.mark.perf` 效能測試（SC-001、研究 R2）：
  - 在背景執行緒以 `127.0.0.1` 啟動真實 uvicorn，連上老師 1 條與 6 組各 2 條，共 13 條 WebSocket。
  - 開輪、關輪、定案、結束各做 10 次，量測「送出 HTTP → 13 條連線都收到新版本」的時間。
  - 每項的最大值都要小於 2000 ms，並把每項的最大值與平均值印成報表。

### Implementation for User Story 6

- [x] T063 [US6] 2026-11-23 隨 US7 完成 `disconnect_device`（其餘項目已在 T020 完成並由 T060、T061 驗證）。**轉接層**：在 `src/lecture_quiz/adapters/web/ws_sync.py` 完成：
  - 只有 `changed` 時才推送。
  - 推送時逐一連線送出，任一連線失敗時只關閉該連線，並記錄 `INFO`（不含 token）。
  - 支援 `disconnect_device(code, token_hash, reason)`，給離開本組與刪除組別使用。
  - 重啟後找不到活動時，送 `gone`。
- [x] T064 [US6] **轉接層**：在 `src/lecture_quiz/adapters/static/js/sync.js`、`teacher.js`、`student.js` 串接：
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

- [x] T065 [P] [US5] 在 `tests/unit/core/test_state_machine_end_cancel.py` 測試：
  - `Scenario: US5-AS1`：在 `RESULT_FINAL` 結束後為 `ENDED`，`unsolved_questions` 含第 3 題。
  - `Scenario: US5-AS3`：在 `ROUND_OPEN`、`RESULT_PENDING` 結束時回傳 `STAGE_NOT_ALLOWED`，訊息含「請先關輪並確認定案」。
  - `Scenario: US5-AS4` （C8）：在 `PREPARING` 取消後為 `CANCELLED`，之後任何操作都被拒。
  - `Scenario: US5-AS5`：`ENDED` 時加入被拒，`accepts_submission` 為 `False`。
  - `Scenario: US5-AS6`：在 `PREPARING` 送 `EndActivity` 被拒，訊息為「準備中只能取消活動」。
- [x] T066 [P] [US5] 在 `tests/integration/test_us5_end_cancel.py` 以 HTTP 加 WebSocket 測試 `Scenario: US5-AS1`～`US5-AS6`：
  - AS1：所有頁面的快照都有 `unsolvedQuestions`。
  - `Scenario: US5-AS2`：`export_view` 在 `ENDED` 時可以使用，未成功題標示為未成功。
  - AS4 （C8）：在 `CANCELLED` 時呼叫 `export_view`，回傳 `STAGE_NOT_ALLOWED`。

### Implementation for User Story 5

- [x] T067 [US5] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `EndActivity`（只允許 `RESULT_FINAL`）與 `CancelActivity`（只允許 `PREPARING`，alignment 2026-11-23 C8）；`snapshot_view.py` 在 `ENDED` 時填入 `unsolvedQuestions`。
- [x] T068 [US5] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `end(code, requester)`、`cancel(code, requester)`：兩者都呼叫 `scheduler.cancel`。
  - 給 005 的 `export_view(code, requester)`：只限老師，`CANCELLED` 時拒絕（alignment 2026-11-23 C8）。
- [x] T069 [US5] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/end`（回傳 `unsolvedQuestions`）與 `POST /activities/{code}/cancel`。
- [x] T070 [US5] **轉接層**：在 `teacher.html`、`teacher.js`、`student.html`、`student.js` 加入：
  - 「結束活動」按鈕：只在已定案時可按。
  - 「取消活動」按鈕：只在準備中顯示。
  - 已結束畫面：顯示未成功題清單。
  - 已取消畫面：學生顯示「活動已取消」，不顯示匯出入口。

**Checkpoint**: 完整生命週期（含收尾）都可以運作

---

## Phase 9: User Story 7 - 學生改正選錯的組別，老師清除多建的空組 (Priority: P2)

**Goal**: 非搶答中可以離開本組並改加入其他組；老師可以刪除沒有提交紀錄的組別

**Independent Test**: 準備中離開並加入正確組別；搶答中離開被拒；刪除空組成功；刪除有提交紀錄的組被拒

### Tests for User Story 7 (REQUIRED) ⚠️

- [x] T071 [P] [US7] 在 `tests/unit/core/test_state_machine_group_correction.py` 測試（alignment 2026-11-23 B4、B5）：
  - `Scenario: US7-AS1`：在 `PREPARING`、`RESULT_PENDING`、`RESULT_FINAL` 執行 `LeaveGroup`，只移除該裝置；組別、其他裝置與 `success_count` 不變。
  - `Scenario: US7-AS2`：離開後可以加入另一組。
  - `Scenario: US7-AS3`：在 `ROUND_OPEN` 離開時回傳 `NO_GROUP_SWITCH_DURING_ROUND`。
  - `Scenario: US7-AS4`：原組的 `has_submissions` 在裝置離開後仍為 `True`。
  - `Scenario: US7-AS5`：刪除 `has_submissions=False` 的組時，移除組與其所有裝置，組號可以再使用（再次加入時建立新組與新憑證）。
  - 另外測試：刪除不存在的組號回傳 `GROUP_NOT_FOUND`；`Anonymous` 或不在任何組的裝置離開時回傳 `NOT_IN_GROUP`；學生刪除組別回傳 `NOT_TEACHER`。
  - `Scenario: US7-AS6`：刪除 `has_submissions=True` 的組時回傳 `GROUP_HAS_SUBMISSIONS`，`activity` 不變。
  - 另外測試：`MarkGroupSubmitted` 只在 `ROUND_OPEN` 時生效。
- [x] T072 [P] [US7] 在 `tests/integration/test_us7_group_correction.py` 以 HTTP 加 WebSocket 測試 `Scenario: US7-AS1`～`US7-AS6`：
  - 離開時，該裝置的 WebSocket 收到 `unauthorized`、`reason == "LEFT_GROUP"`。
  - 刪除組別時，原組裝置收到 `reason == "GROUP_DELETED"`。
  - 在 `ROUND_OPEN` 刪除空組成功。
  - 「刪除」與 `mark_group_submitted` 同時發生時，不會出現「答案已記錄但組別被刪除」。

### Implementation for User Story 7

- [x] T073 [US7] **核心**：在 `src/lecture_quiz/core/activity/state_machine.py` 實作 `LeaveGroup`、`DeleteGroup`、`MarkGroupSubmitted`，允許的階段照 spec「不改變階段的組別操作」表；`LeaveGroup` 在 `ROUND_OPEN` 回傳 `NO_GROUP_SWITCH_DURING_ROUND`；`results.py` 新增 `NOT_IN_GROUP`、`GROUP_NOT_FOUND`。
- [x] T074 [US7] **服務層**：在 `src/lecture_quiz/app/activity/service.py` 實作：
  - `leave_group(code, requester)`。
  - `delete_group(code, requester, number_raw)`：組號交給核心正規化。
  - 給 003 的 `mark_group_submitted(code, group_number)`。
  - 成功後呼叫 `SyncPublisher.disconnect_device`（`ports.py` 的 `SyncPublisher` 新增此方法）。
- [x] T075 [US7] **轉接層**：在 `src/lecture_quiz/adapters/web/http_api.py` 實作 `POST /activities/{code}/groups/leave` 與 `DELETE /activities/{code}/groups/{number}`。
- [x] T076 [US7] **轉接層**：在 `student.html`、`student.js` 加入「離開本組」按鈕（搶答中停用並說明原因）；在 `teacher.html`、`teacher.js` 的組別清單，對 `hasSubmissions == false` 的組顯示「刪除」按鈕。

**Checkpoint**: 全部 User Story 完成

---

## Phase N: Polish & Cross-Cutting Concerns

- [x] T077 [P] 建立 `tests/SCENARIO_MAP.md`：列出 47 個 `USn-ASm` 與對應的測試函式。用 `grep -rn "Scenario:" tests/` 核對沒有遺漏（原則 VI）。
  - 2026-11-23：已建立 `tests/SCENARIO_MAP.md`，47 個 Scenario 全部有對應測試，未對應：無。
- [x] T078 [P] 在 `tests/integration/test_idempotency.py` 測試 SC-004：建立活動、加入組別、開輪各用相同的 `Idempotency-Key` 重送 20 次，重複的活動、組別、輪次數都是 0，每次回應都相同。
  - 2026-11-23：`tests/integration/test_idempotency.py` 通過；三種操作各重送 20 次，重複的活動、組別、輪次數皆為 0。
- [x] T079 [P] 在 `tests/contract/test_error_safety.py` 測試 SC-008：觸發每一種 `RejectionReason`、404、400 `INVALID_REQUEST`、500，確認回應都有中文 `message`，而且不含 `Traceback`、`File "`、`.py`、任何 token、任何憑證。
  - 2026-11-23：`tests/contract/test_error_safety.py` 通過；觸發全部 16 種 RejectionReason、404、400，回應皆含中文訊息且無堆疊追蹤、路徑、token、憑證。500 由 `tests/contract/test_http_common.py` 涵蓋。
- [x] T080 [P] 在 `tests/integration/test_logging.py` 檢查日誌（技術限制 3）：
  - 2026-11-23：`tests/integration/test_logging.py` 通過；完整流程的 log 都是 INFO、不含 token 與憑證；`src/` 沒有 `print(`。
  - 用 `caplog` 擷取一輪完整流程的 log，確認層級是 `INFO`，而且不含任何 `teacherToken`、`deviceToken`、`credential` 的值。
  - 在 `src/` 中用 grep 確認沒有 `print(`。
- [x] T081 執行 `ruff check .`、`ruff format --check .`、`mypy src`，全部通過並記錄結果（憲章 v1.0.1 技術限制 2）。
  - 2026-11-23：`ruff check .` All checks passed；`ruff format --check .` 111 files already formatted；`mypy src` no issues found in 26 source files。
- [x] T082 程式碼與圖表一致性驗證：逐一比對 `diagrams/001-activity-session-*.puml` 的組件、類別、方法名稱、時序與實作（例如 `ActivityService` 的方法、`RejectionReason` 的值）。有差異時，先更新圖表並重新轉出 PNG（原則 II）。
  - 2026-11-23（US1、US3～US6 範圍）：依 jacky0407 決定，以程式碼與 data-model 為準更新類別圖（Command、Identity 只存雜湊、Round／RoundRules 欄位、ActivityService 簽名、ports 與外層實作）、時序圖（onDeadline、openRound／closeRound 參數、publish(activity)）、組件圖（ports、common.py、鎖內去重）並重新轉出 PNG；US2／US7 尚未實作的項目保留在圖上並標「待 US2／US7」，實作後需再驗證一次。
  - 2026-11-23（US2、US7 與 Clarifications 後）：逐一比對類別圖的 `ActivityService`（`create`、`join`、`leaveGroup`、`deleteGroup`、`resolveDevice`、`markGroupSubmitted`）、`ActivityRegistry.findByTeacher`、`SyncPublisher.disconnectDevice`、`InputRules` 三個新方法、`RejectionReason` 16 個值，與程式碼一致；時序圖的建立（C7、組數上限）、加入（組號）、組別更正流程與實作一致。PNG 待 T095 重新產生。
  - 2026-11-23（審查修正後）：類別圖補上 `Activity.revision`、`ActivitySnapshot.revision` 與 WebSocketHub 的推送規則（內容相同不送、並行、1 秒逾時），三張 PNG 已由 T095 在本機重新產生。
- [x] T083 執行 `pytest` 與 `pytest -m perf`，記錄日期、指令，以及通過、失敗、略過的數字；perf 記錄四種操作的最大延遲（原則 VI、品質關卡 4）。
  - 2026-11-23：`pytest` 347 passed、1 deselected、0 failed；`pytest -m perf` 1 passed（老師 + 6 組 × 2 條連線，各 10 次）：開輪最大 7.5 ms、關輪 9.8 ms、定案 2.7 ms、結束 2.9 ms，皆小於 2000 ms。執行環境為雲端 Linux（Python 3.13），Windows 本機需再跑一次。
  - 2026-11-23（Windows 11 本機、Python 3.11.5，含 T096～T101 修正後）：`pytest` 362 passed、1 deselected、0 failed；`pytest -m perf` 1 passed：開輪最大 6.9 ms、關輪 4.8 ms、定案 4.5 ms、結束 5.0 ms。
- [ ] T084 由非實作者依 [quickstart.md](quickstart.md) 的 27 步人工驗證，記錄在 `specs/001-activity-session/verification.md`：日期、每一步的操作與結果、第 8、15、17 步的延遲 ms，以及 SC-005「1 分鐘內兩組加入」、SC-010「30 秒內換組」的實際時間（原則 VI）。
- [x] T085 [P] 指令或流程與文件不同時，更新 `specs/001-activity-session/quickstart.md`；在 `CLAUDE.md` 的「專案現況」補上 build、lint、test 指令與 `src/lecture_quiz` 三層結構（現在已有程式碼）。
  - 2026-11-23：quickstart 已更新為 23 步並改用 `python -m lecture_quiz` 啟動；CLAUDE.md「專案現況」補上 001 結構與組數上限。
- [x] T086 用全新 clone 在乾淨的 venv 重跑安裝與 `pytest`，確認不依賴任何本機未提交的檔案（規章第 9 節）。
  - 2026-11-23：從 GitHub 全新 clone `feature/5-001-activity-session`（`a1c9596`），在乾淨的 venv 以一般安裝 `pip install ".[dev]"`（不加 `-e`）後執行：ruff 通過、mypy 通過、`pytest` 347 passed。一般安裝不會產生含路徑的 `.pth`，適合只跑不改的驗證情境；平常開發仍以可編輯安裝加改 `.pth` 為首選，一般安裝改了 `src/` 後要重新安裝才會生效（三種做法見 `docs/DEVELOPMENT.md`「專案路徑含中文時」，2026-11-23 統一說法）。
- [x] T087 追蹤開發用 seed API 的移除：在 Issue #6（002）留言，註明「002 合併後的第一個 PR 移除 `src/lecture_quiz/adapters/web/dev_seed.py`、`LECTURE_QUIZ_DEV_SEED` 與 `tests/integration/test_dev_seed.py`」。本子功能內不刪除。
  - 2026-11-23：已在 Issue #6 留言（issuecomment-7094090227）。
- [x] T088 確認提案相依的任務狀態：`docs/alignment.md` 2026-11-21 的 6 列已於 2026-11-23 全部獲 OpenSpec 組確認（新增一列決議），結論與提案一致；另依 Clarifications 增加組號、組數上限與 C7，已重跑 clarify → plan → tasks。
- [x] T095 在有 `plantuml.jar` 的環境（本機 Windows）執行 `java -jar plantuml.jar "./diagrams/001-*.puml"`，重新產生三張 PNG 並目視檢查（原則 II；2026-11-23 的 `.puml` 修改是在無法執行 PlantUML 的雲端環境完成）。
  - 2026-11-23：本機 Windows 以 `java -jar plantuml.jar -charset UTF-8 "./diagrams/001-*.puml"` 重新產生三張 PNG，已目視確認內容與 `.puml` 一致。

## 審查修正（PR #15 第二、三次審查，2026-11-23）

- [x] T096 超長組號不得變成 500（第三次審查問題 1；FR-031、SC-008）：`normalize_group_number` 去掉前導零後先比位數再轉整數；`tests/unit/core/test_input_rules_group_number.py` 補 4～100000 位數與全形數字，`tests/contract/test_error_safety.py` 補加入（400）與刪除（404 `GROUP_NOT_FOUND`，依契約 #5）兩個端點。已確認還原修正時測試會失敗。
- [x] T097 去重查表與記錄必須在鎖內，且測試要能抓到回歸（第二、三次審查）：`tests/unit/app/test_idempotency_inside_lock.py` 以會檢查鎖狀態的 registry 驗證 `recall`／`remember`／`recall_create`／`remember_create` 都在鎖內呼叫。已確認把查表搬到鎖外時測試會失敗。
- [x] T098 `mark_group_submitted` 契約（第三次審查問題 3；jacky0407 決定）：`contracts/service-interfaces.md` 規定 003 先標記、成功後才寫入答案，被拒就不寫入；修正原本把保證寫成 001 單方面提供的敘述。
- [x] T099 學生版只推與自己有關的變更（第三次審查問題 2；FR-027、FR-030；jacky0407 決定）：`Activity.version`／`changed_at` 只在學生可見的共同狀態改變時遞增，新增 `revision`（只在老師快照）；WebSocketHub 對每條連線內容相同時不送；`sync.js` 老師快照以 `(version, revision)` 排序。spec FR-027／FR-030、data-model、sync-websocket、http-api 已同步；測試 `tests/unit/core/test_public_version.py`、`tests/integration/test_fr030_student_push.py`，並把 4 個依舊語意的測試改為新語意。
- [x] T100 推送並行與逾時（第二次審查問題 2）：`WebSocketHub.publish` 以 `asyncio.gather` 並行送出，每條連線 `asyncio.wait_for` 1 秒，失敗或逾時只關閉該連線。
- [x] T101 前端連按防護（第二次審查問題 3）：`teacher.js` 的 `teacherAction` 送出期間停用活動區塊所有按鈕並忽略新操作；`student.js` 的「離開本組」送出期間停用。

## T084 人工驗證後的決議（2026-11-23，兩組已同意；EricC430 驗證回報）

- [x] T102 測試先行：`tests/unit/core/test_state_machine_open_joining.py`（26 個測試）涵蓋開放加入、準備中不能加入、空組免憑證、搶答中不能刪除組別、刪除後組號重建與舊憑證失效。
  - 2026-11-23：實作前（`git stash` 暫時移開 `src/` 的修改）執行 `pytest tests/unit/core/test_state_machine_open_joining.py`：1 error（匯入 `OpenJoining` 失敗，測試收集中斷）；實作後 26 passed。
- [x] T103 核心、服務層與 HTTP：`Stage.JOINING`、`OpenJoining` 操作、`JOIN_NOT_OPEN`／`GROUP_DELETE_DURING_ROUND`；加入組別的階段改為開放加入起、組別沒有裝置時免憑證；離開本組與刪除組別、開輪、取消、重新匯入的階段依 spec 調整；`ActivityService.open_joining` 與 `POST /activities/{code}/open-joining`（#12）。
- [x] T104 前端：老師頁新增「開放加入」按鈕（準備中顯示，沒有題目時停用）、開輪面板改在開放加入與結果已定案顯示、取消按鈕在準備中與開放加入顯示、搶答中不顯示「刪除」組別按鈕；學生頁與老師頁加入「開放加入」階段名稱。前端沒有自動化測試，請在 T084 人工驗證。
- [x] T105 既有測試改為先開放加入再加入／開輪（`tests/conftest.py` 新增 `open_joining`、`create_joinable`；`tests/unit/core/helpers.py` 新增 `joining_activity`）；刪除組別的「搶答中並行」測試改為驗證「搶答中一律拒絕刪除、不會產生孤兒答案」；`tests/SCENARIO_MAP.md` 重新掃描（57 個 Scenario，未對應：無）。
- [x] T106 文件同步：spec（FR-008、FR-011、FR-013、FR-025、FR-034、FR-035、新增 FR-038、US8、US2-AS10、US7-AS7、US7-AS8、Clarifications、Traceability）、data-model、contracts（HTTP #12、WebSocket 階段列舉、service-interfaces）、research R11、plan、quickstart（改為 27 步）、類別圖與時序圖的 `.puml`、`docs/alignment.md`（三列 2026-11-23 決議）。
- [ ] T107 重新產生三張 PNG：`.puml` 在 T106 又改過，現有 PNG 落後；需要在有 `plantuml.jar` 的本機 Windows 執行 `java -jar plantuml.jar -charset UTF-8 "./diagrams/001-*.puml"` 並目視確認（原則 II）。T095 的證據對應的是更早的版本。
- [x] T108 Ctrl+C 關機保護（緩解，未在回報者的環境驗證）：`python -m lecture_quiz` 加上 `timeout_graceful_shutdown=3`，最多等 3 秒就取消剩下的連線並退出。EricC430 回報按 Ctrl+C 後後端沒有結束；本機（Windows、Python 3.14、uvicorn 0.54）以 8 條自動重連的 WebSocket 模擬，修改前後都在 0.2 秒內正常結束，所以**無法重現**，這項只是保險，需要 T084 第 26 步在回報者的環境再確認。
- 2026-11-23 驗證（Windows 11、Python 3.14.7；與 T083 的 3.11.5 不同）：`ruff check .` All checks passed；`ruff format --check .` 115 files already formatted；`mypy` Success: no issues found in 26 source files；`pytest` 389 passed、1 deselected；`pytest -m perf` 1 passed。

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
Task: "T030 tests/unit/core/test_input_rules_group_number.py"
Task: "T031 tests/unit/core/test_state_machine_join.py"
Task: "T032 tests/unit/core/test_snapshot_view_groups.py"
Task: "T033 tests/contract/test_http_join.py"
Task: "T034 tests/integration/test_us2_join.py"

# 測試失敗後，核心規則可以先並行實作：
Task: "T035 src/lecture_quiz/core/activity/input_rules.py normalize_group_number"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2（基礎，包含架構測試）→ 單獨 PR 先合併（見下方「共用骨架先合併」）。
2. 依序完成 US1 → US2 → US3 → US4 → US6（全部 P1），每完成一個 Story 就執行該 Story 的整合測試。
3. **STOP and VALIDATE**：完成 P1 後，跑 quickstart 第 1～19、23、25、26 步。

### Incremental Delivery

1. 加上 US5（結束與取消）→ 驗證 quickstart 第 24、27 步。
2. 加上 US7（組別更正，alignment 2026-11-23 B4、B5）→ 驗證 quickstart 第 16、20～22 步。
3. 完成 Polish → 開 PR（`Closes #5`），由 EricC430 審查。

### 共用骨架先合併

- Phase 1 + Phase 2（T001～T022）建立 002～005 都會用到的共用骨架：`pyproject.toml`、三層目錄、`main.py`、`tests/conftest.py`、前端 `api.js`／`sync.js`／`identity.js`。
- 這部分先從 main 開 `chore/5-project-skeleton` 分支，**單獨開 PR**（`Refs #5`，不關閉 Issue），盡快合併到 main。之後 001 的 User Story 與 002～005 都從 main 接續。
- 共用檔案的約定（與 EricC430 協調，見 Issue #5）：

  | 檔案或目錄 | 約定 |
  |---|---|
  | `main.py` | 每個子功能只新增一行，掛自己的 router |
  | `teacher.html`／`student.html` | 每個子功能只新增一個區塊與自己的 `js/<能力>.js` |
  | `pyproject.toml` | 相依追加在列表最後 |
  | 程式碼 | 放在自己的 `core/<能力>/`、`app/<能力>/`、`adapters/web/<能力>.py` |

### 分工

- 本子功能（001）全部由 jacky0407 實作。
- EricC430 負責審查 PR，並執行 T084 的人工驗證（規章 2.2、第 9 節：人工驗證必須由非實作者執行）。

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- 每個 Story 都可以單獨完成與測試
- 實作前先確認測試是失敗的
- 每完成一個任務或一組相關任務就 commit，訊息格式 `<type>: <summary>`，附 `Refs #5`
- 避免：模糊的任務、多個任務同時改同一個檔案造成衝突、破壞 Story 獨立性的跨 Story 相依
