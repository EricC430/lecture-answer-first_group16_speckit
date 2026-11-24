---

description: "004-ranking-review 任務清單"
---

# Tasks: 順位計算、判錯重算與定案（Ranking Review）

**Input**: Design documents from `/specs/004-ranking-review/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（憲章原則 VI）。每個 Acceptance Scenario 與對應的 OpenSpec Scenario 至少一個自動化測試；測試函式 docstring 第一行寫 `Scenario: USn-ASm`（與 001、003 相同慣例，供 `tests/SCENARIO_MAP.md` 掃描）。**先寫測試、執行並確認失敗（記錄失敗數），再寫實作。** 004 不呼叫 Google 或任何外部服務；自動化測試完全不用 mock 以外的外部資源。

**Diagrams**: REQUIRED（憲章原則 II）。`diagrams/004-ranking-review-{component,class,sequence}.puml` 與 PNG 已存在（plan 2026-11-24 版）；Polish 有「程式碼與圖表一致性驗證」任務，實作偏離時先改圖。

**Architecture**: REQUIRED（NON-NEGOTIABLE）。`src/lecture_quiz/core/ranking_review/` 只匯入標準函式庫與 `lecture_quiz.core`，不讀時鐘、不匯入 003 的型別；時間資料只來自 `Candidate.received_at`。快照擴充函式必須是同步、無副作用的純讀取（`docs/DEVELOPMENT.md` 3.5，研究 R2）。

**慣例**：路徑以 repo 根目錄為準；`<core>` = `src/lecture_quiz/core/ranking_review`，`<app>` = `src/lecture_quiz/app/ranking_review`，`<web>` = `src/lecture_quiz/adapters/web`，`<static>` = `src/lecture_quiz/adapters/static`。每個公開函式、類別、方法都要有型別提示與 Google 風格 docstring；日誌只用 `logging`，不用 `print`，不記答案內容、token、憑證（FR-032）。

**前置條件**：004 從 main 切出（001、003 已合併）。002 的實作若尚未合併，手動驗證用的題目要在 002 合併後才能真實匯入（T094）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行（不同檔案、沒有未完成的相依）
- **[Story]**: 所屬 User Story（US1～US7）；Setup、Foundational、Polish 不加

---

## Phase 1: Setup

**Purpose**: 建立目錄、確認基準、準備測試資料

- [ ] T001 建立套件目錄與空的 `__init__.py`（含模組 docstring）：`<core>/__init__.py`、`<app>/__init__.py`、`tests/unit/core/ranking_review/__init__.py`、`tests/unit/app/ranking_review/__init__.py`；另建 `specs/004-ranking-review/verification.md` 骨架（標題「基準」「先寫測試的失敗紀錄」「自動化結果」「效能」「人工驗證」「N/A 說明」「問題紀錄」）
- [ ] T002 記錄基準：在目前分支（已合併 main 的 003）執行 `ruff check .`、`ruff format --check .`、`mypy`、`pytest`，把指令與通過／失敗／略過數寫入 `specs/004-ranking-review/verification.md` 的「基準」段落，作為之後「既有測試不退步」的比較依據
- [ ] T003 [P] 在 `tests/unit/core/ranking_review/helpers.py` 建立測試資料與建構函式：`cand(group, question, second, seq)`（以固定起點加 `second` 秒產生 `Candidate`，`seq` 為接收序號）、`inp(...)`（建構 `RankingInput`）、`LAYOUT_A = (1, 2, 3, 4)`（4 題）、`LAYOUT_B = (1, 2, 3, 4, 5)`（5 題，其中題 3 沒有任何提交、題 5 為題組提交），以及 OpenSpec 範例資料：`FAIR_TWO_QUESTIONS`（甲乙基準皆 0，接收順序甲題一、甲題二、乙題一、乙題二）、`CROSS_QUESTION`（甲乙基準皆 0，甲在兩題都先送出，公平模式）
- [ ] T004 [P] 在 `tests/unit/app/ranking_review/conftest.py` 建立服務層測試工具：`FakeSubmissionReader`（實作 `round_submissions(code, round_number)`，回傳預先設定、依（`received_at`, `sequence`）排序的 003 `Submission` tuple）、`RecordingPublisher`（實作 `SyncPublisher.publish`，記錄呼叫次數，並記錄呼叫當下該活動的 004 鎖是否被持有）、`closed_round_env(...)` fixture：以真 `ActivityService` + `FakeClock` + `ManualScheduler` 建立活動、匯入題號、開放加入、組別加入、開輪（可指定 `fair_mode`）、關輪，回傳進入「結果未定案」的活動代碼、老師與各組身分

---

## Phase 2: Foundational（型別、存放區、組裝、定案 helper）

**Purpose**: 所有 User Story 共用的基礎；完成前不能開始任何 User Story

**⚠️ CRITICAL**: 本階段碰到既有測試（定案 helper），完成後 001、003 既有測試必須全部通過且**不修改斷言**

### 測試（先寫、確認失敗）

- [ ] T005 [P] 在 `tests/unit/core/ranking_review/test_models.py` 測試核心型別（`Scenario` 不適用，為共用基礎）：所有型別是 `frozen` dataclass，修改欄位拋 `FrozenInstanceError`；`display_status(rank, wrong)`：被判錯 → `DisplayStatus.WRONG`；名次 1 且未判錯 → `SUCCESS`；名次大於 1 且未判錯 → `FAILED`；`as_final(rankings)`：名次 1 的 `SUCCESS` 改為 `DisplayStatus.CORRECT`，`WRONG`、`FAILED` 不變；`RankingInput` 不變式（data-model）：「同一（題號, 組號）最多一個候選；`sequence` 在所有候選中不重複；每個候選的題號都在 `question_numbers`；`wrong_marks` 的每一項都對應一個候選」，違反時 `recompute` 以 `AssertionError` 拒絕
- [ ] T006 [P] 在 `tests/unit/app/ranking_review/test_store.py` 測試 `ReviewStore`：未知活動 `get` 回 `None`；`put` 後 `get` 取回同一物件；不同活動、不同輪次互不影響；同一活動代碼永遠回同一把 `asyncio.Lock`、不同活動不同把；`drop(code)` 清掉該活動的審閱狀態、鎖與快取；快取鍵含「是否定案」：同（活動, 輪次, 版本, 角色種類）但定案旗標不同時是不同項目，取不到對方的值
- [ ] T007 [P] 在 `tests/unit/app/ranking_review/test_extension_registration.py` 測試：建立 `RankingService` 後，`ActivityService` 恰有一個新增的快照擴充；沒有任何已關輪輪次時擴充回傳空 mapping，快照與未註冊前**完全相同**（既有快照測試不需修改）
- [ ] T008 [P] 在 `tests/contract/test_http_ranking_review_wiring.py` 測試：`create_app()` 之後 `app.state.ranking_service` 是 `RankingService`；`/api` 之下沒有尚未實作的 004 路徑被意外註冊（只有 T051、T069 之後才會有 PUT judgement 與 POST finalize）

### 實作

- [ ] T009 在 `<core>/models.py` 實作型別（逐欄位照 data-model.md「核心」；欄位型別與限制逐字）：`Candidate`（`group_number: int`、`question_number: int`、`received_at: datetime`、`sequence: int`）、`RankingInput`（`question_numbers: tuple[int, ...]`、`fair_mode: bool`、`baseline: Mapping[int, int]`、`candidates: tuple[Candidate, ...]`、`wrong_marks: frozenset[tuple[int, int]]`，元素為（組號, 題號）；`baseline` 沒有的組視為 0）、`WinReason`（`SOLE_CANDIDATE`、`EARLIER_SUBMISSION`、`FEWER_SUCCESSES`、`BACKEND_ORDER`）、`DisplayStatus`（`SUCCESS`＝搶答成功、`CORRECT`＝搶答正確（定案後才有）、`WRONG`、`FAILED`）、`RankEntry`（`group_number: int`、`rank: int | None`、`count_at_processing: int | None`、`reason: WinReason | None`、`wrong: bool`、`display_status: DisplayStatus`；被判錯者 `rank`、`reason` 為 `None`；速度模式 `count_at_processing` 為 `None`）、`QuestionRanking`（`question_number: int`、`entries: tuple[RankEntry, ...]`、`success_group: int | None`；`entries` 先放有名次者再放被判錯者）、`RoundResult`（`order: tuple[int, ...]`、`rankings: tuple[QuestionRanking, ...]`、`group_counts: Mapping[int, int]`、`wins: Mapping[int, int]`）、`display_status()` 函式；全部 `@dataclass(frozen=True)`，集合用 `tuple`／`frozenset`／`MappingProxyType`（依賴 T005 先失敗）
- [ ] T010 [P] 在 `<core>/outcome.py` 實作 `FinalizedResult`（`version: int`、`rankings: tuple[QuestionRanking, ...]`、`final_counts: Mapping[int, int]`、`solved_questions: frozenset[int]`、`success_increments: Mapping[int, int]`；定案時保存，之後只讀）
- [ ] T011 [P] 在 `<core>/review.py` 實作 `ReviewRejection`（`StrEnum`，值與 HTTP 狀態、預設訊息逐項照 research R12：`INVALID_REQUEST` 400、`NOT_TEACHER` 403、`ACTIVITY_NOT_FOUND` 404、`ROUND_NOT_FOUND` 404、`SUBMISSION_NOT_FOUND` 404、`ROUND_STILL_OPEN` 409、`NO_ROUND` 409、`STALE_ROUND` 409、`RESULT_ALREADY_FINAL` 409、`ACTIVITY_CANCELLED` 409、`STALE_RESULT_VERSION` 409、`FINALIZE_REJECTED`（依 001））、`MarkDecision`（`ok: bool`、`changed: bool`、`review: RoundReview | None`、`rejection: ReviewRejection | None`）與 `RoundReview` dataclass（`round_number: int`、`version: int`、`wrong_marks: frozenset[tuple[int, int]]`、`result: RoundResult`、`affected: frozenset[int]`、`replaced: Mapping[int, tuple[int, ...]]`＝題號 → 依判錯順序保存的被替換搶答成功者歷程（最後一位是最近一位；撤銷判錯時移出歷程以「退回上一步」；定案時清空；初始為空）、`finalized: FinalizedResult | None`）；`ReviewRejection` 的訊息不含堆疊、路徑、token
- [ ] T012 在 `<app>/store.py` 實作 `ReviewStore`（記憶體）：`reviews: dict[tuple[str, int], RoundReview]`、每活動一把 `asyncio.Lock`（`lock(code)`）、`cache: dict[tuple[str, int, int, bool, str], JsonDict]`（鍵為（活動代碼, 輪次, 結果版本, **是否定案**, 角色種類）；版本或定案旗標變了就是不同項目。定案不會增加結果版本卻會改變輸出，所以旗標必須在鍵裡）、`get`、`put`、`drop`（依賴 T006）
- [ ] T013 [P] 在 `<app>/ports.py` 定義 `RankingReader`（Protocol，`finalized_rounds(code) -> tuple[FinalizedRound, ...]`）、`FinalizedRound`（`round_number: int`、`result: FinalizedResult`）、`MarkResult`（`changed: bool`、`result_version: int`、`affected_questions: tuple[int, ...]`）、`FinalizeResult`（`version: int`、`result_version: int`、`already_finalized: bool`）；`Outcome` 沿用 001 的型別，服務不拋業務錯誤
- [ ] T014 在 `<app>/service.py` 建立 `RankingService` 骨架：建構子接收 `activity_service`（001）、`submissions: SubmissionReader`（003）、`store: ReviewStore`、`publisher: SyncPublisher`；建構時呼叫 `activity_service.add_snapshot_extension(self.snapshot_extension)`；`snapshot_extension` 先回傳 `{}`；`mark_wrong`、`unmark_wrong`、`finalize`、`finalized_rounds` 先留 `NotImplementedError`；模組 docstring 說明「推送在鎖外、日誌只記輪次／題號／組號／版本」（依賴 T007、T012、T013）
- [ ] T015 在 `<web>/ranking_review.py` 建立 `create_router(app: FastAPI) -> APIRouter`（先回傳空 router，路由由 T051、T069 加入）；在 `src/lecture_quiz/main.py` 新增 `_wire_ranking(app)`（建立 `RankingService(app.state.activity_service, app.state.submission_service, ReviewStore(), app.state.sync_hub)` 並設 `app.state.ranking_service`）與「子功能 router」區塊的**一行** `api.include_router(ranking_review.create_router(app))  # 004`（依賴 T008、T014）
- [ ] T016 在 `tests/conftest.py` 末端新增 helper `finalize_current(client, teacher, code)`：讀 `GET /api/activities/{code}/snapshot`，若有 `ranking.rounds` 取最後一輪的 `resultVersion`，沒有則用 `1`，再 `POST .../rounds/current/finalize`，本文 `{"resultVersion": n}`、帶老師身分。**在 001 空路由尚存（US6 之前）與 004 路由取代後都能運作**（本文多餘欄位會被舊路由忽略）
- [ ] T017 把既有測試中以 HTTP `POST .../rounds/current/finalize` 搭配 `{}` 定案的呼叫改用 `finalize_current`，**只改呼叫方式、不改任何斷言**：`tests/contract/test_http_close_finalize.py`、`tests/integration/test_fr030_student_push.py`、`tests/integration/test_logging.py`、`tests/integration/test_us1_teacher.py`、`tests/integration/test_us4_close_finalize.py`、`tests/integration/test_us5_end_cancel.py`、`tests/integration/test_us5_published.py`、`tests/perf/test_sync_latency.py`、`tests/unit/app/round_submission/test_submit_deadline.py`（先 `grep -rn "finalize" tests/` 確認清單完整；直接呼叫 `ActivityService.finalize` 或狀態機的測試不用改；若某測試的斷言必須改才能通過，停下並記在 verification.md「問題紀錄」，不得悄悄改斷言）
- [ ] T018 執行 `pytest`（含 `tests/architecture/test_core_is_pure.py`，確認它掃到新的 `core/ranking_review/`）：T005～T008 通過，T002 的基準測試全部維持通過；把結果數字寫入 `verification.md`

