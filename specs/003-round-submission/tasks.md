---

description: "003-round-submission 任務清單"
---

# Tasks: 多題搶答與送出

**Input**: Design documents from `/specs/003-round-submission/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（憲章原則 VI）。每個 Acceptance Scenario 與對應的 OpenSpec Scenario 至少一個自動化測試；測試函式 docstring 第一行寫 `Scenario: USn-ASm`（與 001 相同慣例，供 `tests/SCENARIO_MAP.md` 掃描）。**先寫測試、執行並確認失敗，再實作**。003 不呼叫 Google。

**Diagrams**: REQUIRED（憲章原則 II）。`diagrams/003-round-submission-{component,class,sequence}.puml` 與 PNG 已存在（plan 2026-11-23 版）；Polish 有一致性驗證任務。

**Architecture**: REQUIRED（NON-NEGOTIABLE）。`src/lecture_quiz/core/round_submission/` 只匯入標準函式庫與 `lecture_quiz.core`，不讀時鐘；`now` 由 001 在鎖內取得後傳入，接收序號取自 `SubmissionLedger.next_sequence`。

**慣例**：路徑以 repo 根目錄為準；`<core>` = `src/lecture_quiz/core/round_submission`，`<app>` = `src/lecture_quiz/app/round_submission`，`<web>` = `src/lecture_quiz/adapters/web`，`<static>` = `src/lecture_quiz/adapters/static`。每個公開類別、函式、方法都要有型別提示與 Google docstring。日誌只用 `logging`，不記 token 與答案內容。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行（不同檔案、沒有未完成的相依）
- **[Story]**: 所屬 User Story（US1～US6）

---

## Phase 1: Setup

**Purpose**: 建立目錄、確認基準

- [ ] T001 建立套件目錄與空的 `__init__.py`（含模組 docstring）：`<core>/__init__.py`、`<app>/__init__.py`、`tests/unit/core/round_submission/__init__.py`、`tests/unit/app/round_submission/__init__.py`
- [ ] T002 記錄基準：在目前分支執行 `ruff check .`、`ruff format --check .`、`mypy`、`pytest`，把通過數（預期 001 合併後為 389 passed、1 deselected）寫入 `specs/003-round-submission/verification.md` 的「基準」段落，作為 Foundational 之後「001 既有測試全過」的比對依據
- [ ] T003 [P] 在 `tests/unit/core/round_submission/helpers.py` 建立測試資料：`LAYOUT_A = {1: 2, 2: 2, 3: 1, 4: 1}`（課程範本：4 題、前兩題各兩格）、`LAYOUT_B = {1: 1, 2: 3, 3: 1, 4: 2, 5: 1}`（另一份版面：5 題、含三格題組），以及 `make_context(...)`、`make_attempt(...)`、`make_submission(...)` 工廠函式（憲章原則 III 的兩份版面）
- [ ] T004 [P] 在 `tests/conftest.py` 新增 003 共用工具：`FakeQuestionShapeSource`（可設定每個活動代碼的格數）、`submit(client, code, device_token, round_number, question_number, answers)` 呼叫 `POST /api/activities/{code}/submissions`、`seed_questions` 增加可選參數 `blanks: list[int] | None`；在模組 docstring 的 fixture 清單補上這些項目

---

## Phase 2: Foundational（001 擴充、核心資料結構、組裝）

**Purpose**: 研究 R1、R2、R4、R6 的基礎；完成前不能開始任何 User Story

**⚠️ CRITICAL**: 本階段改到已合併的 001，完成後 001 既有測試必須全部通過且不需修改

### 測試（先寫、確認失敗）

- [ ] T005 [P] 在 `tests/unit/core/test_state_machine_record_submission.py` 測試 001 新指令 `RecordSubmission`（與 `MarkGroupSubmitted` 相同，不檢查 actor：只由服務層以 `System()` 送出，沒有 HTTP 入口）：只在 `ROUND_OPEN` 成功，其他 6 個階段回 `STAGE_NOT_ALLOWED`；有截止時間時 `now < deadline` 成功、`now == deadline` 與之後拒絕（`STAGE_NOT_ALLOWED`），沒有截止時間時成功；組別不存在回 `GROUP_NOT_FOUND`；成功時 `has_submissions = True`，**每次都 `changed`**：第二次對同組套用 `revision` 仍加 1，`version` 與 `changed_at` 都不變（研究 R2、R5）
- [ ] T006 [P] 在 `tests/unit/app/test_record_submission.py` 測試 `ActivityService.record_submission(code, device_token, handler)`：活動不存在回 `ACTIVITY_GONE`、token 無效回 `NOT_IN_GROUP`，兩者都不呼叫 `handler.decide`；`clock.now()` 只呼叫一次，且同一個值傳給 `decide`；`SubmissionWindow.accepting` 在搶答中且 `now < deadline`（或無截止）時為真、其他情況為假；`decide` 回 `accept` → 先套用 `RecordSubmission` 再呼叫 `commit`，`commit` 被呼叫時活動鎖仍被持有（仿 `tests/unit/app/test_idempotency_inside_lock.py` 的 LockCheckingRegistry），鎖釋放後 `publish` 恰好一次；`no_change` → 不呼叫 `commit`、不推送、`revision` 不變，`Outcome.ok` 為真且 `value` 為 handler 給的值；`RecordSubmission` 被拒（例如 FakeClock 讓截止時間在 window 組成後才到 —— 以 handler 內推進 FakeClock 的方式模擬不了時，直接構造截止已過的活動並讓 handler 強制回 `accept`）→ 不呼叫 `commit`，回傳拒絕
- [ ] T007 [P] 在 `tests/unit/app/test_snapshot_extension.py` 測試快照擴充：未註冊時 `snapshot_for` 的結果與改動前完全相同；註冊後老師（`TeacherViewer`）與學生（`GroupViewer(n)`）的快照 `extra` 包含擴充回傳的欄位；擴充可覆寫 001 欄位；`snapshot()` 與 `WebSocketHub` 推送都經過擴充（以 TestClient WebSocket 收到的訊息驗證）；身分無效時仍回 `None`、不呼叫擴充
- [ ] T008 [P] 在 `tests/unit/core/round_submission/test_models.py` 測試 `SubmissionLedger`：空 ledger `next_sequence == 1`；`with_added` 回傳新物件、原物件不變、`next_sequence + 1`；`find(round, question, group)` 找得到／找不到；`for_round` 只回該輪；所有型別 frozen（指定屬性拋 `FrozenInstanceError`）
- [ ] T009 [P] 在 `tests/unit/app/round_submission/test_store.py` 測試 `SubmissionStore`：未知代碼回空 ledger；`put` 後 `get` 取回同一物件；不同活動互不影響

### 001 擴充實作

- [ ] T010 在 `src/lecture_quiz/core/activity/commands.py` 新增 `RecordSubmission(actor: Actor, group_number: int)`（docstring 說明只給 003、每次都算變更），加入 `Command` 聯集；在 `src/lecture_quiz/core/activity/state_machine.py` 新增 `_record_submission`：允許階段 `frozenset({Stage.ROUND_OPEN})`、有截止時間時 `ActivityStateMachine.is_deadline_passed(current, now)` 為真就拒絕（`STAGE_NOT_ALLOWED`）、組別不存在 `GROUP_NOT_FOUND`、否則 `has_submissions = True` 並一律回 `_changed`；在 `describe_rejection` 若需要補 `RecordSubmission` 的訊息。不改 `MarkGroupSubmitted`（依賴 T005）
- [ ] T011 在 `src/lecture_quiz/app/activity/ports.py` 新增：`SubmissionWindow`（frozen：`group_number: int`、`stage: Stage`、`round_number: int | None`、`open_questions: tuple[int, ...]`、`deadline: datetime | None`、`accepting: bool`）；`HandlerStep[T]`（`kind: Literal["accept", "no_change"]`、`value: T`，附 `accept(value)`／`no_change(value)` 建構函式；003 的拒絕也用 `no_change` 回傳，拒絕原因在 `value` 裡）；`SubmissionHandler[T]` Protocol（`decide(window, now) -> HandlerStep[T]`、`commit() -> None`）；`TeacherViewer`、`GroupViewer(group_number)`、`Viewer` 聯集；`SnapshotExtension` Protocol（`__call__(activity, viewer) -> Mapping[str, object]`）。**不修改** `Outcome`（001 HTTP 層 `unwrap()` 直接使用 `rejection.http_status`，放寬型別會讓 mypy 失敗）
- [ ] T012 在 `src/lecture_quiz/app/activity/service.py` 實作 `record_submission(code, device_token, handler)`（研究 R2 步驟 1～7；鎖內順序：找裝置 → `now = self._clock.now()` → 組 `SubmissionWindow` → `handler.decide` → `accept` 時以 `ActivityStateMachine.apply(activity, RecordSubmission(System(), group), now, None)` 套用並 `registry.put` → `handler.commit()`；鎖外 `_publish`）、`add_snapshot_extension(ext)`，並把 `snapshot_for` 改為實例方法（先呼叫 `SnapshotView`，再依序併入擴充欄位）；同步修改 `snapshot()` 與所有呼叫點（依賴 T010、T011）
- [ ] T013 在 `src/lecture_quiz/adapters/web/ws_sync.py` 的 `_push` 改為 `self._service.snapshot_for(activity, conn.requester)`（`_service` 為 `None` 時直接 return 並記 WARNING）（依賴 T012）
- [ ] T014 執行 `pytest`：T005～T007 通過，001 既有測試**不修改**全部通過；把結果數字補進 `verification.md`。若有 001 測試因 `snapshot_for` 改為實例方法而失敗，只調整呼叫方式，不得改斷言，並在 verification.md 列出

### 003 核心資料結構與應用層骨架

- [ ] T015 [P] 在 `<core>/models.py` 建立 frozen 型別（欄位照 data-model.md）：`Submission(activity_code, round_number, question_number, group_number, answers: tuple[str, ...], received_at: datetime, sequence: int)`、`SubmissionAttempt(round_number_raw: object, question_number_raw: object, answers_raw: object)`、`RoundContext(group_number, round_number: int | None, open_questions: tuple[int, ...], accepting: bool, blanks_per_question: Mapping[int, int])`（`blanks_per_question` 以 `MappingProxyType` 凍結）、`SubmissionLedger(submissions: tuple[Submission, ...] = (), next_sequence: int = 1)` 與 `find`／`for_round`／`with_added`（依賴 T008）
- [ ] T016 [P] 在 `<core>/rules.py` 先建立 `DecisionKind`（`ACCEPTED`、`ALREADY_SUBMITTED`、`REJECTED`）、`SubmissionRejection`（`StrEnum`：`ACTIVITY_GONE`、`NOT_IN_GROUP`、`STALE_ROUND`、`ROUND_CLOSED`、`QUESTION_NOT_OPEN`、`INVALID_ANSWER`、`WRONG_BLANK_COUNT`、`BLANK_EMPTY`、`ANSWER_TOO_LONG`，各自的 `http_status` 依 data-model.md「判定順序」表：410、403、409、409、400、400、400、400、400）、`SubmissionDecision(kind, submission, rejection, blank_numbers: tuple[int, ...] = (), expected_blanks: int | None = None)`；`decide` 先留 `NotImplementedError`（US1 起逐步完成）
- [ ] T017 [P] 在 `<app>/ports.py` 定義 `QuestionShapeSource`（`blanks_per_question(code) -> Mapping[int, int] | None`）與 `SubmissionReader`（`round_submissions(code, round_number)`、`all_submissions(code)`）Protocol，以及 `NullQuestionShapeSource`（一律回 `None`；002 合併前、非 dev seed 時使用）；在 `<app>/store.py` 實作 `SubmissionStore`（依賴 T009、T015）
- [ ] T018 擴充 dev seed（研究 R6）：`<web>/dev_seed.py` 的 `SeedBody` 新增可選 `blanks: list[StrictInt] | None`（長度必須等於 `count`，每個值 1～10，否則 400 `INVALID_REQUEST`）；新增 `DevQuestionShapeSource`（記憶體 dict：代碼 → 題號 → 格數；沒給 `blanks` 時每題 1 格），seed 成功後寫入；在 `tests/integration/test_dev_seed.py` 補測試：有／沒有 `blanks`、長度不符、值超出範圍。檔頭註解註明 002 合併後連同 `DevQuestionShapeSource` 一起移除
- [ ] T019 在 `<app>/service.py` 建立 `SubmissionService.__init__(activity_service, store, shapes: QuestionShapeSource)`：建構時呼叫 `activity_service.add_snapshot_extension(self.snapshot_extension)`；`snapshot_extension` 先回傳空 dict（US4、US5 完成）；在 `src/lecture_quiz/main.py` 組裝：`app.state.question_shape_source` 在 dev seed 啟用時為 `DevQuestionShapeSource`，否則 `NullQuestionShapeSource`；建立 `app.state.submission_service`；在「子功能 router」區塊加 `api.include_router(submission_api.create_router(app))  # 003`（`<web>/submission_api.py` 先建立空 router）（依賴 T012、T017、T018）

