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
- **成功的狀態變更**：回應會帶 `version`（學生可見的狀態版本）。前端可以據此判斷之後收到的推送是不是已經涵蓋這次變更。組別加入、離開、刪除不改變 `version`，回應中的值與操作前相同（FR-030）。

## 端點

| # | 方法與路徑 | 身分 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|---|
| 1 | `POST /activities` | 無，或同瀏覽器上一個活動的老師 token（C7） | `{"maxGroups": int}` | `201 {"code", "teacherToken", "maxGroups", "version"}` | FR-001～003、FR-036、FR-037 |
| 2 | `GET /activities/{code}/snapshot` | 老師或裝置 | — | `200 ActivitySnapshot`（依角色裁切） | FR-028 |
| 3 | `POST /activities/{code}/groups/join`（準備中回 `409 JOIN_NOT_OPEN`；既有組號一律要憑證；最後一台裝置離開且從未提交的組號已釋放，視為新組號） | 無或裝置 | `{"groupNumber": int \| str, "credential": str \| null}` | `200 {"deviceToken", "groupNumber", "credential", "version"}` | FR-006～012 |
| 4 | `POST /activities/{code}/groups/leave` | 裝置 | `{}` | `200 {"version"}` | FR-034 |
| 5 | `DELETE /activities/{code}/groups/{number}`（搶答中回 `409 GROUP_DELETE_DURING_ROUND`） | 老師 | — | `200 {"version"}` | FR-035 |
| 6 | `POST /activities/{code}/rounds` | 老師 | `{"questionNumbers": [int], "fairMode": bool, "countdownSeconds": int \| null}` | `201 {"roundNumber", "deadline" \| null, "version"}` | FR-013～018 |
| 7 | `POST /activities/{code}/rounds/current/close` | 老師 | `{}` | `200 {"roundNumber", "version", "alreadyClosed": bool}` | FR-019 |
| 8 | `POST /activities/{code}/rounds/current/finalize` | 老師 | 由 004 提供，見 `specs/004-ranking-review/contracts/http-api.md` R2（本文 `{"resultVersion"}`） | `200 {"version", "resultVersion", "alreadyFinalized"}` | FR-020、FR-021 |
| 9 | `POST /activities/{code}/end` | 老師 | `{}` | `200 {"version", "unsolvedQuestions": [int]}` | FR-022～024 |
| 10 | `POST /activities/{code}/cancel` | 老師 | `{}` | `200 {"version"}` | FR-025 |
| 12 | `POST /activities/{code}/open-joining` | 老師 | `{}` | `200 {"version"}`；沒有題目時 `409 NO_QUESTIONS` | FR-038 |
| 11 | `POST /dev/activities/{code}/seed-questions` | 老師 | `{"count": int}` | `200 {"version"}` | **已移除（2026-11-23，於 002 實作分支）**；原僅在 `LECTURE_QUIZ_DEV_SEED=1` 時存在（research R8） |

所有偏離與新增行為已於 alignment 2026-11-23 獲 OpenSpec 組確認。

## 個別說明

- **#1 建立活動**：
  - `maxGroups` 原樣交給核心驗證，不是 1～99 的整數時回 `400 INVALID_MAX_GROUPS`。
  - `teacherToken` 只在這個回應中出現一次，前端存到 `localStorage["teacher:{code}"]`，並把 `localStorage["teacher:last"]` 設為這個 `code`。用同一個 `Idempotency-Key` 重送時，回傳同一個 `code` 與 `teacherToken`。
  - **C7**：前端建立新活動時，附上 `teacher:last` 那個活動的老師 token。該活動仍存續（非已結束、非已取消）時回 `409 TEACHER_HAS_ACTIVE_ACTIVITY`，訊息含該活動代碼；找不到活動（例如後端已重啟）或已終止時照常建立（研究 R10）。
- **#2 取得快照**：活動不存在時，例如後端重啟後，回傳 `410 ACTIVITY_GONE`，不回 404。理由是帶著 token 來查詢，代表這個活動曾經存在。沒帶 token 而代碼不存在時，回 404。
- **#3 加入組別**：
  - `groupNumber` 原樣交給核心的 `InputRules.normalize_group_number`：可以是整數，或由半形／全形數字組成的字串（可有前導零與首尾空白）；轉換後不是 1～N 時回 `400 INVALID_GROUP_NUMBER`，訊息為「組號須為 1～N 的整數」。
  - **新組號**：建立組別，回傳新的 `credential`。
  - **既有組號**：`credential` 去除首尾空白並轉大寫後，必須等於該組憑證（`hmac.compare_digest`），否則回 `403 BAD_CREDENTIAL`；成功時回傳該組 `credential`。
  - 學生輸入的活動代碼不分大小寫，也忽略首尾空白（FR-001）。
  - 請求已帶有效裝置 token 時，表示這台裝置已經在某一組，回 `409 ALREADY_IN_GROUP`，訊息為「這台裝置已經在第 n 組，請先離開本組」。
- **#4 離開本組**：沒有帶有效裝置 token 時回 `403 NOT_IN_GROUP`；搶答中回 `409 NO_GROUP_SWITCH_DURING_ROUND`。成功後，該裝置的 WebSocket 收到 `unauthorized`（`reason: LEFT_GROUP`）並被關閉。
- **#5 刪除組別**：`{number}` 原樣交給 `normalize_group_number`；組別不存在回 `404 GROUP_NOT_FOUND`，有提交紀錄回 `409 GROUP_HAS_SUBMISSIONS`。成功後，原組裝置的 WebSocket 收到 `unauthorized`（`reason: GROUP_DELETED`）並被關閉。
- **#6 開輪**：
  - `questionNumbers` 省略或為 `null` 時，視為「全部未成功題」，對應 FR-014 的預設值。前端預設會送出全選的清單。
  - `countdownSeconds` 可以是 `null` 或省略，表示不倒數；不得為小數或字串（alignment 2026-11-23 C9）。
- **#7 關輪**：輪次已經關過時，回 `200` 並帶 `alreadyClosed: true`，`version` 不變（FR-019）。

## 日誌

每個請求記錄一行 `INFO`：

- **要記錄**：方法、路徑樣板（例如 `/activities/{code}/rounds`）、活動代碼、結果代碼、`version`、耗時。
- **不記錄**：`Authorization` 標頭、請求本文中的 `credential`、回應中的 `teacherToken`、`deviceToken`、`credential`（技術限制 3）。
  - **由 007 修訂（2026-11-26）**：#3 的回應移除 `deviceToken`，加入時必須有瀏覽器金鑰（cookie 或 Bearer），沒有時回 `400 BROWSER_SESSION_REQUIRED`；`ALREADY_IN_GROUP` 訊息改為「這個瀏覽器已是第 n 組成員，請先離開本組。」；學生請求的身分取自 `lq_browser` cookie（Bearer 優先）。日誌同樣不記錄 cookie。新增 `POST /api/browser-session`。詳見 `specs/007-browser-identity-sync/contracts/http-and-sync-changes.md`。
