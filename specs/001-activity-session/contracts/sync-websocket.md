# WebSocket 同步契約：001-activity-session

**用途**：伺服端把依角色裁切的完整快照推送到每個頁面（研究 R1）。WebSocket **只推送，不接收任何操作**；操作一律走 [http-api.md](http-api.md)。

## 連線流程

1. 前端連線到 `ws://127.0.0.1:<port>/ws/activities/{code}`。
2. 連線後 5 秒內，前端送出第一則訊息 `{"type": "auth", "token": "<老師或裝置 token>"}`。token 不放在 URL。
3. 伺服端驗證 token：
   - **成功**：立即送出一則 `snapshot`。
   - **活動不存在**（例如後端已重啟）：送出 `{"type": "gone"}` 後，以 close code `4410` 關閉連線。
   - **token 無效**：送出 `{"type": "unauthorized"}` 後，以 close code `4401` 關閉連線。適用情況包括：token 錯誤、裝置已離開本組、所屬組別已被老師刪除。
4. 之後每次活動狀態變更，伺服端都對每條連線推送一則新的 `snapshot`，內容依該連線的角色裁切。
5. 伺服端每 10 秒送一次 `{"type": "ping"}`。前端超過 25 秒沒收到任何訊息，就視為中斷。

## 訊息格式

### `snapshot`（伺服端 → 前端）

共同欄位：

```json
{
  "type": "snapshot",
  "role": "teacher | student",
  "code": "K7QH2M",
  "version": 12,
  "changedAt": "2026-11-21T13:05:07.123+08:00",
  "stage": "PREPARING | JOINING | ROUND_OPEN | RESULT_PENDING | RESULT_FINAL | ENDED | CANCELLED",
  "roundNumber": 2,
  "openQuestions": [1, 3],
  "deadline": "2026-11-21T13:06:07+08:00",
  "fairMode": false,
  "unsolvedQuestions": [3]
}
```

- **`version`、`changedAt`**：學生可見的狀態版本與其變更時間，只在階段、輪次、題號或已成功題改變時更新；老師與學生在同一個狀態下看到相同的值（FR-027）。組別加入、離開、刪除與提交標記不改變這兩個欄位（FR-030）（2026-11-23，jacky0407 依 PR #15 第三次審查決定）。
- **`roundNumber`**：還沒開過輪時為 `null`。
- **`openQuestions`**：只在 `ROUND_OPEN` 時有內容，其他階段為空陣列。
- **`deadline`**：沒有倒數或不在搶答中時為 `null`。
- **`unsolvedQuestions`**：只在 `ENDED` 時有內容（FR-022），其他階段為空陣列。

**學生版另外有**：

```json
{ "ownGroup": { "number": 3, "credential": "Q8MZ3R", "successCount": 1 } }
```

學生版**不含**其他組的任何資訊，包括組號、實際組數、憑證、進度（FR-030）。

**老師版另外有**：

```json
{
  "revision": 27,
  "maxGroups": 6,
  "groups": [
    { "number": 3, "credential": "Q8MZ3R", "successCount": 1, "hasSubmissions": true, "deviceCount": 2 }
  ],
  "questionNumbers": [1, 2, 3, 4]
}
```

### 其他訊息

| `type` | 方向 | 說明 |
|---|---|---|
| `auth` | 前端 → 伺服端 | 只能是第一則訊息；之後再送任何訊息，伺服端都會忽略並記錄 `WARNING`（不含內容） |
| `ping` | 伺服端 → 前端 | 保持連線；前端不需回應 |
| `gone` | 伺服端 → 前端 | 活動已失效；前端顯示「活動已失效，請重新建立或加入活動」，並清除本機的身分 |
| `unauthorized` | 伺服端 → 前端 | `{"type": "unauthorized", "reason": "INVALID_TOKEN \| LEFT_GROUP \| GROUP_DELETED"}`；學生頁面回到加入畫面。`GROUP_DELETED` 時顯示「此組已被老師刪除，請重新加入」。組別被刪除或裝置離開時，伺服端會對該裝置的現有連線送出這則訊息並關閉連線 |

## 前端行為（驗收依據）

- **同步中斷**：WebSocket `close`／`error`，或超過 25 秒沒收到訊息時，立即顯示「同步中斷，正在重新連線」，並停用所有「成功」的提示（FR-028）。
- **重連**：依序等 0.5、1、2、4 秒，之後每次都等 4 秒，直到連上。重連後收到的第一則 `snapshot` 就是最新的完整狀態（FR-028）。
- **舊版本**：收到的 `snapshot.version` 小於目前畫面的版本時，直接丟棄；老師快照在 `version` 相同時，`revision` 較小者丟棄。
- **狀態列**：頁面右下角顯示 `v{version}` 與延遲（畫面更新完成的時間 − `changedAt`，單位毫秒），供人工量測 2 秒同步（研究 R2）。
- **不可信文字**：伺服端回傳的文字（錯誤訊息等）一律以 `textContent` 輸出（原則 V）。
- **組別排序**：老師版 `groups` 依組號由小到大排列。

## 推送保證

- **推送時機**：只有狀態真的改變時才推送（`Transition.changed == True`）。例如重複關輪、重送的請求都不會推送。
- **推送範圍**：推送給該活動的所有連線，每條連線各自裁切內容；**裁切後的內容與該連線上次收到的完全相同時不送**。因此他組的加入、離開、刪除與提交標記只會推送給老師（`revision` 改變），學生不會收到任何訊息（FR-030）（2026-11-23，jacky0407 依 PR #15 第三次審查決定）。
- **失敗與逾時**：各連線並行送出，每條連線限時 1 秒；送出失敗或逾時時，只關閉那條連線，不影響其他連線，也不影響狀態（PR #15 第二次審查）。
