# HTTP API 契約：005-result-export

**用途**：老師預覽並手動寫回定案成果、重新核對與重試、重新授權、下載 CSV。沿用 [001 的 HTTP 契約](../../001-activity-session/contracts/http-api.md) 的共通規則：基底 `http://127.0.0.1:<port>/api`、JSON、`Authorization: Bearer <老師 token>`、錯誤格式 `{"error": {"code", "message"}}`。

**所有端點只限該活動的老師**；學生沒有任何匯出端點，也看不到預覽、寫回狀態與 CSV（原則 V）。寫回結果的狀態另經 001 的快照推送給老師，見 [sync-websocket.md](sync-websocket.md)。

## 端點

| # | 方法與路徑 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|
| X1 | `POST /activities/{code}/export/preview` | `{}` | `200 Preview` | FR-002～FR-006、FR-007 |
| X2 | `POST /activities/{code}/export/writes` | `{"snapshotId": str}` | `200 Attempt` | FR-004、FR-005、FR-007～FR-021 |
| X3 | `POST /activities/{code}/export/writes/{attemptId}/recheck` | `{}` | `200 Attempt` | FR-016 |
| X4 | `POST /activities/{code}/export/writes/{attemptId}/retry` | `{}` | `200 Attempt` | FR-017、FR-019 |
| X5 | `GET /activities/{code}/export/writes/latest` | — | `200 {"attempt": Attempt \| null}` | FR-021 |
| X6 | `POST /activities/{code}/export/authorization` | `{}` | `200 {"authUrl": str}` | FR-010 |
| X7 | `GET /activities/{code}/export/csv` | — | `200 text/csv` 檔案 | FR-022～FR-030 |

- 授權完成後，Google 導回沿用 002 的 `GET /api/oauth/callback`（`302` 到 `/teacher.html?code=…&auth=ok|denied|error`），005 不新增回呼端點。

## 回應形狀

**Preview**（X1）：

```json
{
  "snapshotId": "1.2",
  "canConfirm": true,
  "structure": { "ok": true, "differences": [] },
  "items": [
    {
      "roundNumber": 1, "questionNumber": 3, "subIndex": 1, "groupNumber": 4,
      "answer": "…", "target": "C7", "impact": "REPLACE", "currentDisplay": "（原內容）"
    }
  ],
  "unwrittenQuestions": [2, 5],
  "sheetTitle": "學習單"
}
```

- `target` 是顯示用的 A1 位置（例如 `C7`），由列欄換算；不是寫入用的座標（寫入用 `sheetId` 與索引，不經前端）。
- `impact` 為 `EMPTY`、`REPLACE`、`SAME`；`currentDisplay` 只在 `REPLACE` 有值，後端已截斷至 40 字元。
- 結構不符時 `structure.ok=false`、`canConfirm=false`，`differences` 為 `[{"kind", "row", "col", "detail"}]`（`row`、`col` 為 1 起算的顯示值、欄以字母，無位置時為 `null`，最多回 20 筆並附 `"moreDifferences": int`）。此時 `items` 仍會列出（以匯入時位置顯示），但不可確認。
- `answer`、`currentDisplay`、`sheetTitle` 都是不可信文字，前端一律 `textContent`。
- 沒有已定案且有搶答成功者的題目時不回 Preview，改回 `409 NO_RESULTS`（FR-006）。

**Attempt**（X2～X5）：

```json
{
  "attemptId": 2, "kind": "WRITE", "snapshotId": "1.2",
  "status": "PENDING",
  "reason": "UNKNOWN",
  "totalCells": 12, "confirmedCells": 0, "notWrittenCells": 0, "pendingCells": 12,
  "differences": [],
  "cellChecks": [
    { "questionNumber": 3, "subIndex": 1, "expected": "…", "currentDisplay": "…", "matches": false }
  ],
  "startedAt": "2026-11-24T20:15:30.123+08:00",
  "finishedAt": "2026-11-24T20:16:30.456+08:00",
  "alreadyInProgress": false
}
```

- `status`：`IN_PROGRESS`、`SUCCESS`、`FAILED`、`PENDING`。`reason` 只在 `FAILED`／`PENDING` 有值。
- `cellChecks` 只在 `recheck` 的回應有值（逐格預期與目前內容，FR-016）；其他情況為空陣列。
- `alreadyInProgress=true`：收到寫入請求時已有一次寫入進行中，回覆的是那次進行中的嘗試，沒有開始第二次（FR-020）。
- X2 與 X4 即使 Google 端失敗也回 `200`＋`status=FAILED`／`PENDING`：嘗試已被記錄，老師要看到原因與下一步；只有在「根本沒有開始嘗試」（身分、陳舊快照、沒有成果、已取消……）時才回 4xx。