**Checkpoint**: 型別、存放區、組裝與定案 helper 就緒；001、003 既有測試全部通過

---

## Phase 3: User Story 1 - 以歷史成功次數作為每輪的起點 (Priority: P1) 🎯 MVP 起點

**Goal**: 每輪的基準來自 001 在開輪時保存的各組成功次數；題組只計一次、速度模式成功也計入；沒有紀錄的組視為 0；本輪未定案結果不累加到基準

**Independent Test**: 用 001 的 `finalize(FinalizeOutcome)` 製造先前輪次的成功次數，開下一輪，確認 004 建出的基準；中途加入的組基準為 0

### Tests for User Story 1（先寫、確認失敗）⚠️

- [ ] T019 [P] [US1] 在 `tests/unit/core/ranking_review/test_baseline.py` 測試 `RankingCalculator.initial_counts(baseline, group_numbers)`：回傳基準的複本、傳入的 `baseline` 不被修改；基準沒有的組為 0（`Scenario: US1-AS4`）；基準有、但本輪沒有候選的組保留原值
- [ ] T020 [P] [US1] 在 `tests/unit/app/ranking_review/test_baseline_us1.py` 用真 `ActivityService`、`FakeClock` 測試：第 1 輪速度模式，以 `ActivityService.finalize(code, teacher, FinalizeOutcome(frozenset({1}), {1: 1}))` 模擬「甲組（組號 1）贏得一個三格題組」並定案，開第 2 輪（公平模式）後 `RankingService._build_input` 的 `baseline == {1: 1}`，不是 3（`Scenario: US1-AS1` ↔ OpenSpec「題組與不同模式的累計」）；模擬甲組贏得兩個單題 → 基準為 2（`Scenario: US1-AS2`）
- [ ] T021 [P] [US1] 在同一檔案測試：關輪後（結果未定案）甲組目前是兩題的搶答成功者，查看初始結果與判錯重算多次，`activity.groups[1].success_count` 與 `round.baseline` 都不變，直到定案（`Scenario: US1-AS3`）；乙組在第 2 輪開輪後才加入並提交，其基準以 0 計（`Scenario: US1-AS4`，FR-001）

### Implementation for User Story 1

- [ ] T022 [US1] 在 `<core>/ranking.py` 實作 `RankingCalculator.initial_counts(baseline: Mapping[int, int], group_numbers: Iterable[int]) -> dict[int, int]`（純函式，不修改輸入）
- [ ] T023 [US1] 在 `<app>/service.py` 實作 `_build_input(activity, round_number, submissions, wrong_marks) -> RankingInput`：`question_numbers`、`fair_mode` 取自 `Round.rules`，`baseline` 取自 `Round.baseline`（key 為組號、開輪時保存，重算一律使用這份），`candidates` 由 003 `Submission` 轉出 `Candidate`（只取 `group_number`、`question_number`、`received_at`、`sequence`）；組別、時間、序號一律取自後端資料，不採信任何前端輸入（FR-026）

**Checkpoint**: 基準建構正確，與 001 的成功次數一致

---

## Phase 4: User Story 2 - 速度模式與固定題序 (Priority: P1)

**Goal**: 關輪後每題依接收時間、接收序號排名，最早者為搶答成功者；無候選題顯示「未成功」；題序在關輪時固定、判錯不移動；老師與學生在快照裡取得 `ranking`

**Independent Test**: 三題（含一題無人提交、一題同時間戳）以速度模式計算，核對題序、順位、搶答成功者、理由；把最早提交判錯，題序不動

### Tests for User Story 2（先寫、確認失敗）⚠️

