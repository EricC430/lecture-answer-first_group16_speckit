# HTTP API 契約：003-round-submission

**用途**：學生送出答案。讀取提交資料一律透過 001 的快照（`GET /activities/{code}/snapshot` 與 WebSocket），見 [sync-websocket.md](sync-websocket.md)。共通規則（基底、格式、身分、錯誤格式）沿用 001 [`http-api.md`](../../001-activity-session/contracts/http-api.md)。

## 端點

| # | 方法與路徑 | 身分 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|---|
| S1 | `POST /activities/{code}/submissions` | 裝置 token | `{"roundNumber": int, "questionNumber": int, "answers": [str, ...]}` | 接受：`201 {"result": "accepted", "submission": Submission}`；本組已送出：`200 {"result": "alreadySubmitted", "submission": Submission}` | FR-001～020、FR-034 |

`Submission`（JSON）：

```json
{
  "roundNumber": 1,
  "questionNumber": 2,
  "groupNumber": 3,
  "answers": ["第 1 格原文", "第 2 格原文"],
  "receivedAt": "2026-11-23T08:00:01.234+00:00"
}
```

接收序號只用於排序，不放進學生可見的回應（spec Assumptions）。

## 規則

- 本文多送的欄位（例如前端時間、自稱的組號）一律**忽略**（`extra="ignore"`），不影響接受與否與接收時間；所屬組別一律由後端依 token 判定（FR-012、FR-015、US3-AS7）。
- `roundNumber`、`questionNumber`、`answers` 的型別錯誤**不**由請求格式驗證擋下，而是原樣交給核心判定（`STALE_ROUND`、`QUESTION_NOT_OPEN`、`INVALID_ANSWER`），讓訊息可修正、判定順序一致（data-model.md「判定順序」）。
- `Idempotency-Key` 可以帶，但不需要：同組同題重送一律回 `alreadySubmitted` 與原提交（FR-010），不會產生第二筆。
- 「本組已送出」不是錯誤：前端顯示既有答案（US2-AS1、US2-AS4）。
- 被拒時不保存、不消耗機會、不推送（FR-005）。

## 錯誤

`{"error": {"code": "<SubmissionRejection>", "message": "..."}}`：

| code | 狀態 | 何時 |
|---|---|---|
| `ACTIVITY_GONE` | 410 | 活動不存在（後端重啟等） |
| `NOT_IN_GROUP` | 403 | token 無效或不屬於任何組 |
| `STALE_ROUND` | 409 | 輪次識別不是目前輪次 |
| `ROUND_CLOSED` | 409 | 不在搶答中、已截止或已關輪 |
| `QUESTION_NOT_OPEN` | 400 | 題號不在本輪開放範圍 |
| `SHAPES_UNAVAILABLE` | 503 | 本輪開放題查不到格數（尚未匯入或格數來源未接上）；不是學生的錯，訊息請稍後再試或請老師確認匯入 |
| `INVALID_ANSWER` | 400 | `answers` 不是字串陣列 |
| `WRONG_BLANK_COUNT` | 400 | 格數不符（訊息含需要的格數） |
| `BLANK_EMPTY` | 400 | 有空格（訊息列出格號） |
| `ANSWER_TOO_LONG` | 400 | 有格子超過 500 字（訊息列出格號） |
| `INVALID_REQUEST` | 400 | 本文不是 JSON 物件，或缺少 `roundNumber`／`questionNumber`／`answers` 欄位 |

訊息不含 token、堆疊追蹤、檔案路徑或他組資料（FR-034）。

## 日誌

沿用 001 的請求日誌（路徑模板、狀態碼、`result=<code>`）；服務層另記 `activity round question group result`，不記 token 與答案（研究 R13）。