## 規則

- **X1**：先驗證身分與階段（取消的活動拒絕），再重新讀取來源（結構與目標格目前內容）。不改變任何狀態、不寫入 Google。
- **X2**：`snapshotId` 必須等於目前已定案輪次所決定的識別，否則 `409 STALE_SNAPSHOT`（FR-005）。順序固定：階段與身分 → 快照 → 進行中檢查 → 重新讀取與結構比對 → 寫入 → 記錄結果。結構不符、授權失敗、讀取失敗都在**送出任何寫入之前**停止，記為 `FAILED`（FR-008、FR-010、FR-014）。
- **X3**：只讀取，不寫入、不做結構檢查（clarify Q2）；只能作用在**最新一次**嘗試且該嘗試不在進行中。Google 讀取失敗（授權失效、無權限、網路）時**不改變該嘗試的狀態與格數**，回對應錯誤碼（`NOT_AUTHORIZED`／`AUTH_EXPIRED` 401、`PERMISSION_DENIED` 403、`READ_FAILED` 502），讓老師重新授權後再核對。
- **X4**：使用該嘗試的同一份快照內容；每次都重新讀取並做結構檢查；結果以新的嘗試編號記錄（`kind=RETRY`）；只能作用在最新一次嘗試。對已成功的嘗試重試也允許（冪等，FR-019）。
- **X6**：先做自己的閘門（活動存在、老師、非已取消、Google 連線設定齊備），再呼叫 002 的授權連接埠；在準備中、搶答中、結果階段與已結束都可使用。
- **X7**：不需要 Google 授權；`Content-Type: text/csv; charset=utf-8`、`Content-Disposition: attachment; filename="quiz-results-<活動代碼>.csv"`、`Cache-Control: no-store`；本文以 UTF-8 加 BOM 編碼。沒有已定案輪次時只含表頭列。
- **推送**：每次嘗試狀態改變後，老師快照在 2 秒內更新（FR-021）。X1、X7 不推送。

## 錯誤碼與狀態碼

| `code` | 狀態碼 | 何時 |
|---|---|---|
| `INVALID_REQUEST` | 400 | 本文不是 JSON 物件、`snapshotId` 缺少或不是字串、`attemptId` 不是正整數 |
| `NOT_TEACHER` | 403 | 不是該活動的老師（學生、其他活動的老師、匿名） |
| `ACTIVITY_NOT_FOUND` | 404 | 活動代碼不存在且沒帶 token；帶 token 時依 001 慣例回 `410 ACTIVITY_GONE` |
| `ACTIVITY_CANCELLED` | 409 | 活動已取消：「活動已取消，不提供寫回與 CSV 下載。」 |
| `NO_RESULTS` | 409 | 沒有可寫回的結果（FR-006） |
| `STALE_SNAPSHOT` | 409 | 預覽之後有新輪次定案：「成果已更新，請重新預覽後再確認。」 |
| `ATTEMPT_NOT_FOUND` | 404 | `attemptId` 不存在 |
| `NOT_LATEST_ATTEMPT` | 409 | 只能對最新一次嘗試核對或重試 |
| `WRITE_IN_PROGRESS` | 409 | 核對或重試時該活動仍有寫入進行中 |
| `NO_IMPORT_RECORD` | 409 | 找不到 002 的匯入記錄（防禦用，已有定案輪次時不應發生） |
| `NOT_AUTHORIZED`、`AUTH_EXPIRED` | 401 | X1、X3 時 Google 授權不存在或已失效；訊息指引重新授權 |
| `PERMISSION_DENIED` | 403 | X1、X3 時對該檔案沒有權限 |
| `READ_FAILED` | 502 | X1、X3 時無法讀取來源 |
| `GOOGLE_NOT_CONFIGURED` | 503 | 尚未設定 Google 連線（訊息不含變數名稱） |

- 訊息一律集中在一個對照表，測試逐項檢查**不含** token、授權碼、檔案路徑、堆疊追蹤與他人資料（FR-031）。
- X2、X4 遇到授權、權限、讀取、結構、限流等失敗時**不**回上述 4xx／5xx，而是 `200 Attempt`（`status=FAILED`、`reason` 為 `NOT_AUTHORIZED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`REJECTED`、`RATE_LIMITED`、`STRUCTURE_CHANGED`、`NOT_CONFIGURED`、`READ_FAILED`），因為嘗試已被記錄。

## 日誌

請求日誌沿用 001（路徑樣板、活動代碼、結果碼、狀態碼、耗時）；服務層另記 `activity attempt snapshot cells status reason`。**不記錄**答案、原儲存格內容、試算表網址與標題、token、授權碼（FR-033）。