- [ ] T024 [P] [US2] 在 `tests/unit/core/ranking_review/test_order.py` 測試 `QuestionOrder.compute(question_numbers, candidates)`：第 3 題最早提交比第 1 題早、第 2 題無人提交、第 1 題最早提交最晚 → `(3, 1, 2)`（`Scenario: US2-AS1`）；兩個以上題無提交 → 接在後面依題號遞增（`Scenario: US2-AS2`）；用 `LAYOUT_A`、`LAYOUT_B` 各測一次，確認題序不依賴固定題數或題號順序；決定題序的依據不受判錯影響
- [ ] T025 [P] [US2] 在 `tests/unit/core/ranking_review/test_rank_speed.py` 測試速度模式排名：甲在題一、題二都比乙早、公平模式關閉 → 甲是兩題搶答成功者，理由 `EARLIER_SUBMISSION`（`Scenario: US2-AS4` ↔ OpenSpec「同組最快回答兩題」）；三個候選 → 名次 1、2、3，第一名為唯一 `success_group`，其餘 `display_status` 為 `FAILED`（`Scenario: US2-AS5`）；接收時間相同 → 接收序號較小者較早，理由 `BACKEND_ORDER`（`Scenario: US2-AS6`）；基準甲 3、乙 0 且甲較早 → 甲仍是搶答成功者（`Scenario: US2-AS7`）；無候選 → `success_group is None`（未成功）；唯一候選理由 `SOLE_CANDIDATE`；理由規則逐列照 research R9 表（速度模式的列）
- [ ] T026 [P] [US2] 在 `tests/unit/core/ranking_review/test_recompute_speed.py` 測試：決定題序的最早提交被判錯後以**已保存的題序**重算，`result.order` 不變、該組失去該題候選資格、次早的候選成為搶答成功者（`Scenario: US2-AS3` ↔ OpenSpec「最早提交被判錯」）
- [ ] T027 [P] [US2] 在 `tests/unit/app/ranking_review/test_initial_result.py` 測試：關輪後、沒有任何判錯時 `RankingService.review_for(code, round_number)` 以純計算導出版本 1 的結果，**`ReviewStore` 沒有被寫入**（`store.get(...) is None`），連續兩次呼叫結果逐項相同；活動在搶答中時回傳 `None`（研究 R2）
- [ ] T028 [P] [US2] 在 `tests/unit/core/ranking_review/test_view_shapes.py` 測試 `ResultView.for_teacher` 與 `for_student` 的 JSON 形狀逐欄照 `contracts/sync-websocket.md`：結構 `rounds[].{roundNumber, fairMode, resultVersion, final, affectedQuestions, questionOrder, questions[]}`、`questions[].{questionNumber, successGroup, replacedGroup, entries[]}`、`entries[].{groupNumber, rank, judgedWrong, displayStatus}`（有名次者在前、被判錯者在後；`successGroup: null` 的題 `entries` 可為空）；`displayStatus` 為 `SUCCESS`／`WRONG`／`FAILED`，`final=true` 時名次 1 為 `CORRECT`；`replacedGroup` ＝ `replaced` 歷程的最後一位，`final=true` 時兩種角色皆為 `null`，未定案時老師版輸出、學生版只在該題 `successGroup` 不是 `null`（有遞補者）時輸出；**老師版另有**：entry 的 `countAtProcessing`、`reason`，每輪的 `groupCounts`（key 為組號字串），以及每題的 `actions.{judgeGroup, undoGroup}`（`judgeGroup` ＝ 未定案時的 `successGroup`、`undoGroup` ＝ 未定案時的 `replacedGroup`，`final=true` 時皆為 `null`；學生版沒有 `actions`；`Scenario: US4-AS9`、`US4-AS10` 的資料部分，FR-034；把「哪些按鈕要顯示」放進純函式與測試，前端只照 `actions` 顯示）
- [ ] T029 [P] [US2] 在 `tests/integration/test_us2_ranking_snapshot.py` 測試：老師關輪後，老師與學生的 `GET /snapshot` 與 WebSocket 推送在 2 秒內出現 `ranking.rounds[0]`，`resultVersion == 1`、`final == false`；搶答中（`ROUND_OPEN`）兩種身分的快照都**沒有** `ranking` 欄位（`Scenario: US7-AS1` 的第一部分）

### Implementation for User Story 2

- [ ] T030 [US2] 在 `<core>/order.py` 實作 `QuestionOrder.compute(question_numbers, candidates) -> tuple[int, ...]`：每題取該題全部候選（不論是否被判錯）中 `(received_at, sequence)` 最小者為依據，有依據的題依該鍵遞增，沒有任何候選的題接在後面依題號遞增（FR-004）
- [ ] T031 [US2] 在 `<core>/ranking.py` 實作 `RankingCalculator.rank_speed`（未被判錯候選依 `(received_at, sequence)` 排名，被判錯者附在後面、無名次）、理由分類（research R9 表）、`recompute(input, order) -> RoundResult`（速度模式分支；`order` 由呼叫端傳入，不在 `recompute` 內重新計算題序）與 `display_status` 推導；`recompute` 不讀時鐘、不依賴字典順序（FR-017）
- [ ] T032 [US2] 在 `<core>/review.py` 實作 `RoundReview.initial(input: RankingInput) -> RoundReview`（先以 `QuestionOrder.compute` 決定題序一次、呼叫 `recompute`，`version=1`、`affected` 為空、`finalized=None`）
- [ ] T033 [US2] 在 `<core>/view.py` 實作 `ResultView.for_teacher(reviews)` 與 `ResultView.for_student(reviews)`（純函式，依 T028；`final` 由呼叫端傳入；`final=true` 時 `affectedQuestions` 為空、`SUCCESS` 改為 `CORRECT`、`replacedGroup` 為 `null`；`replacedGroup` 的角色差異與老師版 `actions` 見 T028）
- [ ] T034 [US2] 在 `<app>/service.py` 實作 `review_for(code, round_number)`（stored → 否則導出初始結果；搶答中或輪次不存在回 `None`）與 `snapshot_extension(activity, viewer)`：只輸出已關輪輪次（搶答中的目前輪不輸出）、`final` 依 001 階段與輪次判定（階段結果已定案／已結束，或輪次早於目前輪）、老師用 `for_teacher`、學生用 `for_student`；以 `ReviewStore.cache` 對（輪次, 版本, 是否定案, 角色種類）快取序列化結果（定案旗標必須在鍵裡，否則定案後會回傳定案前的舊 JSON）；沒有任何已關輪輪次時回傳空 mapping
- [ ] T035 [US2] 前端老師端：在 `<static>/js/ranking-review-teacher.js` 以 `onTeacherSnapshot` 畫出每輪每題的候選表（名次、組號、答案與送出時間——以（輪次、題號、組號）合併 003 的 `submissions.published` entry、處理當下成功次數、理由、顯示狀態文字「搶答成功」「答錯」「搶答失敗」、整題「未成功」），並顯示活動階段「結果未定案／結果已定案」（FR-031）；所有文字 `textContent`、保留換行；在 `<static>/teacher.html` 只新增一個 `<section id="ranking-review-section" data-feature="004-ranking-review" hidden>` 與一行 `<script type="module" src="js/ranking-review-teacher.js">`（`docs/DEVELOPMENT.md` 約定）
- [ ] T036 [US2] 前端學生端（基本版，US7 再依 FR-036 限縮）：在 `<static>/js/ranking-review.js` 以 `onStudentSnapshot` 畫出本組每題的顯示狀態（組號取自 `ownGroup.number`）；在 `<static>/student.html` 只新增一個 `<section id="ranking-review-student-section" data-feature="004-ranking-review" hidden>` 與一行 script；`textContent` 輸出

**Checkpoint**: 速度模式結果與固定題序正確，老師與學生在關輪後取得 `ranking`

---

## Phase 5: User Story 3 - 公平模式 (Priority: P1)

**Goal**: 從基準出發依固定題序逐題處理，次數少者優先、第一名暫算次數加一；理由與次數反映處理當下

**Independent Test**: 用純資料驗證 OpenSpec 兩個公平 Scenario，再加入基準不同、次數與時間都相同、題組等變體

### Tests for User Story 3（先寫、確認失敗）⚠️

