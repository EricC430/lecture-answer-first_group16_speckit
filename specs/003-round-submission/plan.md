# Implementation Plan: 多題搶答與送出

**Branch**: `feature/7-003-round-submission` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-round-submission/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/003-round-submission-component.puml`](../../diagrams/003-round-submission-component.puml)
- 類別圖：[`diagrams/003-round-submission-class.puml`](../../diagrams/003-round-submission-class.puml)
- 時序圖：[`diagrams/003-round-submission-sequence.puml`](../../diagrams/003-round-submission-sequence.puml)

本 plan 的模組、類別與流程都依這三張圖命名；plan 階段因研究 R2、R4 調整了「鎖內流程」與「快照擴充」，三張圖已在同一個 commit 更新並重新轉出 PNG。實作偏離時先改圖。

## Summary

已加入組別的學生裝置在搶答中依任意順序提交本輪開放題；一筆提交包含該題全部子空格（格數來自 002）；每組每題每輪只保存第一筆有效提交；後端以「嚴格早於截止時間」判定並產生接收時間與接收序號；搶答中學生只看得到本組資料，老師看板即時顯示全部；關輪後公開本輪提交，歷史輪次可查但不洩漏新一輪。

技術做法：

- **核心**（`core/round_submission/`，純函式）：`SubmissionRules.decide(ledger, context, code, attempt, now)`（序號取自 `ledger.next_sequence`） 依固定順序判定「接受／本組已送出／拒絕」；`AnswerRules` 集中 Q-20 的答案規則；`SubmissionView` 產生老師版、學生版、關輪公開版資料，依（接收時間, 接收序號）排序。
- **服務層**（`app/round_submission/`）：`SubmissionService` 不自己持有鎖，而是呼叫 001 新增的 `ActivityService.record_submission(...)`，在 **001 的同一把活動鎖內**完成「解析裝置 → 取時間 → 判定 → 標記組別 → 保存」，鎖外推送（研究 R2）。提交資料存在 003 自己的記憶體 `SubmissionStore`（研究 R1）。
- **快照**：001 新增「快照擴充」機制，003 註冊一個擴充函式，把本組提交（學生）或全部提交（老師）併入 001 既有的快照；推送沿用 001 的 `WebSocketHub` 與版本規則（研究 R4、R5）。
- **外層**：`POST /api/activities/{code}/submissions`（研究 R7）；學生頁作答表單（`js/round-submission.js`）、老師頁提交看板（`js/round-submission-teacher.js`），所有文字用 `textContent`。
- **002 介面**：003 定義 `QuestionShapeSource.blanks_per_question(code)`，由 002 實作（已與 EricC430 口頭協調）；002 合併前以 dev seed 的假實作驗證（研究 R6）。

## Technical Context

**Language/Version**: Python 3.11 以上（沿用 001；本機驗證 3.11.5 與 3.14）

**Primary Dependencies**: FastAPI、uvicorn、pydantic（沿用 001，不新增套件）；前端原生 JavaScript

**Storage**: 只存在後端記憶體（憲章原則 VII），後端重啟清空

**Testing**: pytest（`perf` marker 預設排除）、pytest-timeout、FastAPI TestClient；ruff、mypy（`src/`）

**Target Platform**: Windows 本機，後端只監聽 127.0.0.1

**Project Type**: 單一 web 服務（後端 + 靜態前端），沿用 001 的 src layout

**Performance Goals**: 老師 + 6 組、每組 2 條連線時，有效提交被接受後 2 秒內出現在老師看板與同組另一台裝置（SC-006）

**Constraints**: 核心不依賴網路、框架、系統時鐘；截止判定嚴格 `now < deadline`；學生不因他組提交收到任何推送（001 FR-030）；日誌不記 token 與答案內容

**Scale/Scope**: 每活動最多 99 組（001 A2）；題數依匯入結果（通常 < 50）；每格答案 ≤ 500 字（Q-20 提議）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致（NON-NEGOTIABLE） | spec 的 Traceability 涵蓋 round-submission 全部 6 個 Requirement、13 個 Scenario；Q-20／21／22／26 原為 SpecKit 組提議，OpenSpec 組已於 2026-11-23 全部同意（alignment.md「003 提交待確認事項：OpenSpec 組同意」列） | ✅ |
| II 圖表生成（NON-NEGOTIABLE） | 三張圖已在 specify 產出；plan 調整鎖內流程與快照擴充後同步更新並重新轉出 PNG；implement 後要做「程式碼 ↔ 圖」一致性檢查（tasks 列為必做） | ✅ |
| III Guided Notes 動態定位 | 子空格數只從 `QuestionShapeSource`（002 的成功匯入結果）取得，核心不出現任何固定格數或題數；測試用兩份版面的格數配置（A：4 題 [2,2,1,1]；B：5 題 [1,3,1,2,1]），002 合併後以兩份真實學習單匯入再提交 | ✅ |
| IV 後端為唯一事實來源 | 組別由 001 依裝置 token 判定；接收時間由後端 `Clock` 在鎖內取得一次，同時用於截止判定與記錄；接收序號在活動內嚴格遞增；同一組同題重送只會得到既有提交；排序規則（時間, 序號）確定性 | ✅ |
| V 資料可見性與安全 | 學生版擴充只含本組資料，搶答中不含排名與他組成功次數（Q-22；本組成功次數沿用 001 可見）；他組提交不改學生快照內容，hub 不推送（FR-030）；沒有「以組號查詢提交」的端點；前端一律 `textContent`；驗證失敗不保存、不推送、不改版本；錯誤訊息不含 token、路徑、堆疊；日誌只記代碼、輪次、題號、組號、結果 | ✅ |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 與 OpenSpec Scenario 都有測試並在 `tests/SCENARIO_MAP.md` 對照；003 不呼叫 Google；真實路徑驗證＝002 合併後用兩份真實學習單匯入→提交→關輪；非實作者（EricC430）依 quickstart 人工驗證 | ✅ |
| VII 簡單與本機運作 | 不新增套件、不新增資料庫；對 001 的修改限於兩個小擴充點（`record_submission`、快照擴充），見 Complexity Tracking | ✅（附理由） |
| 技術限制：架構（NON-NEGOTIABLE） | `core/round_submission/` 只匯入標準函式庫與 `core/` 內模組；`tests/architecture/test_core_is_pure.py` 已涵蓋整個 `core/` | ✅ |
| 技術限制：日誌、風格 | `logging` INFO；Google docstring、型別提示；ruff、ruff format、mypy 全過才提交 | ✅ |

**Post-design 重新檢查（Phase 1 後）**：data-model、contracts 與 quickstart 都沒有引入新的違反項目；兩個 001 擴充點都不改 001 既有行為（`mark_group_submitted` 保留，既有測試不需改）。研究 R9（Q-22 與 001 學生快照的成功次數）已由 jacky0407 決定沿用 001（本組成功次數可見），001 學生快照不需修改。

## Project Structure

### Documentation (this feature)

```text
specs/003-round-submission/
├── plan.md              # 本檔
├── research.md          # Phase 0：R1～R14 決策
├── data-model.md        # Phase 1：實體、驗證規則、判定順序
├── quickstart.md        # Phase 1：自動化與人工驗證步驟
├── contracts/
│   ├── http-api.md          # POST /submissions
│   ├── sync-websocket.md    # 快照新增的 submissions 欄位
│   └── service-interfaces.md # 003 ↔ 001／002／004／005
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks 產生
```

### Source Code (repository root)

```text
src/lecture_quiz/
├── core/
│   ├── activity/                    # 001（小改：新增 RecordSubmission 指令）
│   │   ├── commands.py              # + RecordSubmission
│   │   └── state_machine.py         # + _record_submission（必定 revision+1、檢查截止）
│   └── round_submission/            # 003 新增（純函式）
│       ├── __init__.py
│       ├── models.py                # Submission、SubmissionAttempt、RoundContext、SubmissionLedger
│       ├── answer_rules.py          # Q-20：判空、字數上限、保存原文
│       ├── rules.py                 # SubmissionRules.decide、order、describe（SubmissionRejection 等型別定義在 models.py）
│       └── view.py                  # SubmissionView（老師版／學生版／公開版）、可見性規則（Q-21／22／26）
├── app/
│   ├── activity/                    # 001（小改）
│   │   ├── ports.py                 # + SubmissionHandler、SnapshotExtension Protocol
│   │   └── service.py               # + record_submission()、add_snapshot_extension()、snapshot_for 改為實例方法
│   └── round_submission/            # 003 新增
│       ├── __init__.py
│       ├── ports.py                 # QuestionShapeSource、SubmissionReader
│       ├── store.py                 # SubmissionStore（記憶體）
│       └── service.py               # SubmissionService
└── adapters/
    ├── web/
    │   ├── submission_api.py        # POST /api/activities/{code}/submissions
    │   ├── ws_sync.py               # 小改：改呼叫 service.snapshot_for（實例方法）
    │   └── dev_seed.py              # 小改：seed 可指定每題格數（002 合併前）
    └── static/
        ├── student.html / js/student.js   # 作答表單、本組提交、公開結果
        ├── teacher.html                   # 提交看板區塊（js/teacher.js 不改）
        ├── js/submission.js               # 作答表單與看板共用的繪製函式（textContent）
        ├── js/round-submission.js         # 學生端接線（onStudentSnapshot），依 DEVELOPMENT.md 一個子功能一個 module
        └── js/round-submission-teacher.js # 老師端看板接線（onTeacherSnapshot）