**Checkpoint**: 001 擴充完成且 001 測試全過；003 骨架可匯入；`tests/architecture/test_core_is_pure.py` 自動涵蓋 `<core>`

---

## Phase 3: User Story 1 - 學生依任意順序完整提交本輪題目 (Priority: P1) 🎯 MVP

**Goal**: 本輪開放題可依任意順序送出，題組必須填滿所有子空格，無效提交整筆拒絕且不消耗機會

**Independent Test**: 以 LAYOUT_A 建活動、一組加入、開輪，先送題 2 再送題 1；送一筆少一格的題組；檢查接受、拒絕與剩餘機會

### Tests for User Story 1（先寫、確認失敗）⚠️

- [ ] T020 [P] [US1] 在 `tests/unit/core/round_submission/test_answer_rules.py` 測試 `AnswerRules.check(raw, expected)`（Q-20 提議）：格數不符 → `WRONG_BLANK_COUNT` 且 `expected_blanks == expected`（`Scenario: US1-AS4` ↔ OpenSpec「題組少一格」）；任一格 `strip()` 後為空（含半形空白、全形空白 U+3000、Tab、`\n`）→ `BLANK_EMPTY` 並列出**全部**空格格號（`Scenario: US1-AS3`、`Scenario: US1-AS6`）；`answers_raw` 不是 list、元素不是 str → `INVALID_ANSWER`；恰好 500 字通過、501 字 → `ANSWER_TOO_LONG` 並列出格號；同時有空格與超長時回 `BLANK_EMPTY`；通過時回傳**原文**（保留首尾空白與換行）；`MAX_ANSWER_CHARS == 500` 為模組常數
- [ ] T021 [P] [US1] 在 `tests/unit/core/round_submission/test_decide_us1.py` 測試 `SubmissionRules.decide`：LAYOUT_A 開放題 1、2，先送題 2 再送題 1 都 `ACCEPTED`，序號 1、2（`Scenario: US1-AS1` ↔ OpenSpec「不同順序作答」）；只送其中兩題，其餘仍可送（`Scenario: US1-AS2`）；送本輪未開放的題 3 與不存在的題 99 → `QUESTION_NOT_OPEN`，ledger 不變（`Scenario: US1-AS5`）；題號不是整數 → `QUESTION_NOT_OPEN`；被拒後同題再送完整答案 → `ACCEPTED`（不消耗機會，FR-005）；內容明顯錯誤但非空 → `ACCEPTED` 且原文保存（`Scenario: US1-AS7`）；LAYOUT_B 題 2 需要 3 格：送 2 格 → `WRONG_BLANK_COUNT`、送 3 格 → `ACCEPTED`（原則 III、SC-009）；開放題查不到格數 → `QUESTION_NOT_OPEN`
- [ ] T022 [P] [US1] 在 `tests/unit/app/round_submission/test_submit_us1.py` 以真的 `ActivityService` + `FakeClock` + `FakeQuestionShapeSource` 測試 `SubmissionService.submit`：接受後 store 有該筆、`received_at == fake_clock.now()`、老師快照 `revision` 加 1、`version` 不變；被拒時 store、`next_sequence`、`revision`、`version` 都不變且沒有推送（FR-005）
- [ ] T023 [P] [US1] 在 `tests/contract/test_http_submissions.py` 測試 `POST /api/activities/{code}/submissions`：接受回 `201 {"result": "accepted", "submission": {roundNumber, questionNumber, groupNumber, answers, receivedAt}}`，回應不含 `sequence`；`WRONG_BLANK_COUNT`／`BLANK_EMPTY`／`ANSWER_TOO_LONG`／`QUESTION_NOT_OPEN`／`INVALID_ANSWER` 回 400 與 `{"error": {"code", "message"}}`，訊息分別含「需要 k 格」「第 i 格尚未填寫」「第 i 格超過 500 字」「不在本輪」；本文不是 JSON 物件或缺欄位 → 400 `INVALID_REQUEST`；裝置 token 無效、未帶 token、改用**老師 token** 送出 → `403 NOT_IN_GROUP`；後端重啟後（活動不存在）帶舊 token 送出 → `410 ACTIVITY_GONE`（Edge Cases「不是學生裝置的請求」「活動已失效」）；錯誤回應不含 token、`Traceback`、檔案路徑（FR-034、SC-007）