- [ ] T037 [P] [US3] 在 `tests/unit/core/ranking_review/test_rank_fair.py` 用 `FAIR_TWO_QUESTIONS` 測試：題一由甲成功（理由 `EARLIER_SUBMISSION`），題二由乙成功（理由 `FEWER_SUCCESSES`，因處理題二時甲已有本輪暫算 1 次）（`Scenario: US3-AS1` ↔ OpenSpec「公平分配兩題」）；兩候選次數與接收時間皆相同 → 接收序號較小者勝出，理由 `BACKEND_ORDER`（`Scenario: US3-AS2` ↔ OpenSpec「完全同次數與同時間」）；甲基準 1、乙基準 0、兩人在題一提交且甲較早 → 題一由乙成功，理由 `FEWER_SUCCESSES`（`Scenario: US3-AS3`）
- [ ] T038 [P] [US3] 在同一檔案測試：甲在題一成功後處理題二，排名依甲「已是 1」計，題二每個 entry 的 `count_at_processing` 是處理當下的值（`Scenario: US3-AS4`）；候選全部是題組提交、該組成功 → `wins` 與 `group_counts` 只加 1，不按子空格數（`Scenario: US3-AS5`）；某題三個候選只有第一名成功 → 其他候選的暫算次數不變（`Scenario: US3-AS6`）；理由規則逐列照 research R9 表（公平模式的列）
- [ ] T039 [P] [US3] 在 `tests/unit/core/ranking_review/test_fair_layouts.py` 以 `LAYOUT_A`、`LAYOUT_B`（含無提交題、題組）測試：公平模式依**固定題序**而非題號大小處理（例如題序 `(3, 1, 2)` 時先處理題 3），結果不依賴固定題數（憲章原則 III 的「不寫死版面」在 004 的對應驗證）
- [ ] T040 [P] [US3] 在 `tests/integration/test_us3_fair_snapshot.py` 測試：老師開公平模式輪次、三組提交、關輪後，老師快照 entry 含 `countAtProcessing` 與 `reason`、每輪含 `groupCounts`；數字與 `core` 直接計算相同

### Implementation for User Story 3

- [ ] T041 [US3] 在 `<core>/ranking.py` 實作 `RankingCalculator.rank_fair` 與 `recompute` 的公平模式分支：從 `initial_counts` 開始，依傳入的固定題序逐題；候選（未被判錯）依 `(counts[group], received_at, sequence)` 排名；每個候選的 `count_at_processing` 為處理當下的次數；第一名成為 `success_group`、其 `counts` 加 1，其他候選不加；`wins` 為各組本輪成功題數、`group_counts` 為處理完本輪後的暫算次數；一律從基準開始，不使用上一版暫算次數（FR-007、FR-015）
- [ ] T042 [US3] 前端老師端：`ranking-review-teacher.js` 在公平模式輪次顯示每個候選的「處理當下成功次數」與理由文字（`SOLE_CANDIDATE`＝唯一候選、`EARLIER_SUBMISSION`＝提交較早、`FEWER_SUCCESSES`＝成功次數較少、`BACKEND_ORDER`＝以後端接收先後決定），並顯示每輪各組暫算次數；速度模式不顯示次數欄

**Checkpoint**: 速度與公平兩種模式的順位、理由與次數都正確

---

## Phase 6: User Story 4 - 老師判錯與撤銷判錯 (Priority: P1)

**Goal**: 老師在「結果未定案」對任一已接受提交判錯／撤銷；題組整筆；原答案、時間、序號保留；免填原因；各階段與身分的拒絕

**Independent Test**: 關輪後對勝者與非勝者判錯、撤銷，檢查狀態、顯示文字與保留的原始資料；學生、搶答中、不存在的提交都被拒絕

### Tests for User Story 4（先寫、確認失敗）⚠️

- [ ] T043 [P] [US4] 在 `tests/unit/core/ranking_review/test_review_rules_mark.py` 測試 `RoundReviewRules.mark(review, input, group, question, wrong)`：判錯題組整筆提交，該組在該題無名次、`display_status` 為 `WRONG`，候選的 `answers`、`received_at`、`sequence` 沒有被改動（`Scenario: US4-AS1` ↔ OpenSpec「非勝者與題組判錯」、`US4-AS2`）；撤銷後該筆依原接收時間與序號回到原名次（`Scenario: US4-AS3` ↔ OpenSpec「撤銷誤判」）；（組, 題）沒有候選 → `SUBMISSION_NOT_FOUND`（`Scenario: US4-AS6`）；對已判錯者再判錯、對未判錯者撤銷 → `ok=True, changed=False`、版本不變（FR-025）；實際變更 → `version + 1`；`replaced` 歷程：判錯「判錯前是該題 `success_group`」的組別 → 附加到 `replaced[question]` 末端；判錯非搶答成功者 → 歷程不變；撤銷某組 → 從歷程移除（撤銷最近一位即退回上一步，前一位成為最近一位）；連續判錯甲、乙後撤銷兩次：第一次後歷程為 `(甲,)`、搶答成功者回到乙，第二次後歷程為空、搶答成功者回到甲（`Scenario: US4-AS10`、`US7-AS3` 的核心部分）；**不變式**：每次 `mark` 後，`replaced` 歷程中的每一組都必須在該題的 `wrong_marks` 內、且歷程中沒有重複的組（對 `mark`／`unmark` 的任意操作序列以參數化測試驗證）
- [ ] T044 [P] [US4] 在 `tests/unit/app/ranking_review/test_mark_permissions.py` 測試：學生裝置、其他活動的老師、匿名請求判錯／撤銷 → `NOT_TEACHER`，`ReviewStore` 與結果版本不變、`RecordingPublisher` 沒被呼叫、回應不含老師專用資料（`Scenario: US4-AS4`）
- [ ] T045 [P] [US4] 在 `tests/unit/app/ranking_review/test_mark_stages.py` 測試判定順序（data-model「判定規則」表）：活動不存在 `ACTIVITY_NOT_FOUND`；活動已取消 `ACTIVITY_CANCELLED`；還沒有輪次 `NO_ROUND`；輪次編號不存在 `ROUND_NOT_FOUND`；目前輪搶答中 `ROUND_STILL_OPEN`，訊息為「本輪尚未關閉，無法判錯」（`Scenario: US4-AS5`）；該輪已定案 `RESULT_ALREADY_FINAL`；每種都不更動存放區與版本
- [ ] T046 [P] [US4] 在 `tests/unit/app/ranking_review/test_mark_publish.py` 測試：實際變更恰推送一次且**在 004 鎖釋放後**（`RecordingPublisher` 記錄呼叫時鎖未被持有）；重複判錯、重複撤銷、被拒絕的請求都不推送；推送拋例外時狀態變更仍保留並記 `logger.exception`（研究 R4）
- [ ] T047 [P] [US4] 在 `tests/contract/test_http_ranking_review.py` 測試 `PUT /api/activities/{code}/rounds/{round}/questions/{q}/groups/{g}/judgement`：本文 `{"wrong": true}` → 200 `{"changed": true, "resultVersion": 2, "affectedQuestions": [...]}`；本文多送 `reason` 等欄位被忽略、不需要也不顯示原因（`Scenario: US4-AS8`）；錯誤碼與 HTTP 狀態逐列照 `contracts/http-api.md` 錯誤表（`INVALID_REQUEST` 400：本文不是物件、缺 `wrong`、`wrong` 不是布林、路徑上輪次／題號／組號不是正整數；`NOT_TEACHER` 403；`ACTIVITY_NOT_FOUND` 404／`ACTIVITY_GONE` 410；`ROUND_NOT_FOUND`、`SUBMISSION_NOT_FOUND` 404；`ROUND_STILL_OPEN`、`NO_ROUND`、`RESULT_ALREADY_FINAL`、`ACTIVITY_CANCELLED` 409）；所有錯誤訊息不含堆疊、檔案路徑、token；對**非搶答成功者**的已接受提交 PUT 判錯回 200（API 不限於目前的搶答成功者，`Scenario: US4-AS9` 的 API 部分，FR-011）
- [ ] T048 [P] [US4] 在 `tests/integration/test_us4_judgement.py` 測試端對端（真 app、HTTP + 快照）：題組候選判錯後快照該筆 `judgedWrong=true`、`displayStatus="WRONG"`，003 的答案仍在 `submissions.published`（`Scenario: US4-AS1`、`US4-AS2`）；速度模式候選 1、2、3、4：老師判 1、2 錯 → 1、2 `WRONG`、3 `SUCCESS`、4 `FAILED` 且 `judgedWrong=false`；再判 3 錯 → 4 遞補 `SUCCESS`（`Scenario: US4-AS7`）；撤銷（`Scenario: US4-AS3`）；連續判錯甲、乙（搶答成功者依序換成乙、丙）後連續撤銷兩次，每一步 `replacedGroup`、`successGroup` 與 `actions` 都依規則退回（`Scenario: US4-AS10`）；以 API 直接對非搶答成功者判錯仍回 200（`Scenario: US4-AS9` 的 API 部分）
- [ ] T055 [P] [US4] 在 `tests/unit/core/ranking_review/test_diff.py` 測試 `diff`：只有順位或搶答成功者真正改變的題被列入，沒改變的題不列入（`Scenario: US5-AS5`）；對非搶答成功者判錯（有名次 → 無名次）仍列入；初始結果沒有舊版 → 空集合（`diff` 在 T049 實作，所以其測試放在 US4 的測試區先寫、先失敗；US5 的 T053～T054 驗證整輪重算語意）

### Implementation for User Story 4

