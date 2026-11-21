# HTTP API 契約：001-activity-session

**用途**：老師與學生頁面的所有操作。伺服端推送見 [sync-websocket.md](sync-websocket.md)。

## 共通規則

- **基底**：`http://127.0.0.1:<port>/api`，只監聽本機（技術限制 1）。
- **格式**：請求與回應都是 `application/json; charset=utf-8`。
- **身分**：放在 `Authorization: Bearer <token>`。老師用老師 token，學生用裝置 token。
- **重送去重**：所有 `POST`／`DELETE` 都可以帶 `Idempotency-Key: <uuid>`。
  - 同一身分、同一個 key 重送時，直接回傳第一次的回應，不重複套用（FR-018、FR-033）。
  - 前端每次使用者操作都要帶 key；重試時沿用同一個值。
- **錯誤**：一律回傳 `{"error": {"code": "<RejectionReason>", "message": "<可修正的中文說明>"}}`。
  - 狀態碼依 [data-model.md](../data-model.md) 的 RejectionReason 表；活動代碼不存在時回 404。
  - 錯誤回應不含堆疊追蹤、檔案路徑、token 或憑證（原則 V）。
  - 請求格式不符（缺欄位、型別錯誤）回 400，`code` 為 `INVALID_REQUEST`，訊息指出是哪一個欄位。
- **成功的狀態變更**：回應會帶 `version`。前端可以據此判斷之後收到的推送是不是已經涵蓋這次變更。

## 端點

| # | 方法與路徑 | 身分 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|---|
| 1 | `POST /activities` | 無 | `{}` | `201 {"code", "teacherToken", "version"}` | FR-001～003 |
| 2 | `GET /activities/{code}/snapshot` | 老師或裝置 | — | `200 ActivitySnapshot`（依角色裁切） | FR-028 |
| 3 | `POST /activities/{code}/groups/join` | 無或裝置 | `{"name": str, "credential": str \| null}` | `200 {"deviceToken", "groupName", "credential", "version"}` | FR-006～012 |
| 4 | `POST /activities/{code}/groups/leave` | 裝置 | `{}` | `200 {"version"}` | FR-034 ⚠ |
| 5 | `DELETE /activities/{code}/groups/{name}` | 老師 | — | `200 {"version"}` | FR-035 ⚠ |
| 6 | `POST /activities/{code}/rounds` | 老師 | `{"questionNumbers": [int], "fairMode": bool, "countdownSeconds": int \| null}` | `201 {"roundNumber", "deadline" \| null, "version"}` | FR-013～018 |
| 7 | `POST /activities/{code}/rounds/current/close` | 老師 | `{}` | `200 {"roundNumber", "version", "alreadyClosed": bool}` | FR-019 |
| 8 | `POST /activities/{code}/rounds/current/finalize` | 老師 | `{}`（004 會擴充） | `200 {"version"}` | FR-020、FR-021 |
| 9 | `POST /activities/{code}/end` | 老師 | `{}` | `200 {"version", "unsolvedQuestions": [int]}` | FR-022～024 |
| 10 | `POST /activities/{code}/cancel` | 老師 | `{}` | `200 {"version"}` | FR-025 ⚠ |
| 11 | `POST /dev/activities/{code}/seed-questions` | 老師 | `{"count": int}` | `200 {"version"}` | 只在 `LECTURE_QUIZ_DEV_SEED=1` 時存在；002 合併後移除（research R8） |

⚠ 表示受 alignment 待確認提案影響。

## 個別說明

- **#1 建立活動**：`teacherToken` 只在這個回應中出現一次，前端存到 `localStorage["teacher:{code}"]`。用同一個 `Idempotency-Key` 重送時，回傳同一個 `code` 與 `teacherToken`。
- **#2 取得快照**：活動不存在時，例如後端重啟後，回傳 `410 ACTIVITY_GONE`，不回 404。理由是帶著 token 來查詢，代表這個活動曾經存在。沒帶 token 而代碼不存在時，回 404。
- **#3 加入組別**：
  - `name` 會先正規化（去除首尾空白）。
  - **新組名**：建立組別，回傳新的 `credential`。
  - **既有組名**：`credential` 必須等於該組憑證（`secrets.compare_digest`），否則回 `403 BAD_CREDENTIAL`；成功時回傳該組 `credential`。
  - 學生輸入的活動代碼不分大小寫，也忽略首尾空白（FR-001）。
  - 請求已帶有效裝置 token 時，表示這台裝置已經在某一組，回 `409 STAGE_NOT_ALLOWED`，訊息為「請先離開本組」。
- **#5 刪除組別**：`{name}` 經過 URL 編碼，伺服端解碼並正規化後再比對。
- **#6 開輪**：
  - `questionNumbers` 省略或為 `null` 時，視為「全部未成功題」，對應 FR-014 的預設值。前端預設會送出全選的清單。
  - `countdownSeconds` 可以是 `null` 或省略，表示不倒數；不得為小數或字串（⚠ Q-08）。
- **#7 關輪**：輪次已經關過時，回 `200` 並帶 `alreadyClosed: true`，`version` 不變（FR-019）。

## 日誌

每個請求記錄一行 `INFO`：

- **要記錄**：方法、路徑樣板（例如 `/activities/{code}/rounds`）、活動代碼、結果代碼、`version`、耗時。
- **不記錄**：`Authorization` 標頭、請求本文中的 `credential`、回應中的 `teacherToken`、`deviceToken`、`credential`（技術限制 3）。