### Implementation for User Story 1

- [ ] T024 [US1] 在 `<core>/answer_rules.py` 實作 `MAX_ANSWER_CHARS = 500` 與 `AnswerRules.check(raw, expected) -> tuple[str, ...]`，失敗時拋 `InvalidAnswerError(rejection, blank_numbers, expected_blanks)`（規則照 T020 與 research R8；docstring 註明 Q-20 為 SpecKit 組提議、待 OpenSpec 確認）（依賴 T020）
- [ ] T025 [US1] 在 `<core>/rules.py` 實作 `SubmissionRules.decide(ledger, context, code, attempt, now)` 的步驟 3（題號）、5（`AnswerRules`）、6（接受：`Submission(..., received_at=now, sequence=ledger.next_sequence)`）；步驟 1、2、4 先以「一律通過」的位置保留並加 `# US2／US3 完成` 註解（依賴 T021、T024）
- [ ] T026 [US1] 在 `<app>/service.py` 實作 `submit(code, device_token, attempt) -> Outcome[SubmissionDecision]`：建立 `_SubmitHandler`（`decide`：讀 `store.get(code)`、以 `shapes.blanks_per_question(code)` 與 window 組 `RoundContext`、呼叫 `SubmissionRules.decide`、把結果轉成 `HandlerStep`：`ACCEPTED` → `accept(decision)`，`ALREADY_SUBMITTED` 與 `REJECTED` → `no_change(decision)`；`commit`：`store.put(code, ledger.with_added(sub))`），呼叫 `activity_service.record_submission`；`record_submission` 回傳 `ok=False` 時（001 的 `ACTIVITY_GONE`、`NOT_IN_GROUP`）轉成 `SubmissionDecision(kind=REJECTED, rejection=SubmissionRejection 同名值)`，讓 `submit` 一律回傳 `Outcome(ok=True, value=decision)`；INFO 日誌 `activity round question group result`，不含 token 與答案（研究 R13）（依賴 T022、T025）
- [ ] T027 [US1] 在 `<web>/submission_api.py` 實作 `POST /activities/{code}/submissions`：pydantic 本文 `SubmitBody`（`model_config = ConfigDict(extra="ignore")`；`roundNumber`、`questionNumber`、`answers` 型別為 `object`，原樣交給核心）；以 001 `http_api` 的 `Token` 依賴取得 bearer token；接受回 201、拒絕以 `ApiError(status, code, message)` 拋出；`annotate_request_log(request, result=...)`（依賴 T023、T026）
- [ ] T028 [US1] 前端作答表單：新增 `<static>/js/submission.js`，匯出 `renderAnswerForm(container, questionNumber, blanks, onSubmit)`（每格一個 `<textarea>`、標示「第 i 格」、`maxlength=500` 只是提示）、`describeSubmitError(error)`；`<static>/js/student.js` 在 `ROUND_OPEN` 時依快照的 `openQuestions` 與 `questionShapes` 畫出每題表單，送出時呼叫 `api.js` 的 POST；**一律用 `textContent`／`createElement`，不得使用 `innerHTML`**；`<static>/student.html` 加作答區塊容器。以 `node --check` 檢查語法