- [ ] T049 [US4] 在 `<core>/ranking.py` 實作 `RankingCalculator.diff(old: RoundResult, new: RoundResult) -> frozenset[int]`（逐題比較 `QuestionRanking`：成功者與所有 `RankEntry`，任一項不同即受影響；初始結果無舊版回傳空集合；research R10）；在 `<core>/review.py` 實作 `RoundReviewRules.mark`：驗證 `(group, question)` 有候選 → 狀態相同則 `changed=False` → 否則更新 `wrong_marks`、以**保存的題序**與基準重算整輪、`version + 1`、`affected = diff(old, new)`、依 T043 更新 `replaced` 歷程（附加／移除，依賴 T043）
- [ ] T050 [US4] 在 `<app>/service.py` 實作 `mark_wrong` 與 `unmark_wrong`（共用 `_set_wrong`）：依 data-model 判定順序檢查（活動存在 → 老師身分 `ActivityService.is_teacher` → 未取消 → 有輪次 → 輪次存在 → 該輪是否已定案 → 目前輪已關閉，搶答中 `ROUND_STILL_OPEN`）；在 `ReviewStore.lock(code)` 內讀取或導出 `RoundReview`、呼叫 `RoundReviewRules.mark`、寫回存放區；鎖外 `await publisher.publish(activity)`；日誌 `logger.info("判錯 activity=%s round=%s question=%s group=%s wrong=%s changed=%s version=%s", ...)`，不記答案、token（FR-032）（依賴 T044～T046）
- [ ] T051 [US4] 在 `<web>/ranking_review.py` 實作 `PUT /activities/{code}/rounds/{round}/questions/{q}/groups/{g}/judgement`：`JudgementBody(BaseModel)`（`wrong: StrictBool`，`extra="ignore"`）；身分用 `service().resolve_requester(code, token)`；`Outcome` 轉 `ApiError(rejection.http_status, rejection.value, message)`；成功回 `{"changed", "resultVersion", "affectedQuestions"}` 並 `annotate_request_log(request, activity_code=code, result=..., version=...)`；路徑參數非正整數回 400 `INVALID_REQUEST`（依賴 T047）
- [ ] T052 [US4] 前端老師端：`ranking-review-teacher.js` 在活動階段為「結果未定案」時，按鈕只依老師版 JSON 的 `actions` 顯示、前端不自行判斷：每題**只對 `actions.judgeGroup`（目前的搶答成功者）顯示「判錯」按鈕**（搶答成功者之後的候選沒有按鈕，判完由遞補的下一組接手），並**只對 `actions.undoGroup`（最近一位被替換者）顯示「撤銷判錯」按鈕**，撤銷是「退回上一步」（按完按鈕移到更早一位被替換者旁），呼叫 `api.js` 送出 PUT（這只是介面限制，API 仍允許對任一提交判錯與撤銷，FR-034、`Scenario: US4-AS9`）；**不提供原因輸入欄**；失敗時以 `textContent` 顯示後端訊息；階段為「結果已定案」或「已結束」時不顯示按鈕

**Checkpoint**: 判錯與撤銷可用、各種拒絕情境都有明確訊息且不改變狀態

---

## Phase 7: User Story 5 - 整輪重算與受影響題目 (Priority: P1)

**Goal**: 每次判錯狀態改變從基準與固定題序整輪重算；結果版本遞增；只標示最近一次變更的受影響題目；同輸入同結果

**Independent Test**: 跨題範例（判錯題一甲 → 題一乙勝、題二甲勝）、撤銷回原結果、重複多次結果相同

### Tests for User Story 5（先寫、確認失敗）⚠️

- [ ] T053 [P] [US5] 在 `tests/unit/core/ranking_review/test_recompute.py` 用 `CROSS_QUESTION` 測試：公平結果題一甲勝、題二乙勝；判錯題一甲後重算為題一乙勝、題二甲勝，兩題都在受影響集合，各組本輪暫算次數仍各為 1（`Scenario: US5-AS1` ↔ OpenSpec「判錯造成跨題勝者改變」）；撤銷後回到判錯前逐項完全相同（`Scenario: US5-AS2`）；某題所有候選被判錯 → 該題 `success_group is None`、不增加任何組次數（`Scenario: US5-AS3` ↔ OpenSpec「全部被判錯」）；對不同題連續判錯、撤銷數次再回到最初判錯集合 → 與最初結果逐題完全相同（`Scenario: US5-AS4`，SC-003）；同一輸入連續重算 100 次逐項相等（SC-002）
- [ ] T054 [P] [US5] 在同一檔案加入**負對照**：以測試內定義的 `accumulating_recompute`（在舊暫算次數上累加／扣減的錯誤實作）驗證 SC-003 的比較函式「會失敗」——跑完 T053 的操作序列後，`accumulating_recompute` 的結果與初始結果不同、`RankingCalculator.recompute` 相同；證明這組測試有鑑別力（憲章：評測要分得出好壞）
- [ ] T056 [P] [US5] 在 `tests/unit/app/ranking_review/test_marks_concurrency.py` 測試：兩個判錯請求以 `asyncio.gather` 同時到達（不同提交），依鎖的取得順序逐一套用，結果版本各遞增一次（版本 = 初始 + 2），最終結果等同兩筆判錯都生效後的整輪重算，且與順序無關（`Scenario: US5-AS7`）
- [ ] T057 [P] [US5] 在 `tests/integration/test_us5_recalc.py` 端對端測試（HTTP + 快照）：先判錯造成題一、題二的 `affectedQuestions == [1, 2]`，再判錯只影響題三的一筆 → `affectedQuestions == [3]`，題一、題二的標示消失；定案後 `affectedQuestions == []`；晚開啟的頁面（新的 `GET /snapshot`）與早開啟頁面看到相同的標示（`Scenario: US5-AS6`）；搶答成功者被判錯後次一名遞補、原搶答成功者 `WRONG`（`Scenario: US5-AS8`）；`resultVersion` 嚴格單調遞增，且連續多次讀取 `GET /snapshot` 永遠不出現較小的版本

### Implementation for User Story 5

- [ ] T058 [US5] 確認 `<core>/review.py` 的 `RoundReviewRules.mark` 以**保存的** `RoundResult.order`、開輪基準與完整判錯集合重算（絕不使用 `RoundReview.result.group_counts` 當起點），`affected` 每次實際變更時整個覆蓋、不累計；`ResultView` 在 `final=true` 輸出空 `affectedQuestions`（本任務為驗證與補測：整輪重算與 `mark` 已在 T031、T041、T049 實作，T053～T054 在寫成時可能就通過，不要求先失敗；負對照 T054 證明這組測試有鑑別力）
- [ ] T059 [US5] 前端：`ranking-review-teacher.js` 與 `ranking-review.js` 對 `affectedQuestions` 內的題目加標示文字「結果已更新」（其他題不標）；在 `ranking-review.js` 實作並匯出 `acceptRankingVersion(roundNumber, resultVersion)`：為每輪記住已收過的最大 `resultVersion`，收到較小者回傳 `false`，兩個前端模組都用它決定是否更新結果區塊（研究 R3，FR-016；其他區塊照常更新）

**Checkpoint**: 重算可重現、受影響題目標示正確、版本單調

---

## Phase 8: User Story 6 - 老師確認定案並鎖定歷史 (Priority: P1)

**Goal**: 老師確認所見最新版本後定案；成果只交給 001 一次；重複確認冪等；過期版本被拒；定案後鎖定；供 005 唯讀讀取

**Independent Test**: 以最新版本確認、重送、舊版本確認、定案後判錯；兩輪端對端驗證下一輪基準

### Tests for User Story 6（先寫、確認失敗）⚠️

