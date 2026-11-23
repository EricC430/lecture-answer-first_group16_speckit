# Data Model: 多題搶答與送出

**Date**: 2026-11-23 ｜ 對應類別圖 [`diagrams/003-round-submission-class.puml`](../../diagrams/003-round-submission-class.puml)

所有核心型別都是 `@dataclass(frozen=True)`，集合用 `tuple`／`frozenset`／`MappingProxyType`；核心不讀時鐘，`now` 與序號由服務層傳入。

## 核心（`core/round_submission/`）

| 型別 | 欄位 | 說明 |
|---|---|---|
| `Submission` | `activity_code: str`、`round_number: int`、`question_number: int`、`group_number: int`、`answers: tuple[str, ...]`、`received_at: datetime`、`sequence: int` | 一組在某一輪對某一題的第一筆有效提交。`answers[i]` 是第 i+1 格的**原文**（Q-20）。不含裝置 token。建立後不可修改 |
| `SubmissionAttempt` | `round_number_raw: object`、`question_number_raw: object`、`answers_raw: object` | 學生送出的原始內容，由 `decide` 驗證；被拒時不保存 |
| `SubmissionWindow` | `group_number: int`、`stage: Stage`、`round_number: int \| None`、`open_questions: tuple[int, ...]`、`deadline: datetime \| None`、`accepting: bool` | 001 在鎖內組成（研究 R2）；`accepting` = 搶答中且（無截止時間或 `now < deadline`） |
| `RoundContext` | `window: SubmissionWindow`、`blanks_per_question: Mapping[int, int]` | `decide` 的完整輸入；格數來自 `QuestionShapeSource` |
| `SubmissionLedger` | `submissions: tuple[Submission, ...]`、`next_sequence: int = 1` | 一個活動的全部提交；`find(round, question, group)`、`for_round(round)`、`with_added(sub)`（回傳新 ledger，`next_sequence + 1`） |
| `DecisionKind` | `ACCEPTED`、`ALREADY_SUBMITTED`、`REJECTED` | |
| `SubmissionRejection` | 見下表 | `StrEnum`，每個值有 HTTP 狀態碼與預設訊息 |
| `SubmissionDecision` | `kind`、`submission: Submission \| None`、`rejection: SubmissionRejection \| None`、`blank_numbers: tuple[int, ...]`、`expected_blanks: int \| None` | `ACCEPTED`／`ALREADY_SUBMITTED` 時 `submission` 為新／既有提交；`blank_numbers` 是有問題的格號（1 起算） |

### 不變式

- `SubmissionLedger` 中（`round_number`, `question_number`, `group_number`）不重複（FR-007）。
- `sequence` 在 ledger 內不重複且依加入順序嚴格遞增；`next_sequence` 大於所有既有序號（FR-016）。
- 每筆 `Submission.answers` 的長度等於該題格數、每格 `strip()` 後非空、每格 ≤ 500 字（FR-002、FR-003）。
- 排序：`order(subs)` 以（`received_at`, `sequence`）遞增（FR-018）。

### 判定順序（`SubmissionRules.decide`，研究 R10）

| 順序 | 條件 | 結果 | HTTP | 訊息（語意） |
|---|---|---|---|---|
| — | 活動不存在（001 處理） | `ACTIVITY_GONE` | 410 | 活動已失效，請重新加入 |
| — | token 不屬於任何組（001 處理） | `NOT_IN_GROUP` | 403 | 這台裝置還沒有加入組別 |
| 1 | `round_number_raw` 不是整數，或 ≠ 目前輪次編號，或目前沒有輪次 | `STALE_ROUND` | 409 | 輪次已更新，請重新整理後再作答 |
| 2 | `accepting` 為假 | `ROUND_CLOSED` | 409 | 本輪已結束（或尚未開始），不能再送出 |
| 3 | 題號不是整數或不在 `open_questions`，或查不到格數 | `QUESTION_NOT_OPEN` | 400 | 第 n 題不在本輪開放範圍 |
| 4 | 本組本輪本題已有提交 | `ALREADY_SUBMITTED` | 200 | 本組已送出（附既有答案與時間） |
| 5a | `answers_raw` 不是字串陣列 | `INVALID_ANSWER` | 400 | 答案格式不正確，請重新整理後再作答 |
| 5b | 格數 ≠ 該題格數 | `WRONG_BLANK_COUNT` | 400 | 這題需要 k 格答案 |
| 5c | 任一格 `strip()` 後為空 | `BLANK_EMPTY` | 400 | 第 i 格尚未填寫（列出全部空格） |
| 5d | 任一格超過 500 字 | `ANSWER_TOO_LONG` | 400 | 第 i 格超過 500 字 |
| 6 | 其餘 | `ACCEPTED` | 201 | — |