**Checkpoint**: 學生可依任意順序送出完整答案，無效提交被拒且不消耗機會

---

## Phase 4: User Story 2 - 每組每題每輪只算第一筆 (Priority: P1)

**Goal**: 同組多裝置、重送都只保存第一筆；下一輪同題重新給機會

**Independent Test**: 同組兩裝置同時送同題；接受後重送；定案後下一輪再送同題

### Tests for User Story 2（先寫、確認失敗）⚠️

- [ ] T029 [P] [US2] 在 `tests/unit/core/round_submission/test_decide_us2.py` 測試：本組本輪本題已有提交時，不論內容是否有效都回 `ALREADY_SUBMITTED` 並附既有提交、ledger 不變（`Scenario: US2-AS4`）；先無效被拒、再有效 → `ACCEPTED`（`Scenario: US2-AS5`）；第 1 輪已提交題 1、第 2 輪題 1 再開 → `ACCEPTED`，第 1 輪紀錄不變（`Scenario: US2-AS3` ↔ OpenSpec「下一輪重新作答」）；他組同題不受影響
- [ ] T030 [P] [US2] 在 `tests/unit/app/round_submission/test_submit_concurrency.py` 測試：同組兩台裝置以 `asyncio.gather` 同時送同題不同答案，重複 50 次（每次新活動），每次 store 只有 1 筆、另一個結果為 `ALREADY_SUBMITTED` 且附的答案等於被保存的那筆（`Scenario: US2-AS1` ↔ OpenSpec「同組兩裝置競爭」；SC-002）；接受後以相同與不同內容各重送 10 次，筆數維持 1、回傳的 `received_at` 與 `sequence` 與原提交相同（`Scenario: US2-AS2` ↔ OpenSpec「回應遺失後重送」；SC-003）
- [ ] T031 [P] [US2] 在 `tests/integration/test_us2_submission_once.py` 測試：HTTP 重送回 `200 {"result": "alreadySubmitted", "submission": 原提交}`；同組另一台裝置的 WebSocket 收到含該答案的快照（`Scenario: US2-AS1`）；第 1 輪提交後關輪、定案、該學生離開本組並加入另一組 → 第 1 輪公開資料中該提交仍屬原組（`Scenario: US2-AS6`）；老師刪除有提交的組 → `409 GROUP_HAS_SUBMISSIONS`，搶答中刪除任何組 → `409`（001 拒絕），提交紀錄不變（`Scenario: US2-AS7`）

### Implementation for User Story 2