- [ ] T060 [P] [US6] 在 `tests/unit/core/ranking_review/test_finalize_plan.py` 測試 `RoundReviewRules.finalize_plan(review, baseline)`：`solved_questions` = 有 `success_group` 的題號；`success_increments` = `result.wins`（題組成功只算 1）；`final_counts` = 基準加 `wins`；本輪沒有任何提交（或全被判錯）→ `solved_questions` 為空集合、`success_increments` 為空（`Scenario: US6-AS7`）
- [ ] T061 [P] [US6] 在 `tests/unit/app/ranking_review/test_finalize.py` 用真 `ActivityService` 測試：以最新 `resultVersion` 確認 → 001 階段變「結果已定案」、`Group.success_count` 依 `success_increments` 增加、`Activity.solved_questions` 含新成功題（`Scenario: US6-AS1` ↔ OpenSpec「定案及重複確認」）；同一版本重送 → `already_finalized=True`、001 的 `finalize` **只被呼叫一次**（以包裝的 spy 驗證）、成功次數只增加一次（`Scenario: US6-AS2`）；定案後 `ranking` 的名次 1 提交 `displayStatus` 由 `SUCCESS` 變為 `CORRECT`、`replacedGroup` 為 `null`，`FinalizedResult.rankings` 也是 `CORRECT`（`Scenario: US6-AS1`、`US7-AS14`）；**定案前後 `resultVersion` 相同，但經快取的老師與學生 JSON 必須立即反映定案**（`final` 由 `false` 變 `true`、`SUCCESS` 變 `CORRECT`、老師版 `actions` 與兩種角色的 `replacedGroup` 變 `null`），不得回傳定案前的舊快取；舊版本確認 → `STALE_RESULT_VERSION`，存放區、版本、判錯集合、001 階段都不變（`Scenario: US6-AS3` ↔ OpenSpec「定案前結果被更新」）；定案後以**不同**版本確認 → `RESULT_ALREADY_FINAL`，訊息附定案版本；沒有任何判錯就定案（`Scenario: US6-AS6`）
- [ ] T062 [P] [US6] 在 `tests/unit/app/ranking_review/test_finalize_rejected_by_001.py` 測試：以包裝 `ActivityService` 讓 `finalize` 回 `Outcome(ok=False, ...)`（模擬階段剛好變動、活動已失效）→ 004 回 `FINALIZE_REJECTED`、**不保存**定案紀錄，`RoundReview.finalized is None`，結果仍可判錯、版本不變（edge case「確認定案時 001 拒絕」）
- [ ] T063 [P] [US6] 在 `tests/unit/app/ranking_review/test_finalize_concurrency.py` 測試：兩個相同版本的確認以 `asyncio.gather` 同時到達 → 只有一次呼叫 001、`success_count` 只增加一次、其中一個回 `already_finalized=True`（SC-005 的「兩個頁面同時確認」）；判錯與確認同時到達 → 依鎖的順序序列化，不會出現「版本 v 已確認但判錯已套用」的混合結果
- [ ] T064 [P] [US6] 在 `tests/unit/app/ranking_review/test_post_final_lock.py` 測試：定案後判錯、撤銷 → `RESULT_ALREADY_FINAL`（`Scenario: US6-AS4` ↔ OpenSpec「定案後改判」）；下一輪開輪之後修改**舊**輪次判錯狀態 → 同樣 `RESULT_ALREADY_FINAL`，既有搶答成功者與成功次數不變（`Scenario: US6-AS5`）；004 沒有任何切換模式的入口：檢查 `/api` 路由表沒有任何修改輪次模式的端點，且「結果未定案」「結果已定案」階段再開輪回 `STAGE_NOT_ALLOWED`（FR-010；以既有 001 行為驗證，不新增 004 行為；`RULES_LOCKED` 只用於搶答中重複開輪，不在此測）
- [ ] T065 [P] [US6] 在 `tests/unit/app/ranking_review/test_finalized_reader.py` 測試 `RankingService.finalized_rounds(code)`（`RankingReader`）：只回傳**已定案**輪次、依輪次遞增；未定案與搶答中的輪次不出現；回傳物件不可變；被判錯的提交 `rank is None`、未成功的候選（名次 2、3…）`rank` 為其名次且 `display_status` 為 `FAILED`；`final_counts` 等於 001 定案後各組 `success_count`（005 FR-025 的依據）
- [ ] T066 [P] [US6] 在 `tests/contract/test_http_ranking_review_finalize.py` 測試 `POST /api/activities/{code}/rounds/current/finalize`：本文 `{"resultVersion": n}` → 200 `{"version", "resultVersion", "alreadyFinalized"}`；本文 `{}` 或缺 `resultVersion`、`resultVersion` 不是整數 → 400 `INVALID_REQUEST`；`NOT_TEACHER` 403；`STALE_RESULT_VERSION` 409；`RESULT_ALREADY_FINAL` 409；`ROUND_STILL_OPEN` 409；`/api` 路由表中此路徑只有**一個**處理器（001 的空定案路由已移除）
- [ ] T067 [P] [US6] 在 `tests/integration/test_us6_two_rounds.py` 端對端測試兩輪：第 1 輪速度模式，甲組成功一個三格題組並定案 → 第 2 輪開輪後甲組基準為 1（不是 3，`Scenario: US1-AS1` 的端對端版本）；速度模式的成功與公平模式的成功都計入基準（`Scenario: US1-AS2`）；第 2 輪公平模式依基準排名，次數較少的組先成功；定案後全部題都有成功者時開下一輪被 001 拒絕（不屬 004 行為，確認不退步）；本輪所有題都沒有提交時照常定案、成功次數不變（`Scenario: US6-AS7`）

### Implementation for User Story 6

- [ ] T068 [US6] 在 `<core>/review.py` 實作 `RoundReviewRules.finalize_plan` 與建立 `FinalizedResult`；在 `<app>/service.py` 實作 `finalize(code, requester, result_version)`：在 `ReviewStore.lock(code)` 內依 data-model 判定順序檢查（已定案且版本相同 → 冪等回既有結果，**不再呼叫 001**；已定案但版本不同 → `RESULT_ALREADY_FINAL`；階段須為結果未定案；版本須等於目前結果版本，否則 `STALE_RESULT_VERSION`）→ `await activity_service.finalize(code, requester, FinalizeOutcome(solved, increments))` → 成功才把 `FinalizedResult` 寫回 `RoundReview.finalized`；001 拒絕時回 `FINALIZE_REJECTED` 並沿用 001 訊息；`FinalizedResult.rankings` 以 `as_final(result.rankings)` 產生（名次 1 的 `SUCCESS` 改為 `CORRECT`）；實作 `finalized_rounds`（`RankingReader`）；日誌 `logger.info("定案 activity=%s round=%s version=%s already=%s", ...)`
- [ ] T069 [US6] 在 `<web>/ranking_review.py` 實作 `POST /activities/{code}/rounds/current/finalize`（本文 `FinalizeBody(resultVersion: StrictInt)`，`extra="ignore"`；可接受 `Idempotency-Key` 但不依賴它）；**同時**移除 `src/lecture_quiz/adapters/web/http_api.py` 中 001 預留的 `POST /activities/{code}/rounds/current/finalize` 空定案路由（含其 docstring「004 會擴充本文」）；更新 `specs/001-activity-session/contracts/http-api.md` 第 8 項為「由 004 提供，見 `specs/004-ranking-review/contracts/http-api.md` R2」（Complexity Tracking 已說明理由；PR 說明要列出這項對 001 的影響）
- [ ] T070 [US6] 前端老師端：`ranking-review-teacher.js` 加「確認定案」按鈕，送出畫面上最新的 `resultVersion`；`STALE_RESULT_VERSION` 時顯示「結果已更新，請重新檢視後再確認」且不自動套用；成功或 `alreadyFinalized` 後隱藏判錯與確認按鈕、顯示「結果已定案」；失敗訊息 `textContent`

**Checkpoint**: 定案流程完整、001 與 004 的結果一致、005 可唯讀取得定案結果

---

## Phase 9: User Story 7 - 依角色看到結果、文字安全顯示 (Priority: P2)

**Goal**: 搶答中沒有任何順位；關輪後資料公開查詢（不含理由與他組次數）；學生畫面只顯示本組狀態、目前搶答成功者與剛被判錯的前一組；不可信文字安全顯示

**Independent Test**: 搶答中與關輪後分別以老師、學生取得資料與畫面；含標記與多行答案的顯示；舊輪次可查、新輪次不洩漏

### Tests for User Story 7（先寫、確認失敗）⚠️

- [ ] T071 [P] [US7] 在 `tests/integration/test_ranking_visibility.py` 測試：搶答中老師與學生的所有回應與 WebSocket 推送都不含 `ranking` 欄位，且他組動態不使本組學生收到任何推送（`Scenario: US7-AS1`，SC-007）；關輪後學生快照含各題各組的 `rank`、`judgedWrong`、`displayStatus` 與 `successGroup`（資料公開，`Scenario: US7-AS5`），遞迴掃描學生 JSON，鍵 `reason`、`countAtProcessing`、`groupCounts` 出現次數為 **0**（FR-036、SC-010）；老師 JSON 含這些鍵（`Scenario: US7-AS6`）；某題無人提交或全被判錯 → `successGroup: null`、`entries` 不含該題搶答成功者（`Scenario: US7-AS9`）；開下一輪後舊輪次仍在 `ranking.rounds`，新輪次（搶答中）的他組資料不出現（`Scenario: US7-AS10`）；另測資料面支撐學生畫面所需的資訊：候選甲、乙、丙、丁，老師把搶答成功者甲判錯後，學生 JSON 該題 `successGroup == 乙`、`replacedGroup == 甲`，甲 entry `displayStatus == "WRONG"`、丙 entry `"FAILED"`（`Scenario: US7-AS3`、`US7-AS4`、`US7-AS11` 的資料部分）；該題再判錯（乙）→ `replacedGroup == 乙`、`successGroup == 丙`；撤銷乙 → `replacedGroup == 甲`、`successGroup == 乙`；再撤銷甲 → `replacedGroup is null`、`successGroup == 甲`（`Scenario: US4-AS10`）；整題全被判錯 → 學生 JSON `successGroup`、`replacedGroup` 皆 `null`、老師 JSON `replacedGroup` 保留（`Scenario: US7-AS9`）；定案後 `displayStatus` 名次 1 為 `"CORRECT"`、`replacedGroup` 為 `null`（`Scenario: US7-AS14`）；沒有提交的組在該題沒有 entry（`US7-AS13`）。**畫面實際只顯示哪些組由前端決定，專案沒有前端單元測試設施，這部分由 T094 的人工驗證負責，不得宣稱已由自動化測試驗證**
- [ ] T072 [P] [US7] 在 `tests/unit/core/ranking_review/test_view_student.py` 測試：`for_student` 的輸出與請求者所屬組別無關（任意兩組的學生版相同）；同一份輸入的學生版鍵集合是老師版的真子集；`final=true` 時兩者 `affectedQuestions` 皆為 `[]`
- [ ] T073 [P] [US7] 在 `tests/architecture/test_static_text_safety.py` 擴充（沿用 003 的掃描方式）：新增的 `ranking-review.js`、`ranking-review-teacher.js` 不得使用 `innerHTML`、`outerHTML`、`insertAdjacentHTML`、`document.write`、`eval`、`new Function`，文字一律 `textContent`／`createTextNode`（`Scenario: US7-AS7`，FR-028）
- [ ] T074 [P] [US7] 在 `tests/integration/test_us7_safe_display.py` 測試資料面（沿用 003 `test_us6_safe_display.py` 的做法）：含 `<b>`、`<script>` 字樣與 500 字、多行的答案，經 003 送出、判錯、關輪後，快照中 003 的 `answers` 逐字等於原文（不被截斷、不被跳脫改寫）；004 的 JSON 內不含任何答案內容（答案只由 003 提供，避免重複與洩漏）（`Scenario: US7-AS7`、`US7-AS12`）
- [ ] T075 [P] [US7] 在 `tests/integration/test_ranking_snapshot_monotonic.py` 測試：交錯的判錯與多次 `GET /snapshot`、WebSocket 推送，每個身分看到的某輪 `resultVersion` 單調不減，永遠不會把較小版本送在較大版本之後（後端層保證；前端守衛見 T059 與 T094 的人工步驟，`Scenario: US7-AS8`）