`ALREADY_SUBMITTED` 在服務層回傳 `result: "alreadySubmitted"`，不是錯誤（研究 R7）。

## 可見性規則（`core/round_submission/view.py`，Q-21／Q-22／Q-26 集中可調）

| 常數 | 預設 | 來源 |
|---|---|---|
| `TEACHER_SEES_PROVISIONAL_RANKING_DURING_ROUND` | `False` | Q-21 提議 |
| `STUDENT_SEES_OWN_SUCCESS_DURING_ROUND` | `True` | Q-22 提議（研究 R9：沿用 001，本組成功次數可見；改為 `False` 時由 003 擴充把 `ownGroup.successCount` 設為 `null`） |
| `STUDENT_SEES_JUDGED_WRONG` | `True` | Q-26 提議 |

| 檢視 | 本輪開放中 | 已公開輪次（研究 R11） |
|---|---|---|
| 老師 `TeacherBoard` | 每題 × 每組：已送出／尚未送出、答案、接收時間、先後名次（依排序鍵的第幾個送出，不是順位） | 同左 + `noSubmission` |
| 學生 `StudentSubmissions` | 只有本組：每題已送出與否、答案、接收時間；**不含**他組任何欄位、提交數、先後名次 | 全部組的提交、答案、接收時間、先後、`noSubmission`、`judgedWrong`（004 提供） |

`questionShapes`：老師為全部題的格數；學生只有本輪開放題的格數。

## 應用層（`app/round_submission/`）

| 型別 | 說明 |
|---|---|
| `QuestionShapeSource`（Protocol） | `blanks_per_question(code) -> Mapping[int, int] \| None`；002 實作，002 合併前由 `DevQuestionShapeSource` 提供 |
| `SubmissionReader`（Protocol） | 給 004／005：`round_submissions(code, round_number)`、`all_submissions(code)`，回傳排序後的 `tuple[Submission, ...]`（唯讀） |
| `SubmissionStore` | `get(code) -> SubmissionLedger`（沒有時回傳空 ledger）、`put(code, ledger)`；只存在記憶體 |
| `SubmissionService` | `submit(code, device_token, attempt) -> Outcome[SubmissionDecision]`；實作 `SubmissionReader`；建立時向 `ActivityService.add_snapshot_extension` 註冊擴充函式 |

## 對 001 的擴充（研究 R2、R4）

| 位置 | 新增 | 行為 |
|---|---|---|
| `core/activity/commands.py` | `RecordSubmission(actor, group_number)` | 只允許 `System` |
| `core/activity/state_machine.py` | `_record_submission` | 只在 `ROUND_OPEN`、`now < deadline`（有截止時）且組別存在時成功；設 `has_submissions = True`，**每次都算變更**（`revision + 1`；公開狀態不變，`version` 不變） |
| `app/activity/ports.py` | `SubmissionHandler[T]`（`decide(window, now) -> HandlerStep[T]`、`commit() -> None`）、`SnapshotExtension`、`TeacherViewer`、`GroupViewer` | |
| `app/activity/service.py` | `record_submission(code, device_token, handler)`、`add_snapshot_extension(ext)`；`snapshot_for` 改為實例方法 | 見研究 R2 步驟 1～7 |
| `adapters/web/ws_sync.py` | `_push` 改呼叫 `self._service.snapshot_for` | |

## 狀態轉移

003 沒有自己的階段；提交只在 001 的 `ROUND_OPEN` 被接受。關輪（`ROUND_OPEN → RESULT_PENDING`）之後，本輪提交自動成為「已公開」。
