# HTTP API 契約：002-guided-notes-import

**用途**：老師頁面的 Google 授權、選檔、選工作表與匯入。沿用 [001 的 HTTP 契約](../../001-activity-session/contracts/http-api.md)（位於 `feature/5-001-activity-session` 分支，合併後以 main 為準）的共通規則：基底 `http://127.0.0.1:<port>/api`、JSON、`Authorization: Bearer <老師 token>`、`Idempotency-Key`、錯誤格式 `{"error": {"code", "message"}}`。

所有端點**只限該活動的老師**（回呼端點除外，它以 `state` 驗證）。學生沒有任何匯入端點，也看不到來源映射與結構（原則 V）。

## 端點

| # | 方法與路徑 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|
| 1 | `POST /activities/{code}/import/auth/start` | `{}` | `200 {"authUrl": str}` | FR-001 |
| 2 | `GET /oauth/callback?code=…&state=…`（Google 導回） | — | `302` 導回 `/teacher.html?code=<活動代碼>&auth=ok\|denied\|error` | FR-001、FR-003 |
| 3 | `GET /activities/{code}/import/auth/status` | — | `200 {"authorized": bool}` | FR-003 |
| 4 | `GET /activities/{code}/import/picker-config` | — | `200 {"accessToken", "apiKey", "appId"}`，`Cache-Control: no-store` | FR-001 |
| 5 | `POST /activities/{code}/import/source/inspect` | `{"spreadsheetId": str}` | `200 {"spreadsheetId", "title", "sheets": [{"sheetId": int, "title": str}], "autoSelectSheetId": int \| null}` | FR-002、FR-005 |
| 6 | `PUT /activities/{code}/import/source` | `{"spreadsheetId": str, "sheetId": int}` | `200 {"spreadsheetId", "sheetId", "sheetTitle"}` | FR-002 |
| 7 | `POST /activities/{code}/import` | `{}`（使用 #6 記住的來源） | `200 ImportResult` | FR-015～FR-019、FR-027 |
| 8 | `GET /activities/{code}/import` | — | `200 ImportResult \| {"imported": false}` | FR-017 |

- **`ImportResult`**：`{"imported": true, "sheetTitle": str, "questionNumbers": [int], "blanksPerQuestion": {"<題號>": int}, "totalQuestions": int, "totalBlanks": int, "version": int}`。`version` 是 001 `replace_questions` 回傳的新版本。
- **#2 回呼**是瀏覽器導向，不是 fetch；它以 `state` 找回活動代碼與老師身分，不需要 `Authorization` 標頭。`state` 只能用一次、有有效期限；不符、過期、重複使用都導回 `auth=error`，且**不交換 token**。
- **#4**：access token 只含 `drive.file` 範圍，只回給該活動老師，且**不寫入日誌**。
- **#5 inspect**：不改任何狀態；用來列出工作表。檔案不是 Google 試算表回 `NOT_A_SPREADSHEET`。**`autoSelectSheetId` 由後端決定**：`sheets` 恰好一張時為該張的 `sheetId`，否則為 `null`（FR-002）。前端只依它行事，不自己數工作表。
- **#6**：只在驗證所選 `sheetId` 屬於該試算表之後才寫入；失敗時舊的選定來源不變。前端在 `autoSelectSheetId` 有值時自動呼叫它，否則等老師明確選一張（FR-002）。
- **#7**：流程與順序見 [research.md](../research.md) R6。成功時回傳 `ImportResult`；驗證失敗回 422 並附 `issues`。
- **#8**：頁面重新整理後恢復預覽用；沒有匯入過回 `{"imported": false}`。

## 錯誤碼與狀態碼

| `code`（`ImportRejection`） | 狀態碼 | 附加欄位 |
|---|---|---|
| `INVALID_REQUEST` | 400 | `message` 指出欄位 |
| `NOT_TEACHER` | 403 | — |
| `ACTIVITY_NOT_FOUND` | 404（有帶 token 時依 001 慣例 410 `ACTIVITY_GONE`） | — |
| `NOT_AUTHORIZED`、`AUTH_EXPIRED` | 401 | — |
| `AUTH_DENIED` | 403 | — |
| `PERMISSION_DENIED` | 403 | — |
| `NOT_A_SPREADSHEET` | 422 | — |
| `SHEET_NOT_FOUND`、`SOURCE_NOT_SELECTED` | 422 | — |
| `VALIDATION_FAILED` | 422 | `issues: [{"kind", "row", "col", "quoted", "hint"}]`；`row`、`col` 是 1 起算的顯示值（欄以 A、B… 字母表示），無位置時為 `null` |
| `ROUND_STARTED`、`ACTIVITY_CANCELLED`、`STAGE_NOT_PREPARING`、`GATEWAY_REJECTED` | 409 | — |
| `READ_FAILED` | 502 | — |
| `GOOGLE_NOT_CONFIGURED` | 503 | `message` 只說「尚未設定 Google 連線」，不含變數名稱 |

- 訊息文字固定在一個對照表，測試逐項檢查不含 token、授權碼、檔案路徑、堆疊（FR-022、SC-005）。
- `issues[].quoted` 是來自試算表的文字，前端必須以 `textContent` 輸出；後端已截斷至 40 字元。
- 同一個 `Idempotency-Key` 重送 #7 時，回傳第一次的結果，不重複匯入。

## 日誌

只記錄：活動代碼、端點名稱、結果代碼、成功時的題數與格數、001 版本。**不記錄** token、授權碼、`state`、client secret、試算表標題與儲存格內容（技術限制 3、原則 V）。