### Implementation for User Story 7

- [ ] T076 [US7] 前端學生端（依 FR-036、FR-037 限縮）：`<static>/js/ranking-review.js` 只顯示 ① 本組每題每筆提交的顯示狀態（搶答成功／搶答正確／答錯／搶答失敗；整題無人成功為「未成功」）；② 每題目前的搶答成功者（`successGroup`，組號、答案與狀態：定案前「搶答成功」、定案後「搶答正確」）；有 `replacedGroup` 時，把剛被判錯的那一組（組號、答案與「答錯」）與遞補的搶答成功者**一起**顯示，該題再判錯時換成新被判錯的那一組、撤銷時退回上一步（顯示更早一位被替換者）、定案時移除；整題無搶答成功者只顯示「未成功」與本組狀態（答案由 003 的 `submissions.published` 以（輪次、題號、組號）合併取得）；③ 本組成功次數（`ownGroup.successCount`，沿用 001）；**不**逐組列出其他候選、不顯示理由與他組成功次數；本組沒有提交的題不顯示狀態（`Scenario: US7-AS2`、`US7-AS3`、`US7-AS4`、`US7-AS9`、`US7-AS11`、`US7-AS13`、`US7-AS14`）；多行答案保留換行、完整顯示（`Scenario: US7-AS12`）
- [ ] T077 [US7] 調整 003 已合併的學生頁（FR-037）：在 `<static>/js/round-submission.js` 讓「已公開的作答」區塊（`renderPublished`）**不再對學生列出全部組的答案與送出先後**（改由 T076 的區塊呈現；老師頁 `round-submission-teacher.js` 的已公開輪次列表保留，並由 T035 補上 004 資料）；只改前端呈現與其測試，**不改 003 的資料與後端**；先 `grep -rn "published" tests/` 找出斷言學生頁文字的測試，只調整與畫面呈現有關的斷言並記在 `verification.md`「問題紀錄」，資料層斷言（`submissions.published` 內容）不得改動
- [ ] T078 [US7] 確認老師頁 `ranking-review-teacher.js` 與 003 的已公開輪次列表在同一輪、同一快照內以（輪次、題號、組號）合併、沒有重複顯示答案；`judgedWrong` 以 004 的 `ranking` 為準，**不使用** 003 的佔位 `judgedWrong` 欄位（研究 R5，FR-035）

**Checkpoint**: 所有 User Story 獨立可用

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 影響多個 Story 的收尾與憲章要求的驗證

- [ ] T079 更新 `tests/SCENARIO_MAP.md`：標題改為涵蓋 001、003、004；以 docstring `Scenario:` 掃描產生 004 的 US1-AS1～US7-AS13 對照列；確認每個 Acceptance Scenario 與 OpenSpec ranking-review 的 12 個 Scenario 至少一個測試，未對應者標「無」並在 `verification.md` 說明（憲章原則 VI）
- [ ] T080 [P] 在 `tests/integration/test_ranking_logging.py` 測試日誌（憲章技術限制 3、FR-032）：判錯、撤銷、定案各產生一行 INFO，只含活動代碼、輪次、題號、組號、`wrong`／`changed`、版本；整份日誌找不到答案文字、token、憑證；無 `print`
- [ ] T081 [P] 在 `tests/contract/test_error_safety.py` 擴充 004 的兩個路由：所有錯誤回應不含堆疊追蹤、檔案路徑、token、憑證、他組資料（憲章原則 V、FR-027）
- [ ] T082 [P] 在 `tests/perf/test_ranking_latency.py` 實作效能測試（`@pytest.mark.perf`，預設排除，仿 `tests/perf/test_submission_latency.py`：本機真實 uvicorn、`websockets` 客戶端）：**必過門檻**＝老師 + 6 組、每組 2 條連線（共 13 條 WebSocket）、50 題的輪次，判錯、撤銷、定案各重複 10 次，量「送出請求 → 每條連線收到含新 `resultVersion` 的快照」，**最大值 < 2 秒**（SC-004）；**只記錄**＝同樣流程老師 + 20 組（41 條連線），把最大值與是否小於 2 秒寫進 `verification.md`，沒達標要說明，不得宣稱更大規模達標；全部由自動化測試執行，不靠人工量測
- [ ] T083 執行 `pytest -m perf tests/perf/test_ranking_latency.py`，把 6 組與 20 組的實測最大值、指令寫入 `verification.md`「效能」（若 20 組明顯變慢，依研究 R14 評估「只送目前輪並提供 GET 查詢舊輪」，只記錄建議，不在本 PR 實作）
- [ ] T084 程式碼與圖表一致性驗證：逐一比對 `diagrams/004-ranking-review-{component,class,sequence}.puml` 與實作（類別名、方法名、流程、`ReviewStore`／`RoundReviewRules`／`ResultView`／`SyncPublisher` 相依方向、初始結果由純計算導出）；有差異時**先更新圖表並重新轉出 PNG**（`java -jar plantuml.jar "./diagrams/004-*.puml"`，並實際開啟檢視），再改程式，結果記在 `verification.md`（憲章原則 II）
- [ ] T085 執行 `ruff check .`、`ruff format --check .`、`mypy`，全部通過並把結果寫入 `verification.md`（憲章技術限制 2）
- [ ] T086 檢查日誌與核心純度：`grep -rn "print(" src/` 無結果；`<core>` 無 `datetime.now`、`time`、`asyncio`、`fastapi` 匯入（架構測試已涵蓋，記錄結果）；`snapshot_extension` 無 I/O 與狀態寫入（只有 `ReviewStore.cache` 的不可變快取，研究 R2、R14）
- [ ] T087 執行全部自動化測試（`pytest -m "not real_google and not perf"`），記錄指令與通過／失敗／略過數，並與 T002 基準比較：既有測試不退步、新增測試數合理（憲章原則 VI）
- [ ] T088 [P] 同步文件：`CLAUDE.md` 新增「004-ranking-review 已實作」段落（程式位置、與 001 的定案路由變更、與 003 學生頁的調整、`verification.md` 位置）；`docs/DEVELOPMENT.md` 若有「子功能組裝」說明補上 `_wire_ranking`；`specs/003-round-submission/contracts/sync-websocket.md` 的前端行為補一行「學生頁關輪後的結果呈現由 004 的 `ranking-review.js` 負責（004 FR-037）」；`specs/001-activity-session/contracts/service-interfaces.md`「給 004」補上「定案一律經 004 的 HTTP 路由」
- [ ] T089 [P] OpenSpec 核對：確認 `docs/openspec-reference/ranking-review/spec.md` 的 SHA-256 仍與 `docs/openspec-reference/README.md` 一致（`7a243602279aa7f22f33436903cb171df7749d2efe951783ec5c56c4615bd23f`）；確認實作沒有新增或偏離 OpenSpec 的功能行為，若有（例如學生畫面範圍），依憲章原則 I 記入 `docs/alignment.md` 並經兩組確認後才能合併
- [ ] T090 在 `verification.md`「N/A 說明」寫明：憲章原則 III 的兩份版面學習單與 Google 真實路徑驗證不適用於 004（不讀寫試算表，理由見 spec Assumptions）；004 以 `LAYOUT_A`／`LAYOUT_B` 兩組不同題數配置的純資料測試（T024、T039）與真實後端多分頁人工驗證（T094）取代；自動化測試完全不呼叫外部服務
- [ ] T091 [P] 準備 PR 說明（草稿，不自動發布）：列出對既有程式的影響範圍——001 的 HTTP 定案路由改由 004 提供（`resultVersion`）、既有定案測試改用 helper（斷言未改）、003 學生頁「已公開的作答」呈現調整（資料不變）；列出新增檔案、驗證指令與結果數字、與 OpenSpec 無新偏離的說明；結尾加 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- [ ] T092 [P] 與 003 負責人確認 T077 對學生頁的調整（`round-submission.js` 與其測試），把確認日期與結果記在 `verification.md`「問題紀錄」
- [ ] T093 執行 `quickstart.md` 的「一、自動化驗證」全部指令，確認每條指令與預期相符（含 `tests/SCENARIO_MAP.md` 對照）；結果寫入 `verification.md`
- [ ] T094 **非實作者**（jacky0407）依 `quickstart.md`「二、手動驗證」13 個步驟在多個瀏覽器分頁（老師＋三組學生）以真實後端完整走一遍，另加四項前端專屬檢查：① 開兩個老師分頁，在較舊的分頁確認畫面不會被較舊的 `resultVersion` 覆蓋（`Scenario: US7-AS8`）；② 學生頁關輪後只顯示本組狀態、目前的搶答成功者與（判錯當下）剛被判錯的前一組，沒有列出全部組作答（FR-037）；③ 老師介面每題只有目前的搶答成功者有「判錯」按鈕、只有被替換的那一組有「撤銷判錯」（FR-034）；④ 定案後學生與老師畫面的「搶答成功」同時變成「搶答正確」、「剛被判錯的前一組」消失（`Scenario: US7-AS14`）。記錄日期、操作步驟、實際看到的畫面文字、各組成功次數與 `resultVersion`、畫面右下角延遲；沒有實際執行不得宣稱完成（憲章原則 VI；SC-009）。題目需經 002 真實匯入，002 尚未合併時在此註明阻塞原因，不得以假資料取代

