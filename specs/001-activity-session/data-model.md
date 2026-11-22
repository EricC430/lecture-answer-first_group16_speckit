# 資料模型：001-activity-session

**日期**：2026-11-21 | **藍圖**：[`diagrams/001-activity-session-class.puml`](../../diagrams/001-activity-session-class.puml)

## 設計原則

- **核心資料**：核心的資料都是**不可變的** `@dataclass(frozen=True)`，放在 `src/lecture_quiz/core/activity/models.py`。狀態變更一律產生新物件，不就地修改。
- **集合**：集合欄位用 `tuple` 或 `Mapping`（唯讀）。
- **時間**：時間欄位一律是有時區的 `datetime`，由呼叫端傳入，核心不讀取系統時鐘。
- **命名**：類別名稱沿用類別圖；Python 欄位使用 snake_case，例如類別圖的 `joinCredential` 對應 `join_credential`。

## 實體

### Stage（列舉）

| 值 | 中文 | 終止階段 |
|---|---|---|
| `PREPARING` | 準備中 | 否 |
| `ROUND_OPEN` | 搶答中 | 否 |
| `RESULT_PENDING` | 結果未定案 | 否 |
| `RESULT_FINAL` | 結果已定案 | 否 |
| `ENDED` | 已結束 | 是 |
| `CANCELLED` | 已取消（⚠ 提案相依 Q-09） | 是 |

### Activity