- [ ] T032 [US2] 在 `<core>/rules.py` 完成 `decide` 步驟 4：`ledger.find(round, question, group)` 存在時回 `ALREADY_SUBMITTED`（位置在題號檢查之後、內容檢查之前，研究 R10）（依賴 T029）
- [ ] T033 [US2] 在 `<app>/service.py` 的 handler 對 `ALREADY_SUBMITTED` 回 `HandlerStep.no_change(decision)`；`<web>/submission_api.py` 對它回 `200 {"result": "alreadySubmitted", ...}`；日誌 `result=alreadySubmitted`（依賴 T030、T031、T032）
- [ ] T034 [US2] 前端：`<static>/js/submission.js` 對 `alreadySubmitted` 顯示「本組已送出」與既有答案（`textContent`），該題表單改為唯讀；`student.js` 收到快照中本組已送出的題目時同樣改為唯讀並顯示答案

**Checkpoint**: 每組每題每輪只有一筆

---

## Phase 5: User Story 3 - 截止與接收順序由後端決定 (Priority: P1)

**Goal**: 嚴格早於截止才接受；關輪後拒絕；舊輪次拒絕；接收時間與序號由後端產生，排序確定

**Independent Test**: FakeClock 控制截止邊界；關輪後送；舊輪次送；同時間戳兩組排序；關輪與提交競態

### Tests for User Story 3（先寫、確認失敗）⚠️

- [ ] T035 [P] [US3] 在 `tests/unit/core/round_submission/test_decide_us3.py` 測試：`round_number_raw` 不等於目前輪次或不是整數 → `STALE_ROUND`；目前還沒有任何輪次（準備中、開放加入）→ `ROUND_CLOSED`，訊息為「本輪尚未開始或已結束」（spec Edge Cases「非搶答中提交」）（`Scenario: US3-AS4` ↔ OpenSpec「舊輪次頁面提交」）；輪次相符但 `accepting` 為假 → `ROUND_CLOSED`（`Scenario: US3-AS2`、`Scenario: US3-AS3`）；`STALE_ROUND` 優先於 `ROUND_CLOSED`、`ROUND_CLOSED` 優先於題號與內容檢查；`SubmissionRules.order` 對相同 `received_at` 依 `sequence` 排序，輸入順序打亂結果相同（`Scenario: US3-AS5` ↔ OpenSpec「同時間戳」）
- [ ] T036 [P] [US3] 在 `tests/unit/app/round_submission/test_submit_deadline.py` 以 FakeClock 測試：開輪 60 秒，`deadline - 1ms` 接受、`deadline` 與 `deadline + 1ms` 回 `ROUND_CLOSED` 且不保存（`Scenario: US3-AS1`、`Scenario: US3-AS2` ↔ OpenSpec「截止邊界」；SC-004）；無倒數輪次在老師關輪前一直接受、關輪後 `ROUND_CLOSED`（`Scenario: US3-AS3`）；接收序號跨輪持續遞增、被拒不消耗序號（FR-016）；`received_at` 等於鎖內取得的 `now`
- [ ] T037 [P] [US3] 在 `tests/unit/app/round_submission/test_close_vs_submit.py` 測試關輪與提交以 `asyncio.gather` 同時執行 50 次：每次要嘛提交被保存且關輪後的公開資料包含它，要嘛提交回 `ROUND_CLOSED` 且未保存；不存在「關輪後才保存」的提交（以 store 中每筆的 `received_at < 關輪時間` 且關輪後推送的快照已包含全部保存的提交檢查）（`Scenario: US3-AS6`；FR-019、SC-004）
- [ ] T038 [P] [US3] 在 `tests/contract/test_http_submissions.py` 補：本文多帶 `clientTime`、`receivedAt`、`groupNumber` 欄位時被忽略，`receivedAt` 仍為後端時間、`groupNumber` 仍為 token 所屬組（`Scenario: US3-AS7`）；`STALE_ROUND`、`ROUND_CLOSED` 回 409 且訊息分別含「輪次已更新，請重新整理」「本輪已結束」

### Implementation for User Story 3

- [ ] T039 [US3] 在 `<core>/rules.py` 完成 `decide` 步驟 1（`STALE_ROUND`）與 2（`ROUND_CLOSED`），以及 `SubmissionRules.order(submissions)`（以 `(received_at, sequence)` 排序）；移除 T025 留下的「一律通過」註解（依賴 T035）
- [ ] T040 [US3] 確認 `<app>/service.py` 把 `SubmissionWindow.round_number`、`accepting` 正確轉進 `RoundContext`；`SubmissionReader.round_submissions`／`all_submissions` 以 `order` 回傳排序結果（依賴 T036、T037、T039）
- [ ] T041 [US3] 前端：`submission.js` 對 `STALE_ROUND` 顯示「輪次已更新，請重新整理後再作答」並提供重新整理按鈕，對 `ROUND_CLOSED` 顯示「本輪已結束」並停用全部表單

**Checkpoint**: 截止、關輪、舊輪次與排序都由後端一致判定

---

## Phase 6: User Story 4 - 搶答中只看得到自己組，老師看得到全部 (Priority: P1)

**Goal**: 學生快照只含本組；他組提交不推送給本組；老師看板即時顯示全部與送出先後

**Independent Test**: 甲、乙各提交後，檢查甲組所有可取得的回應與推送，以及老師看板

### Tests for User Story 4（先寫、確認失敗）⚠️