- [ ] T095 確認沒有夾帶機敏資料或不追蹤的檔案（憲章合併前品質關卡第 7 項、原則 V）：`git diff --staged` 與 `git status` 檢查沒有 `.env`、憑證 JSON、`.venv`、`期末專題說明.md`／`.pdf`、`project_proposal_draft.md`；`grep -rn "client_secret\|access_token\|refresh_token" src/ tests/ specs/004-ranking-review/` 無結果；PR、Issue 說明不貼機敏內容；結果記入 `verification.md`

---

## FR／SC 對照表（可追溯性）

| 需求 | 任務 |
|---|---|
| FR-001、FR-002、FR-003 基準 | T019～T023、T060、T067 |
| FR-004、FR-005 固定題序 | T024、T026、T030 |
| FR-006、FR-009 速度模式 | T025、T031 |
| FR-007、FR-008 公平模式與理由 | T037～T042 |
| FR-010 模式固定 | T064 |
| FR-011～FR-014 判錯與撤銷 | T043～T052 |
| FR-015～FR-018 重算、版本、標示、全被判錯 | T053～T059 |
| FR-019～FR-023 定案與鎖定 | T060～T070 |
| FR-024 搶答中不提供順位 | T029、T071 |
| FR-025 重複判錯不變 | T043、T046 |
| FR-026、FR-027 後端判定與輸入驗證 | T044、T045、T047、T066、T081 |
| FR-028 純文字顯示 | T073、T074 |
| FR-029 序列化 | T056、T063 |
| FR-030 2 秒 | T029、T082、T083 |
| FR-031 階段標示 | T035、T094 |
| FR-032 日誌 | T050、T068、T080 |
| FR-033、FR-034 顯示狀態、判錯免填原因與老師介面順序 | T025、T048、T052、T071、T094 |
| FR-035 一致呈現 | T078 |
| FR-036、FR-037 角色畫面與 003 學生頁調整 | T071、T072、T076、T077、T094 |
| SC-001～SC-010 | T079、T053、T054、T082、T061、T063、T071、T073、T074、T094 |
---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 無相依，可立即開始（T003、T004 可平行）
- **Foundational (Phase 2)**: 依賴 Setup；**阻塞所有 User Story**；T017 一定要在 US6 之前完成（它讓既有測試在新舊定案路由下都能運作）
- **US1 → US2 → US3**：US1 的 `_build_input` 是 US2、US3 的輸入；US3 的公平模式依賴 US2 的題序與 `recompute`
- **US4（判錯）** 依賴 US2、US3 的 `recompute` 與 `ResultView`；**US5** 依賴 US4 的 `mark`
- **US6（定案）** 依賴 US4（判錯後版本）；其冪等與版本檢查依賴 US5 的版本規則
- **US7（可見性、學生畫面、003 調整）** 依賴 US2 的快照與前端，建議放在 US6 之後
- **Polish (Phase 10)**: 依賴所有 User Story；T094 需要 002 已合併才能真實匯入題目

### Within Each User Story

- 測試先寫並確認失敗（失敗數記入 `verification.md`），再寫實作
- 核心（`<core>`）→ 服務層（`<app>`）→ 外層（`<web>`、`<static>`）
- 每個 Story 結束時（Checkpoint 前）執行 `ruff check .`、`ruff format --check .`、`mypy` 與全部測試，三者都通過再勾選、commit（憲章技術限制 2：提交前必須通過；T085 是最後的總檢查）

### Parallel Opportunities

- Setup：T003、T004
- Foundational 測試：T005～T008；實作 T010、T011、T013 可平行（不同檔案）
- 各 Story 的測試任務（標 [P]）可同時撰寫，因為檔案不同
- US2 的 T024～T029、US4 的 T043～T048、US6 的 T060～T067 各自可平行

---

## Parallel Example: User Story 4

```text
# 同時寫 US4 的測試：
Task: "T043 tests/unit/core/ranking_review/test_review_rules_mark.py"
Task: "T044 tests/unit/app/ranking_review/test_mark_permissions.py"
Task: "T045 tests/unit/app/ranking_review/test_mark_stages.py"
Task: "T046 tests/unit/app/ranking_review/test_mark_publish.py"
Task: "T047 tests/contract/test_http_ranking_review.py"
Task: "T048 tests/integration/test_us4_judgement.py"
```

## Parallel Example: Foundational

```text
Task: "T005 tests/unit/core/ranking_review/test_models.py"
Task: "T006 tests/unit/app/ranking_review/test_store.py"
Task: "T007 tests/unit/app/ranking_review/test_extension_registration.py"
Task: "T008 tests/contract/test_http_ranking_review_wiring.py"
```

---

## Implementation Strategy

### MVP First（US1 → US2 → US4 → US6）

1. Phase 1 Setup → Phase 2 Foundational（既有測試全過、定案 helper 就緒）
2. Phase 3 US1 → Phase 4 US2：關輪後看得到速度模式順位
3. Phase 6 US4：可判錯；Phase 8 US6：可定案
4. **停下驗證**：老師能「關輪 → 判錯 → 定案」，成功次數正確交給 001（公平模式與整輪重算的完整驗證在 US3、US5）

### Incremental Delivery

1. US1～US3：順位計算完整（兩種模式）
2. US4～US5：判錯與整輪重算
3. US6：定案與 005 的唯讀讀取
4. US7：角色畫面限縮、003 學生頁調整、安全顯示
5. Polish：SCENARIO_MAP、效能（6 組門檻、20 組記錄）、圖表一致性、人工驗證

### 時程提醒

內部凍結點 2026-11-29 晚上；005 依賴 `RankingReader.finalized_rounds`（T068），建議 US1～US6 優先完成並先推上 PR，讓 005 可以開始整合。T094 的人工驗證需要 002 已合併，請提早確認 002 的進度。

---

## Notes

- [P] = 不同檔案且沒有未完成的相依
- 每個 User Story 完成後勾選、commit（`feat:`／`test:`）、push
- **不得**為了讓測試通過而修改 001、003 既有測試的斷言（T017、T077 只能改呼叫方式或畫面呈現，並記錄）
- 快照擴充函式必須是同步、無副作用的純讀取（`docs/DEVELOPMENT.md` 3.5）；初始結果由純計算導出，第一次實際判錯才寫入 `ReviewStore`（研究 R2）
- 學生可取得的資料不得含 `reason`、`countAtProcessing`、`groupCounts`（FR-036，SC-007、SC-010）；答案只由 003 提供，004 的 JSON 不含答案內容
- 日誌只記活動代碼、輪次、題號、組號、`wrong`／`changed`、版本；不記答案、token、憑證（FR-032）
- 驗證結果一律寫在 `specs/004-ranking-review/verification.md`，要有日期、指令與結果數字，沒有實際執行不得勾選