| 欄位 | 型別 | 規則 |
|---|---|---|
| `code` | `str` | 6 碼，字元集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`；不與存續中活動重複（由服務層保證） |
| `stage` | `Stage` | 見狀態轉移 |
| `version` | `int` | 從 1 開始，每次成功的狀態變更加 1；無變化的成功（例如重複關輪）不加 |
| `changed_at` | `datetime` | 最近一次狀態變更的時間（R2 量測起點） |
| `teacher` | `TeacherIdentity` | 建立時產生，不可變 |
| `question_numbers` | `tuple[int, ...]` | 由 002 的成功匯入提供；未匯入時為空 |
| `solved_questions` | `frozenset[int]` | 由 004 定案結果提供；必須是 `question_numbers` 的子集 |
| `groups` | `Mapping[str, Group]` | key 為正規化後的組名 |
| `devices` | `Mapping[str, DeviceIdentity]` | key 為裝置 token 的雜湊（見下） |
| `rounds` | `tuple[Round, ...]` | 依輪次編號排序；最後一個是目前輪次 |

**衍生值**：

- `current_round`：`rounds` 的最後一個，沒有時為 `None`。
- `unsolved_questions`：`question_numbers` 減去 `solved_questions`，保留原本的順序。

### TeacherIdentity

| 欄位 | 型別 | 規則 |
|---|---|---|
| `token_hash` | `str` | 只保存 token 的 SHA-256；原始 token 只在建立活動時回傳一次（⚠ 提案相依 Q-04） |

### Group

| 欄位 | 型別 | 規則 |
|---|---|---|
| `name` | `str` | 正規化：去除首尾空白；不可為空；不可含 Unicode 控制字元（`Cc` 類別，例如換行、Tab）；不設長度上限（Q-07） |
| `join_credential` | `str` | 6 碼，字元集同活動代碼（⚠ 提案相依 Q-06）；只出現在本組學生快照與老師快照 |
| `success_count` | `int` | 大於等於 0；只由 `finalize(outcome)` 增加 |
| `has_submissions` | `bool` | 由 003 經 `mark_group_submitted` 設為 `True`，之後不會變回 `False`（⚠ 提案相依：刪除空組） |

### DeviceIdentity

| 欄位 | 型別 | 規則 |
|---|---|---|
| `token_hash` | `str` | 裝置 token 的 SHA-256 |
| `group_name` | `str` | 指向 `groups` 中的組別；組別被刪除或裝置離開時，這筆資料會被移除 |

老師不使用 `DeviceIdentity`，而是以 `TeacherIdentity` 判定。

### Round

| 欄位 | 型別 | 規則 |
|---|---|---|
| `number` | `int` | 從 1 開始連續遞增 |
| `rules` | `RoundRules` | 開輪後不可變 |
| `opened_at` | `datetime` | 開輪時的 `now` |
| `baseline` | `Mapping[str, int]` | 開輪當下各組的 `success_count` 快照 |
| `closed` | `bool` | 只能由 `False` 變成 `True`，而且只能一次 |
| `closed_at` | `datetime \| None` | 關輪時的 `now` |
| `close_cause` | `Literal["teacher", "deadline"] \| None` | 記錄先生效的關輪來源 |

### RoundRules

| 欄位 | 型別 | 規則 |
|---|---|---|
| `question_numbers` | `tuple[int, ...]` | 至少 1 題；每題都在 `Activity.question_numbers` 中，而且不在 `solved_questions` 中；不得重複 |
| `fair_mode` | `bool` | 預設 `False` |
| `countdown_seconds` | `int \| None` | `None` 表示不倒數；否則為 1～3600 的整數（⚠ 提案相依 Q-08） |
| `deadline` | `datetime \| None` | `opened_at + countdown_seconds`；沒有倒數時為 `None` |

### Command（核心輸入）

各種操作都是不同的 frozen dataclass，共用欄位是 `actor`：

- **`actor` 的型別**：`Teacher(token_hash)`、`Device(token_hash)`、`System`（倒數排程）或 `Anonymous`。
- **操作清單**：`CreateActivity`、`JoinGroup(name_raw, credential_raw)`、`LeaveGroup`、`DeleteGroup(name)`、`OpenRound(question_numbers, fair_mode, countdown_raw)`、`CloseRound`、`Finalize(outcome)`、`EndActivity`、`CancelActivity`、`ReplaceQuestions(question_numbers)`、`MarkGroupSubmitted(group_name)`。
- **身分由服務層解析**：服務層把 HTTP 請求中的 token 轉成雜湊後，才放進 `actor`。核心只比對雜湊，不接觸原始 token。

### Transition（核心輸出）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `ok` | `bool` | 是否成功 |
| `activity` | `Activity` | 成功時為新狀態；失敗或無變化時為原狀態 |
| `changed` | `bool` | 是否真的改變（決定版本是否加 1、是否推送） |
| `rejection` | `RejectionReason \| None` | 失敗原因 |
| `issued` | `IssuedSecrets \| None` | 這次操作新產生、要回傳給請求者一次的秘密（新組憑證、裝置 token）；**由服務層產生後傳入**，核心不產生亂數 |

### RejectionReason（列舉，與類別圖一致）

| 值 | 類別圖名稱 | HTTP | 使用者訊息範例（語意需與 OpenSpec 一致，Q-03） |
|---|---|---|---|
| `NOT_TEACHER` | 非老師 | 403 | 需要這個活動的老師身分才能操作。 |
| `STAGE_NOT_ALLOWED` | 階段不允許 | 409 | 目前是「結果未定案」，請先確認定案本輪結果。（依階段與操作組合產生） |
| `NO_QUESTIONS` | 未匯入題目 | 409 | 請先成功匯入學習單，再開始搶答。 |
| `INVALID_SELECTION` | 選題無效 | 400 | 請至少選擇一題尚未有人答對的題目。 |
| `INVALID_COUNTDOWN` | 倒數秒數無效 | 400 | 倒數秒數須為 1～3600 的整數。 |
| `INVALID_GROUP_NAME` | 組名無效 | 400 | 組名不能是空白，也不能包含換行或 Tab。 |
| `BAD_CREDENTIAL` | 憑證錯誤 | 403 | 此組名已被使用；若你是這一組的成員，請向同組同學查看本組加入憑證，否則請換一個組名。 |
| `ACTIVITY_GONE` | 活動已失效 | 410 | 活動已失效，請重新建立或加入活動。 |
| `RULES_LOCKED` | 規則不可修改 | 409 | 本輪進行中，題目、模式與截止時間不能修改。 |
| `NO_GROUP_SWITCH_DURING_ROUND` | 搶答中不可換組 | 409 | 搶答進行中不能換組，請在本輪關閉後再操作，這段期間可以用同組同學的裝置作答。 |
| `GROUP_HAS_SUBMISSIONS` | 組別已有提交 | 409 | 此組已有作答紀錄，不能刪除。 |

「活動代碼不存在」由服務層在找不到活動時處理，回傳 404：「找不到這個活動代碼，請確認後再輸入。」錯誤回應只含 `code` 與 `message`，不含堆疊追蹤、路徑或任何憑證（原則 V）。

### ActivitySnapshot（推送與查詢的內容）

由 `SnapshotView.for_teacher` 或 `SnapshotView.for_group` 產生。欄位定義見 [contracts/sync-websocket.md](contracts/sync-websocket.md)。

- **學生版**：只含本組的組名、憑證與成功次數。**不含**其他組的名稱、數量、憑證或任何進度（FR-030；保守做法：學生連組數都看不到，避免推知他組狀態）。
- **老師版**：含全部組別與憑證。

## 狀態轉移

藍圖是 spec 的「活動階段狀態機」與時序圖。核心函式 `ActivityStateMachine.apply(activity, command, now)` 依序檢查下列條件，第一個不成立的就回傳該拒絕原因：

1. **活動是否還在**：活動在終止階段時，除了查詢以外，一律回傳 `STAGE_NOT_ALLOWED`。訊息依階段寫成「活動已結束」或「活動已取消」。
2. **權限**：老師專用操作要求 `actor` 是本活動的 `Teacher`，否則回傳 `NOT_TEACHER`。
3. **階段與操作是否相容**：依 spec 的兩張表判定。
4. **輸入**：組名、憑證、選題、倒數秒數，由 `InputRules` 驗證。
5. **業務條件**：例如是否已匯入題目、所選題目是否都未成功、組別是否有提交。

| 操作 | 允許的階段 | 成功後 |
|---|---|---|
| `CreateActivity` | （無） | `PREPARING`，version = 1 |
| `ReplaceQuestions`（002） | `PREPARING` | 更新 `question_numbers`；`solved_questions` 清空 |
| `JoinGroup` | 非終止 | 新組：建立 `Group`＋裝置；既有組：憑證正確時新增裝置 |
| `LeaveGroup` | `PREPARING`、`RESULT_PENDING`、`RESULT_FINAL` | 移除該裝置 |
| `DeleteGroup` | 非終止 | `has_submissions == False` 時，移除組別與其所有裝置 |
| `OpenRound` | `PREPARING`（已有題目）、`RESULT_FINAL` | `ROUND_OPEN`，新增 `Round` |
| `CloseRound` | `ROUND_OPEN`；目前輪次已關時（`RESULT_PENDING`、`RESULT_FINAL`）視為冪等 | `RESULT_PENDING`，`closed = True`；目前輪次已經關過時，回傳成功但沒有變化（`changed=False`，HTTP `alreadyClosed: true`） |
| `Finalize` | `RESULT_PENDING` | `RESULT_FINAL`；套用 `outcome`（已成功題、各組成功次數增量） |
| `EndActivity` | `RESULT_FINAL` | `ENDED` |
| `CancelActivity` | `PREPARING` | `CANCELLED` |
| `MarkGroupSubmitted`（003） | `ROUND_OPEN` | 該組 `has_submissions = True` |

**倒數截止**：`System` 送出的 `CloseRound`，只有在 `deadline` 不為 `None` 且 `now >= deadline` 時才生效；否則回傳成功但沒有變化。這是為了防止排程誤觸發。服務層的倒數回呼一律以 `now = max(clock.now(), deadline)` 呼叫（研究 R6）。`ActivityStateMachine.is_deadline_passed(round, now)` 是供 003 判斷「截止後才到的提交」用的純函式。