- [ ] T042 [P] [US4] 在 `tests/unit/core/round_submission/test_view_open_round.py` 測試 `SubmissionView`：本輪開放中 `for_group(ledger, activity, 1)` 的 `submissions.current` 只有 `own`（甲組的題號、答案、接收時間），整份序列化結果中找不到乙組組號、答案、時間、提交數或 `order`（`Scenario: US4-AS1` ↔ OpenSpec「檢查學生資料回應」、`Scenario: US4-AS3`）；`questionShapes` 只含本輪開放題；`for_teacher` 每題列出全部已送組、依排序鍵給 `order`（1 起算），沒有任何 `rank`／暫定勝者欄位（`Scenario: US4-AS5`；`TEACHER_SEES_PROVISIONAL_RANKING_DURING_ROUND = False`）；可見性常數 `TEACHER_SEES_PROVISIONAL_RANKING_DURING_ROUND = False`、`STUDENT_SEES_OWN_SUCCESS_DURING_ROUND = True`、`STUDENT_SEES_JUDGED_WRONG = True` 集中在 `<core>/view.py` 頂端
- [ ] T043 [P] [US4] 在 `tests/integration/test_submission_visibility.py` 測試：搶答中乙組提交後，甲組 WebSocket 在 1 秒內沒有收到任何訊息（ping 除外），甲組 `GET /snapshot` 的 `version` 與 `changedAt` 不變、內容找不到乙組資料（`Scenario: US4-AS2` ↔ OpenSpec「檢查學生資料回應」；FR-022、SC-005，仿 `tests/integration/test_fr030_student_push.py`）；甲組快照 `ownGroup.successCount` 照 001 可見（Q-22）；不存在可依組號查詢提交的端點（`GET /api/activities/{code}/submissions`、`GET .../groups/2/submissions` 回 404 或 405）；老師 WebSocket 在提交後收到含該組答案與 `order` 的快照（`Scenario: US4-AS4` ↔ OpenSpec「老師即時看板」）；甲組裝置 A 提交後裝置 B 收到含本組答案的快照（`Scenario: US4-AS6`）

### Implementation for User Story 4

- [ ] T044 [US4] 在 `<core>/view.py` 實作可見性常數與 `SubmissionView.for_teacher(ledger, activity) -> dict`、`for_group(ledger, activity, group_number) -> dict` 的「本輪開放中」部分（JSON 形狀照 `contracts/sync-websocket.md`；時間以 ISO 8601 毫秒輸出）；`STUDENT_SEES_OWN_SUCCESS_DURING_ROUND` 為 `False` 時回傳覆寫 `ownGroup.successCount = None` 的欄位（目前為 `True`，不覆寫）（依賴 T042）
- [ ] T045 [US4] 在 `<app>/service.py` 實作 `snapshot_extension(activity, viewer)`：依 viewer 呼叫 `SubmissionView`，併入 `questionShapes`（老師：全部題；學生：本輪開放題）與 `submissions`（依賴 T043、T044）
- [ ] T046 [US4] 前端：`submission.js` 新增 `renderOwnSubmissions(container, current)` 與 `renderBoard(container, current, groups, questionShapes)`（題 × 組表格：已送出顯示答案、接收時間與送出先後；未送出顯示「尚未送出」；全部 `textContent`）；`teacher.js` 在快照更新時呼叫 `renderBoard`；`student.js` 呼叫 `renderOwnSubmissions`；`teacher.html` 加看板容器

**Checkpoint**: 搶答中可見性正確，老師看板即時更新

---

## Phase 7: User Story 5 - 關輪後公開本輪提交，歷史可查但不洩漏新輪 (Priority: P2)

**Goal**: 關輪後所有人看得到本輪全部提交與先後，無人提交顯示未成功；新一輪仍保密；頁面不被舊版本覆蓋

**Independent Test**: 第 1 輪兩組提交後關輪；定案、開第 2 輪、乙組提交，檢查甲組可見範圍

### Tests for User Story 5（先寫、確認失敗）⚠️

- [ ] T047 [P] [US5] 在 `tests/unit/core/round_submission/test_view_published.py` 測試：關輪（`RESULT_PENDING`）後 `for_group` 的 `published` 包含本輪全部組的提交、答案、`order`（`Scenario: US5-AS1` ↔ OpenSpec「結果公布與後續輪次」）；無人提交的題 `noSubmission: true`（`Scenario: US5-AS2`）；每筆有 `judgedWrong: false`，且 `STUDENT_SEES_JUDGED_WRONG` 為真時學生版也有此欄位（`Scenario: US5-AS5`；Q-26）；第 2 輪開放中，甲組的 `published` 有第 1 輪全部資料、`current` 只有甲組自己的第 2 輪提交（`Scenario: US5-AS3`）
- [ ] T048 [P] [US5] 在 `tests/integration/test_us5_published.py` 測試：關輪後所有學生 WebSocket 收到 `version + 1` 的快照且含公開提交（`Scenario: US5-AS1`）；第 2 輪中乙組提交時甲組收不到訊息、甲組快照仍有第 1 輪公開資料（`Scenario: US5-AS3`）；關輪後的快照 `version` 嚴格大於搶答中的快照，前端 `sync.js` 依 001 規則丟棄較舊版本（`Scenario: US5-AS4` ↔ OpenSpec「延遲回應」；版本遞增在此驗證，前端丟棄行為沿用 001 測試與 quickstart 第 12 步）；`SubmissionReader.round_submissions` 與 `all_submissions` 回傳排序後的不可變 tuple（FR-036）

### Implementation for User Story 5

- [ ] T049 [US5] 在 `<core>/view.py` 實作「已公開輪次」部分（研究 R11：輪次編號小於目前輪次，或等於目前輪次且階段不是 `ROUND_OPEN`）：`published` 依輪次遞增，每題含 `noSubmission`、`entries`（`groupNumber`、`answers`、`receivedAt`、`order`、`judgedWrong`）；`current` 在本輪已關閉時為 `None`（依賴 T047）
- [ ] T050 [US5] 在 `<app>/service.py` 完成 `round_submissions`、`all_submissions`（`SubmissionReader`，給 004、005），擴充函式輸出 `published`（依賴 T048、T049）
- [ ] T051 [US5] 前端：`submission.js` 新增 `renderPublished(container, published)`（每輪每題列出各組答案與先後，`noSubmission` 顯示「未成功」，`judgedWrong` 為真顯示「答錯」，全部 `textContent`；「搶答失敗」需要 004 提供的勝者資訊，004 完成前不顯示，未被判錯的候選只列出先後）；老師頁與學生頁在 `RESULT_PENDING`／`RESULT_FINAL`／`ENDED` 與之後的輪次都顯示歷史

