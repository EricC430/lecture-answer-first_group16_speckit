# Data Model: 同一瀏覽器共用學生身分與跨分頁同步

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **類別圖**: [`diagrams/007-browser-identity-sync-class.puml`](../../diagrams/007-browser-identity-sync-class.puml)

007 不新增後端的持久資料結構，也不新增資料庫（憲章原則 VII）。它做了兩件事：

- 改變 001 的 `DeviceIdentity` 鍵值來自哪裡。
- 新增一個存在瀏覽器裡的 cookie。

001 的完整模型見 `specs/001-activity-session/data-model.md`。

## 瀏覽器金鑰（Browser Key）——新增，只存在於瀏覽器的 cookie 與請求中

| 欄位 | 說明 |
|---|---|
| cookie 名稱 | `lq_browser` |
| 值 | `secrets.token_urlsafe(32)`，43 個 URL 安全字元（`[A-Za-z0-9_-]`） |
| 屬性 | `HttpOnly`、`SameSite=Strict`、`Path=/`、`Max-Age=86400`；不設 `Secure`、`Domain`（research R1、R9） |
| 產生者 | `POST /api/browser-session`；請求沒有帶格式正確的金鑰時產生新的，已有時沿用並延長期限 |
| 驗證規則 | 格式不符（長度、字元集）一律視為沒有金鑰，不拋錯；格式正確但在活動中查不到，視為匿名（FR-008） |
| 生命週期 | 瀏覽器保存到最後一次開啟學生頁起 1 天（滑動期限）；後端不保存金鑰本身，只保存它在各活動的雜湊。老師 token 不能當金鑰加入（`TEACHER_CANNOT_JOIN`） |

- 後端**不**保存「已發出的金鑰清單」。金鑰只有在加入組別後，才會以 `hash_token(金鑰)` 的形式成為某個活動的 `DeviceIdentity` 鍵。
- 一把金鑰可以同時是多個活動的裝置（每個活動最多一筆）。

## DeviceIdentity（001）——語意改為「瀏覽器在某活動中的身分」

| 欄位 | 001 | 007 之後 |
|---|---|---|
| `token_hash` | `hash_token(new_token())`，每次加入產生新 token | `hash_token(瀏覽器金鑰)`，同一瀏覽器每次加入都相同 |
| `group_number` | 所屬組號 | 不變 |

**狀態轉換**（與 001 相同，只是主體從「分頁」變成「瀏覽器」）：

```text
（無身分） --加入成功--> 第 N 組成員
第 N 組成員 --離開本組（非搶答中）--> （無身分）   → 該雜湊的所有連線收到 unauthorized LEFT_GROUP
第 N 組成員 --老師刪除第 N 組--> （無身分）        → 該雜湊的所有連線收到 unauthorized GROUP_DELETED
第 N 組成員 --加入任何組--> 拒絕 ALREADY_IN_GROUP（狀態不變）
任何狀態 --後端重啟--> 活動不存在                   → 連線收到 gone
```

## 核心不變量（`ActivityStateMachine._join_group`）

- **INV-1（新增）**：`JoinGroup` 指令新增欄位 `device_token_hash: str | None`，由服務層填入 `hash_token(瀏覽器金鑰)`。`command.device_token_hash` 已在 `activity.devices` 時，必須拒絕 `ALREADY_IN_GROUP`，而且不建立組別、不發憑證。
  - 這條檢查補足「請求者在取得鎖之前就已解析」造成的競爭（research R3），確保同一瀏覽器同時送出的加入請求只會成功一個（FR-007）。
- **INV-2（沿用）**：`activity.devices` 的鍵不重複。每個瀏覽器在每個活動中最多只有一個組別身分（FR-001、FR-003）。
- **INV-3（沿用 001 FR-034）**：只有在「組別最後一筆 `DeviceIdentity` 被移除，而且該組從未提交」時，才釋放組號。這裡的「最後一筆」，從 007 起就是「最後一個瀏覽器」。

## 拒絕原因與訊息

| 代碼 | HTTP | 訊息 | 何時出現 |
|---|---|---|---|
| `ALREADY_IN_GROUP` | 409 | 「這個瀏覽器已是第 N 組成員，請先離開本組。」（原文「這台裝置已經在第 N 組…」改寫） | 已是成員，或同時加入時落敗的那一個請求 |
| `BROWSER_SESSION_REQUIRED`（新增，外層） | 400 | 「瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。」 | 加入請求沒有瀏覽器金鑰，也沒有 Bearer（FR-013） |

`BROWSER_SESSION_REQUIRED` 在 HTTP 轉接層判定，不屬於核心的 `RejectionReason`，因為核心不知道 cookie 的存在（架構限制）。

## 前端狀態（不是後端資料，列出供測試對照）

| 位置 | 007 之前 | 007 之後 |
|---|---|---|
| `sessionStorage["device:{code}"]` | 裝置 token | 移除 |
| `localStorage["teacher:{code}"]`、`["teacher:last"]` | 老師 token | 不變（老師身分不受 007 影響，US3） |
| `BroadcastChannel("lq-identity")` | — | 訊息格式為 `{"type":"joined","code":"<活動代碼>"}`，不含身分內容 |
