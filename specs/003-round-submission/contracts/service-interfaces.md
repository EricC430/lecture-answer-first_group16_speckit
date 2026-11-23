# 服務介面契約：003 與 001／002／004／005

**用途**：Python 程式內的介面，不經過 HTTP。以 `typing.Protocol` 定義。

## 003 使用 001 的介面（001 新增，研究 R2、R4）

| 方法 | 說明 |
|---|---|
| `ActivityService.record_submission(code, device_token, handler: SubmissionHandler[T]) -> Outcome[T]` | 在該活動的鎖內：找裝置（`NOT_IN_GROUP`／`ACTIVITY_GONE`）→ `now = clock.now()` → 組 `SubmissionWindow` → `handler.decide(window, now)` → 若為接受：套用 `RecordSubmission`（失敗就不呼叫 `commit`）→ `handler.commit()` → 鎖外推送 |
| `SubmissionHandler.decide(window, now) -> HandlerStep[T]` | 003 實作；`HandlerStep` 為 `accept(value)`、`no_change(value)` 或 `reject(reason, message)`；**不得有副作用** |
| `SubmissionHandler.commit() -> None` | 003 實作；只在 `RecordSubmission` 成功後、仍在鎖內被呼叫，把新的 ledger 寫入 store |
| `ActivityService.add_snapshot_extension(ext: SnapshotExtension)` | 註冊快照擴充；`ext(activity, viewer) -> Mapping[str, object]`，回傳的欄位併入快照 `extra`，可覆寫 001 的欄位（003 只覆寫學生搶答中的 `ownGroup.successCount`） |
| `ActivityService.snapshot_for(activity, requester)` | 改為實例方法；`WebSocketHub` 與 `snapshot()` 都經過它，擴充自動生效 |
| `mark_group_submitted(code, group_number)` | 保留不變；003 不直接呼叫（`record_submission` 內部以 `RecordSubmission` 達成同樣保證：先標記、成功才保存） |

## 003 使用 002 的介面（由 002 實作）

| 方法 | 說明 |
|---|---|
| `QuestionShapeSource.blanks_per_question(code) -> Mapping[int, int] \| None` | 題號 → 子空格數（單題為 1），來自最後一次成功匯入；尚未匯入時為 `None`。002 的 `ImportService` 以 `ImportRecord.blanks` 計數實作（2026-11-23 與 EricC430 口頭協調）。002 合併前由 `DevQuestionShapeSource`（dev seed）提供 |

## 003 提供給 004、005（`SubmissionReader`）

| 方法 | 說明 |
|---|---|
| `round_submissions(code, round_number) -> tuple[Submission, ...]` | 該輪全部有效提交，依（`received_at`, `sequence`）排序；給 004 計算候選順位、暫定勝者與判錯 |
| `all_submissions(code) -> tuple[Submission, ...]` | 全部輪次的有效提交，同樣排序；給 005 匯出 |

- 回傳不可變物件，004、005 無法修改提交（FR-036）。
- 判錯標記屬於 004；004 若要在快照中顯示判錯，另行註冊快照擴充或擴充 003 的公開版資料（004 plan 決定）。

## 純函式邊界（給架構測試）

- `core/round_submission/` 只能匯入標準函式庫與 `lecture_quiz.core`；不得匯入 `fastapi`、`starlette`、`asyncio`、`time` 等，也不得呼叫 `datetime.now`。
- `SubmissionRules.decide(ledger, context, code, attempt, now)` 的時間由呼叫端傳入；接收序號取自 `ledger.next_sequence`。