**Checkpoint**: 公開與歷史正確，新輪保密

---

## Phase 8: User Story 6 - 倒數、文字安全與送出狀態清楚可靠 (Priority: P2)

**Goal**: 倒數依後端截止時間；無倒數顯示「由老師結束」；答案以純文字顯示；未確認不顯示成功

**Independent Test**: 含標記的答案、無倒數輪次、送出時斷線

### Tests for User Story 6（先寫、確認失敗）⚠️

- [ ] T052 [P] [US6] 在 `tests/integration/test_us6_safe_display.py` 測試：答案 `<b>粗體</b><script>alert(1)</script>` 被接受，老師與學生快照、HTTP 回應中的答案字串與送出原文完全相同（`Scenario: US6-AS1` ↔ OpenSpec「特殊文字答案」；後端不轉義、不過濾，安全由前端 `textContent` 負責）；無倒數輪次的快照 `deadline` 為 `null`，老師關輪前任何時間（FakeClock 推進 1 小時）都接受提交（`Scenario: US6-AS3` ↔ OpenSpec「無倒數輪次」）；有倒數輪次的快照帶後端 `deadline`（`Scenario: US6-AS2`，前端「歸零後停用送出」另由 T053 靜態檢查與 quickstart 第 15 步驗證，後端拒絕由 T036 驗證）；學生 WebSocket 關閉後，同組另一台裝置提交，再以同一 token 重新連線時，第一份快照就包含該提交（`Scenario: US6-AS5`；FR-033）
- [ ] T053 [P] [US6] 在 `tests/architecture/test_static_text_safety.py` 靜態檢查：`<static>/js/submission.js`、`student.js`、`teacher.js` 不含 `innerHTML`、`outerHTML`、`insertAdjacentHTML`、`document.write`（`Scenario: US6-AS1`；FR-031、SC-008）；`student.js` 的倒數歸零處理會停用作答表單（以字串規則檢查倒數結束的回呼中有停用表單的呼叫）（`Scenario: US6-AS2`）；`submission.js` 只有在 `response.ok` 分支呼叫顯示「已送出」的函式（以字串規則檢查 `已送出` 文字只出現在成功處理函式內）（`Scenario: US6-AS4`；FR-032）

### Implementation for User Story 6

- [ ] T054 [US6] 前端倒數與送出狀態：`student.js` 以 001 `countdown.js` 依快照 `deadline` 顯示倒數，`deadline` 為 `null` 時顯示「由老師結束」，歸零時停用所有作答表單（`Scenario: US6-AS2`、`Scenario: US6-AS3`；FR-029、FR-030）；`submission.js` 送出期間停用按鈕，網路錯誤或逾時顯示「送出結果未確認，請重試」，不顯示「已送出」（`Scenario: US6-AS4`；FR-032）；同步中斷沿用 001 `sync.js` 的「同步中斷」提示，恢復後取得完整快照即顯示最新本組提交（`Scenario: US6-AS5`；FR-033）（依賴 T053）
- [ ] T055 [US6] 執行 `node --check` 檢查 `submission.js`、`student.js`、`teacher.js`；T052、T053 通過

**Checkpoint**: 六個 User Story 都可獨立運作

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T056 [P] 效能：在 `tests/perf/test_submission_latency.py`（`@pytest.mark.perf`）建立老師 + 6 組、每組 2 條 WebSocket 連線，連續 20 次有效提交，量測「HTTP 接受 → 老師收到含該提交的快照」與「→ 同組另一台收到」的延遲，最大值都 < 2000 ms，並輸出最大值（SC-006；沿用 001 `tests/perf/test_sync_latency.py` 的寫法）
- [ ] T057 [P] 日誌：在 `tests/integration/test_submission_logging.py` 以 `caplog` 驗證接受、已送出、各種拒絕時的日誌含 `activity`、`round`、`question`、`group`、`result`，**不含**裝置 token、答案內容（以獨特字串如 `SECRET-ANSWER-字串` 檢查）、`Traceback`（FR-035、研究 R13）
- [ ] T058 [P] 兩份版面：在 `tests/integration/test_two_layouts.py` 以 dev seed 的 `blanks` 分別建立 LAYOUT_A（`[2,2,1,1]`）與 LAYOUT_B（`[1,3,1,2,1]`）兩個活動，各自完成「格數錯誤被拒 → 正確格數接受 → 關輪公開」一次（憲章原則 III、SC-009）
- [ ] T059 更新 `tests/SCENARIO_MAP.md`：標題改為涵蓋 001 與 003，以 docstring `Scenario:` 掃描產生 003 的 US1-AS1～US6-AS5 對照列；確認每個 Scenario（含 13 個 OpenSpec Scenario）至少一個測試，未對應者為「無」（SC-001）
- [ ] T060 程式碼與圖表一致性驗證：逐一比對 `diagrams/003-round-submission-{component,class,sequence}.puml` 與實作（類別名稱、方法簽章、`SubmissionRejection` 值、可見性常數、`record_submission` 鎖內順序）；有差異先改圖並執行 `java -DPLANTUML_LIMIT_SIZE=16384 -jar plantuml.jar "./diagrams/003-*.puml"` 重新轉出 PNG，並目視確認圖未被截斷（憲章原則 II）
- [ ] T061 同步文件：`specs/001-activity-session/contracts/service-interfaces.md` 的「給 003」段落補上 `record_submission`、`add_snapshot_extension`、`snapshot_for` 改為實例方法，並註明 003 以 `record_submission` 取代直接呼叫 `mark_group_submitted`；`docs/DEVELOPMENT.md` 子功能擴充約定補「快照擴充」用法；`CLAUDE.md` 003 段落改為「已實作」
- [ ] T062 執行 `ruff check .`、`ruff format --check .`、`mypy`、`pytest`、`pytest -m perf`，全部通過；把日期、Python 版本、指令與數字（passed／failed／deselected、perf 最大延遲）寫入 `specs/003-round-submission/verification.md`，與 T002 基準比較（憲章原則 VI、技術限制 2）
- [ ] T063 檢查日誌與機敏資料：全文搜尋 `src/` 無 `print(`；日誌不記 token、答案；`git status` 與 `git diff --staged` 無 `.env`、憑證、`.venv`、課程說明或提案草稿（憲章技術限制 3、原則 V）
- [ ] T064 非實作者人工驗證：EricC430 依 `quickstart.md` 17 步操作，記錄日期、操作、實際結果與通過／失敗到 `verification.md`（憲章原則 VI）
- [ ] T065 真實路徑驗證（**002 合併後**）：002 的 `ImportService` 實作 `QuestionShapeSource` 並在 `main.py` 取代 `DevQuestionShapeSource`／`NullQuestionShapeSource`；以兩份真實 Google 學習單（版面 A：課程範本；版面 B：起始列欄不同、含三格題組）各匯入一次，完成 quickstart「真實路徑驗證」3 步，記錄到 `verification.md`（不貼試算表網址與憑證）（憲章原則 III、VI）
- [x] T066 OpenSpec 核對：OpenSpec 組 2026-11-23 全部同意 Q-20、Q-21、Q-22（修正版）、Q-26 與「答錯／搶答失敗」顯示方式；已更新 `docs/alignment.md`、spec、plan，常數不需修改

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：無相依
- **Foundational（Phase 2）**：依賴 Setup；**擋住所有 User Story**。T005～T009 可平行；T010 → T011 → T012 → T013 → T014；T015～T018 可與 001 擴充平行；T019 依賴 T012、T017、T018
- **US1（Phase 3）**：依賴 Foundational
- **US2、US3（Phase 4、5）**：依賴 US1 的 `decide` 骨架（T025）與 `submit`（T026）；兩者改 `rules.py` 的不同步驟，建議依序做（同檔案）
- **US4（Phase 6）**：依賴 US1（需要有提交）；可與 US2、US3 平行（不同檔案：`view.py`）
- **US5（Phase 7）**：依賴 US4 的 `view.py`
- **US6（Phase 8）**：依賴 US1、US4 的前端檔案
- **Polish（Phase 9）**：依賴全部 User Story；T065 另外依賴 002 合併；T066 已完成（2026-11-23）

