# 服務介面契約：001 提供給 002～005

**用途**：其他子功能在 Python 程式內呼叫 `ActivityService`，不經過 HTTP。以 `typing.Protocol` 定義，放在 `src/lecture_quiz/app/activity/ports.py`。

這些名稱沿用 002 類別圖的 `ActivityGateway`，以及 001 類別圖的 `ActivityService`。所有方法都是 `async`，進入該活動的鎖（研究 R6），並在狀態改變後觸發推送。

## 共通型別

- **`Requester`**：服務層解析後的身分，只會是 `Teacher(code, token_hash)`、`Device(code, token_hash)` 或 `Anonymous` 其中之一。HTTP 層負責把 token 轉成 `Requester`。
- **`Outcome[T]`**：回傳值，`ok: bool`、`value: T | None`、`rejection: RejectionReason | None`。服務**不會拋出業務錯誤**，只有程式錯誤才拋例外。

## 給 002（Guided Notes 匯入）：`ActivityGateway`

| 方法 | 說明 |
|---|---|
| `stage(code) -> Stage` | 目前階段；活動不存在時回傳 `None` |
| `is_teacher(code, requester) -> bool` | `requester` 是否為該活動老師 |
| `replace_questions(code, requester, question_numbers: tuple[int, ...]) -> Outcome[int]` | 只允許老師在第一輪開始前（`PREPARING`、`JOINING`）呼叫，以整份新題號取代舊的；回傳新 `version`。被拒時，既有題目完全不變（原則 III） |

**與 002 類別圖的差異**：002 類別圖寫的是 `stage()`、`isTeacher(requester)`、`replaceQuestions(result)`。這裡多了 `code` 參數，因為後端會同時有多個活動；而且 `replaceQuestions` 只接收題號清單，不接收整個 `ParseResult`。

- 來源映射與匯入時結構由 002 自己保存，001 只需要知道有哪些題號。
- 002 整合時，請在 002 的類別圖補上 `code` 參數。這一點會在 002 的 PR 中協調。

## 給 003（輪次提交）

| 方法 | 說明 |
|---|---|
| `resolve_device(code, device_token) -> Outcome[DeviceContext]` | 回傳 `group_number`、`stage`、`round_number`、`open_questions`、`deadline`；所屬組別一律由後端判定（FR-012） |
| `accepts_submission(code, now) -> bool` | `stage == ROUND_OPEN`，而且沒有截止時間，或 `now < deadline`；用 `ActivityStateMachine.is_deadline_passed` 判斷 |
| `mark_group_submitted(code, group_number) -> Outcome[int]` | 標記該組有提交紀錄，用於「刪除空組」的判定（alignment 2026-11-23 B5）。只在 `ROUND_OPEN` 生效；與刪除組別在同一把活動鎖內處理，所以「標記」與「刪除」只會有一個先生效。**003 必須先呼叫本方法，成功後才寫入答案；被拒（例如 `GROUP_NOT_FOUND`、`STAGE_NOT_ALLOWED`）就不寫入**。照這個順序，才不會出現「答案已記錄但組別被刪除」（2026-11-23 依 PR #15 第三次審查第 3 項修正：原文把這個保證寫成 001 單方面提供，但 001 只保證標記與刪除互斥，寫入答案的順序要由 003 遵守） |

## 給 004（順位與定案）

| 方法 | 說明 |
|---|---|
| `current_round(code) -> Round \| None` | 包含 `rules` 與 `baseline`（公平模式要用的歷史成功次數基準） |
| `finalize(code, requester, outcome: FinalizeOutcome) -> Outcome[int]` | 只允許老師在 `RESULT_PENDING` 時呼叫。`FinalizeOutcome` 有兩個欄位：`solved_questions: frozenset[int]`（本輪新成功的題號）、`success_increments: Mapping[int, int]`（各組成功次數增量，key 為組號）。004 的前提檢查（例如判錯審閱）由 004 在呼叫前自行完成 |

## 給 005（結果匯出）

| 方法 | 說明 |
|---|---|
| `export_view(code, requester) -> Outcome[ExportView]` | 只限老師。`CANCELLED` 一律拒絕（alignment 2026-11-23 C8）；其他階段是否可以匯出，由 005 依 result-export 規格判定，001 不限制。回傳組別（依組號排序，已刪除的空組不在其中）、題號、已成功題、未成功題與目前階段 |