tests/
├── unit/core/round_submission/      # decide 各順序、AnswerRules、排序、View 裁切
├── unit/core/test_state_machine_record_submission.py
├── unit/app/round_submission/       # 服務 + 真 ActivityService + FakeClock、併發
├── contract/test_http_submissions.py
├── integration/test_us{1..6}_submission*.py、test_submission_visibility.py
└── perf/test_submission_latency.py
```

**Structure Decision**：沿用 001 的三層 src layout；003 新增 `core/round_submission/`、`app/round_submission/`、`adapters/web/submission_api.py`，在 `main.py` 的「子功能 router」區塊加一行掛載。對 001 只做研究 R2、R4 所列的擴充。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| 修改已合併的 001：新增 `record_submission` 與 `RecordSubmission` 指令 | FR-013／FR-019 要求「判定、標記、保存」與關輪互斥，而且結果公開後不能再加入提交；只有 001 的活動鎖能保證這點 | 003 自己加鎖再呼叫 `mark_group_submitted`：`mark_group_submitted` 會在推送時讓出執行權，關輪可能插在「標記」與「保存」之間，造成結果公開後才加入提交（研究 R2） |
| 修改 001：快照擴充機制 | 提交資料要隨 001 的快照一起推送，才能沿用版本規則、hub 去重與重連取完整狀態 | 003 另開一條 WebSocket 或另一種訊息：前端要合併兩個來源、版本規則要再做一次，也更難保證學生收不到他組動態（研究 R4） |