### User Story Dependencies

- US1（P1）：Foundational 之後即可開始，MVP
- US2（P1）、US3（P1）：在 US1 的 `decide` 上補判定步驟
- US4（P1）：在 US1 之後，與 US2／US3 平行
- US5（P2）：在 US4 之後
- US6（P2）：在 US1、US4 之後

### Within Each User Story

- 測試先寫、執行並確認失敗（在 commit 訊息或 `verification.md` 記錄失敗數）
- core（純函式）→ app（服務）→ adapters（HTTP、前端）
- 每個 User Story 完成後執行 `ruff check .`、`mypy`、`pytest`，勾選 tasks、commit、push

### Parallel Opportunities

- Phase 1：T003、T004
- Phase 2：T005～T009（五個測試檔）；T015、T016、T017
- 每個 User Story 的測試任務（標 [P]）
- US2／US3 的測試可與 US4 的測試同時撰寫
- Polish：T056、T057、T058

---

## Parallel Example: User Story 1

```text
# 同時寫 US1 的測試：
Task: "T020 tests/unit/core/round_submission/test_answer_rules.py"
Task: "T021 tests/unit/core/round_submission/test_decide_us1.py"
Task: "T022 tests/unit/app/round_submission/test_submit_us1.py"
Task: "T023 tests/contract/test_http_submissions.py"
```

## Parallel Example: Foundational

```text
Task: "T005 tests/unit/core/test_state_machine_record_submission.py"
Task: "T006 tests/unit/app/test_record_submission.py"
Task: "T007 tests/unit/app/test_snapshot_extension.py"
Task: "T008 tests/unit/core/round_submission/test_models.py"
Task: "T009 tests/unit/app/round_submission/test_store.py"
```

---

## Implementation Strategy

### MVP First（US1）

1. Phase 1 Setup → Phase 2 Foundational（確認 001 測試全過）
2. Phase 3 US1：學生可以送出完整答案
3. **停下驗證**：US1 測試全過、dev seed 手動送出一次

### Incremental Delivery

1. US1 → US2（只算第一筆）→ US3（截止與順序）：提交規則完整
2. US4（可見性與老師看板）→ US5（公開與歷史）：畫面完整
3. US6（倒數與安全顯示）
4. Polish：效能、日誌、兩份版面、SCENARIO_MAP、圖表一致性、人工驗證
5. 002 合併後做 T065（T066 OpenSpec 核對已完成）

### 時程提醒

內部凍結點 2026-11-29 晚上；004、005 依賴 `SubmissionReader`（T050），建議 US1～US5 優先完成並先推上 PR，讓 004 可以開始整合。

---

## Notes

- **交接給 004**：FR-026「所有候選都被判錯 → 顯示未成功」、FR-025 的勝者與「搶答失敗」顯示，都需要 004 的順位與判錯結果；003 只提供 `judgedWrong` 欄位（一律 `false`）、`noSubmission` 與送出先後（`order`）。004 的 tasks 必須涵蓋這些項目
- [P] = 不同檔案且沒有未完成的相依
- 每個 User Story 完成後勾選、commit（`feat:`／`test:`）、push
- 不得為了讓測試通過而修改 001 既有測試的斷言（T014）
- Q-20／21／22／26 的規則只能放在 `<core>/answer_rules.py` 與 `<core>/view.py` 的常數，方便 T066 調整
