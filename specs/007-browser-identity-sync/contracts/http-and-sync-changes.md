# Contract: 007 對 001 HTTP API 與 WebSocket 同步的修改

基準文件：`specs/001-activity-session/contracts/http-api.md`、`sync-websocket.md`。這裡只列出 007 改動的部分，其餘照舊。實作時要同步修改這兩份 001 契約，並在對應位置加註「由 007 修訂」。

## 1. 新增 `POST /api/browser-session`

| 項目 | 內容 |
|---|---|
| 用途 | 確保這個瀏覽器有瀏覽器金鑰（research R3） |
| 身分 | 不需要 |
| 請求本文 | 無 |
| 回應 | 一律回 `204 No Content`，本文為空 |
| Set-Cookie | 只有在請求**沒有**帶格式正確的 `lq_browser` 時才設定：`lq_browser=<金鑰>; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400`。已經有金鑰時不送 `Set-Cookie`，也不延長期限 |
| 冪等 | 是。帶著同一把 cookie 重複呼叫，結果都相同 |
| 日誌 | 只記錄方法、路徑與狀態碼，不記錄 cookie |

## 2. 請求者身分的來源（所有 `/api/activities/...` 端點）

`Token` dependency 改為 `request_token`（research R4）：

1. `Authorization: Bearer <token>` 存在時用它（老師 token；測試的裝置 token）。
2. 沒有時讀 `lq_browser` cookie，格式不符就當成沒有。
3. 兩者都沒有時視為匿名。

002～005 import 的是同一個 `Token`，它們的端點行為會自動改成「學生靠 cookie」，不需要個別修改。

## 3. `POST /api/activities/{code}/groups/join`（001 #3）的修改

| 項目 | 001 | 007 |
|---|---|---|
| 需要的身分 | 無或裝置 | **必須有瀏覽器金鑰**（cookie 或 Bearer）。都沒有時回 `400 BROWSER_SESSION_REQUIRED`（不呼叫服務層，狀態不變） |
| 成功回應 | `200 {"deviceToken", "groupNumber", "credential", "version"}` | `200 {"groupNumber", "credential", "version"}`，**移除 `deviceToken`**（FR-008） |
| 已是成員 | `409 ALREADY_IN_GROUP`「這台裝置已經在第 n 組，請先離開本組」 | `409 ALREADY_IN_GROUP`「這個瀏覽器已是第 n 組成員，請先離開本組。」；同時加入時落敗的請求也回這個（核心 INV-1） |
| 活動不存在 | 帶 token 時回 410，否則 404 | **只看 Bearer**：沒有 Bearer 時回 `404 ACTIVITY_NOT_FOUND`，即使請求帶著 cookie（research R4，打錯代碼不應顯示「活動已失效」） |
| Set-Cookie | — | 不送。金鑰只由 `browser-session` 發出 |

其他端點（快照、離開本組、003 提交、004 學生結果等）的請求格式與回應都不變，差別只在身分改由 cookie 取得。

## 4. WebSocket `/ws/activities/{code}` 的 auth 訊息

| 項目 | 001 | 007 |
|---|---|---|
| 第一則訊息 | `{"type":"auth","token":"<string>"}`，`token` 必填 | `{"type":"auth"}` 或 `{"type":"auth","token":null}`：改用握手請求的 `lq_browser` cookie；`{"type":"auth","token":"<string>"}`：與 001 相同（老師頁） |
| 格式錯誤 | `type` 不是 `auth`，或 `token` 不是字串 → `CLOSE_BAD_FIRST_MESSAGE` | `type` 不是 `auth`，或 `token` 既不是字串也不是 null → `CLOSE_BAD_FIRST_MESSAGE` |
| 沒有身分 | `unauthorized INVALID_TOKEN` 後關閉 | 相同 |
| 離開本組／組別被刪除 | 對該裝置 token 雜湊的連線送 `unauthorized`（`LEFT_GROUP`／`GROUP_DELETED`） | 相同。同一瀏覽器的所有分頁共用雜湊，所以會**一起**收到（US2-AS2、US2-AS4） |

## 5. 前端分頁之間的訊息（瀏覽器內部，不經過後端）

| 頻道 | 訊息 | 送出時機 | 接收端行為 |
|---|---|---|---|
| `BroadcastChannel("lq-identity")` | `{"type":"joined","code":"<6 碼代碼>"}` | 本分頁加入成功後 | 沒有同步連線的學生分頁（在加入畫面）以該代碼開始同步，並把網址改成 `?code=`；已經連線的分頁不處理；格式不符的訊息直接忽略 |

## 6. 錯誤代碼一覽（新增或修改）

| 代碼 | HTTP | 訊息 |
|---|---|---|
| `BROWSER_SESSION_REQUIRED` | 400 | 瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。 |

## 7. 學生頁對回應的處理（前端，research R4、R7）

| 情況 | 學生頁行為 |
|---|---|
| 加入收到 `409 ALREADY_IN_GROUP`，代碼即本活動 | 顯示訊息，並以該代碼開始同步，切換到本組畫面（spec US1-AS3、US1-AS5） |
| 第一次連線收到 `unauthorized INVALID_TOKEN` | 安靜地顯示加入畫面，不顯示錯誤 |
| 第一次連線就收到 `gone`（從未同步成功） | 顯示加入畫面與「找不到這個活動代碼，請確認後再輸入。」 |
| 同步成功過之後收到 `gone` | 顯示「活動已失效，請重新建立或加入活動」（001 行為） |
| `ALREADY_IN_GROUP` | 409 | 這個瀏覽器已是第 n 組成員，請先離開本組。 |

所有錯誤訊息都不得包含金鑰、憑證、堆疊追蹤或檔案路徑（憲章原則 V）。
