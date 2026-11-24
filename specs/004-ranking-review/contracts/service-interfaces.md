# 服務介面契約：004 與 001／003／005

**用途**：Python 程式內的介面，不經過 HTTP。以 `typing.Protocol` 定義（004 自己的放在 `src/lecture_quiz/app/ranking_review/ports.py`）。名稱沿用 004 類別圖。

## 004 使用 001 的介面（已存在，不新增）

| 方法 | 說明 |
|---|---|
| `ActivityService.get(code) -> Activity \| None` | 取得活動（階段、輪次、`Round.rules`、`Round.baseline`、`groups`） |
| `ActivityService.is_teacher(code, requester) -> bool` | 是否為該活動老師 |
| `ActivityService.resolve_requester(code, token) -> Requester` | HTTP 層把 token 轉成身分 |
| `ActivityService.finalize(code, requester, outcome: FinalizeOutcome, idempotency_key=None) -> Outcome[int]` | 只允許老師在「結果未定案」呼叫；`FinalizeOutcome(solved_questions: frozenset[int], success_increments: Mapping[int, int])`，key 為組號；成功回傳新的活動 `version`。001 在自己的鎖內套用成功題與成功次數增量 |
| `ActivityService.add_snapshot_extension(extension)` | 註冊快照擴充；`extension(activity, viewer) -> Mapping[str, object]`，回傳併入快照頂層（`ranking`） |
| `SyncPublisher.publish(activity)` | 推送最新快照給所有連線（001 的 `WebSocketHub`） |

- 004 **不呼叫** `ActivityService.mark_group_submitted`、`record_submission`；也不修改 001 的核心與服務。
- 001 的 `finalize` 對已定案輪次會以階段不符拒絕；所以重複確認由 004 用自己的定案紀錄冪等處理，不再呼叫 001。
- 004 對 001 唯一的改動：移除 HTTP 層預留的空 finalize 路由（研究 R7）。

## 004 使用 003 的介面（`SubmissionReader`，已合併到 main，PR #16）

| 方法 | 說明 |
|---|---|
| `SubmissionReader.round_submissions(code, round_number) -> tuple[Submission, ...]` | 該輪全部有效提交，依（`received_at`, `sequence`）排序、不可修改；`Submission` 含 `round_number`、`question_number`、`group_number`、`answers`（原文）、`received_at`、`sequence` |

- 004 只取 `group_number`、`question_number`、`received_at`、`sequence` 轉成核心的 `Candidate`；答案不進核心。
- 003 保證關輪後不再有新提交（003 FR-019），所以關輪後任何時間讀到的提交集合都相同（研究 R2）。

## 004 提供的介面

### `RankingService`（給 HTTP 層）

| 方法 | 說明 |
|---|---|
| `await mark_wrong(code, requester, round_number, question_number, group_number) -> Outcome[MarkResult]` | 判錯；`MarkResult(changed, result_version, affected_questions)` |
| `await unmark_wrong(...)` | 撤銷判錯，參數與回傳同上 |
| `await finalize(code, requester, result_version) -> Outcome[FinalizeResult]` | 確認定案；`FinalizeResult(version, result_version, already_finalized)` |

- 服務**不拋業務錯誤**；失敗時 `Outcome.ok=False`、`rejection` 為 004 的 `ReviewRejection`（HTTP 狀態與訊息見 research R12）。只有程式錯誤才拋例外。
- 三個方法都在 004 的每活動鎖內判定與寫入，推送在鎖外（研究 R1、R4）。

### `RankingReader`（給 005）

| 方法 | 說明 |
|---|---|
| `finalized_rounds(code) -> tuple[FinalizedRound, ...]` | 已定案輪次依輪次遞增；每筆含 `round_number` 與 `FinalizedResult`（各題全部候選的 `rank`、`judgedWrong`、`display_status`、`success_group`，及 `final_counts`、`solved_questions`） |

- 回傳不可變物件，005 無法修改結果；005 **不得重新計算**順位或勝負（005 FR-025）。
- 只有「已定案」的輪次會出現；未定案輪次與搶答中的輪次不會被回傳（005 FR-023）。
- 被判錯的提交 `rank` 為 `None`；未成功的候選（排名 2、3…）`rank` 為其名次、`display_status` 為 `FAILED`。005 用它填 CSV 的「順位」「是否成功」「是否被判錯」。

### 快照擴充（給 001 的快照機制）

`RankingService.snapshot_extension(activity, viewer) -> Mapping[str, object]`：依 `TeacherViewer`／`GroupViewer` 回傳 `{"ranking": ...}`（形狀見 [sync-websocket.md](sync-websocket.md)）；沒有已關輪的輪次時回傳空 mapping。

## 組裝（`main.py`）

```text
ranking_service = RankingService(
    activity_service,                 # 001
    submission_service,               # 003：實作 SubmissionReader
    ReviewStore(),
    sync_hub,                         # SyncPublisher
)
app.state.ranking_service = ranking_service
api.include_router(ranking_review.create_router(app))  # 004，只加這一行
```

建構時會向 `activity_service.add_snapshot_extension` 註冊擴充（與 003 相同做法）。

## 純函式邊界（給架構測試）

- `core/ranking_review/` 只能匯入標準函式庫與 `lecture_quiz.core`；不得匯入 `fastapi`、`starlette`、`asyncio`、`time`，也不得呼叫 `datetime.now`。
- `RankingCalculator.recompute(input, order)` 與 `RoundReviewRules` 的所有時間資料都來自 `Candidate.received_at`（已保存的後端接收時間）。
