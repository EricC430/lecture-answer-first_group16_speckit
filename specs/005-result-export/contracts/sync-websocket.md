# 快照契約：005 新增的 `export` 欄位

**用途**：005 透過 001 的「快照擴充」把最近一次寫回嘗試的摘要併入**老師**快照的頂層 `export` 欄位，隨 001 既有的 WebSocket 推送與 `GET /activities/{code}/snapshot` 送出，讓多個老師分頁在 2 秒內看到寫回狀態（FR-021）。連線、認證、重連與舊版本丟棄的規則沿用 [001 的 sync-websocket 契約](../../001-activity-session/contracts/sync-websocket.md)，005 不新增連線或訊息類型。

## 何時有 `export`

- **學生快照永遠沒有 `export`**（寫回狀態與答案內容是老師專用資料，憲章原則 V）。
- 老師快照：活動還沒有任何寫回嘗試時沒有 `export` 欄位（擴充回傳 `{}`，快照與原本完全相同）；有嘗試時回傳最近一次。
- 預覽與 CSV 是請求／回應，不放進快照。

## 形狀

```json
{
  "export": {
    "attemptId": 2,
    "kind": "RETRY",
    "snapshotId": "1.2",
    "status": "PENDING",
    "reason": "UNKNOWN",
    "totalCells": 12,
    "confirmedCells": 0,
    "notWrittenCells": 0,
    "pendingCells": 12,
    "inProgress": false,
    "startedAt": "2026-11-24T20:15:30.123+08:00",
    "finishedAt": "2026-11-24T20:16:30.456+08:00"
  }
}
```

- 欄位意義同 [http-api.md](http-api.md) 的 `Attempt`，但**不含**逐格答案、原儲存格內容與結構差異清單（這些只在請求回應中、只給發出請求的老師）。
- `inProgress` 為真時 `status` 是 `IN_PROGRESS`，`finishedAt` 為 `null`。

## 推送時機與規則

- 嘗試開始（進入進行中）與結束（成功、失敗、待確認）、核對改變狀態時，各推送一次；內容沒有變化時不重送（hub 會比較快照內容）。
- 擴充函式是同步、無副作用的純讀取；推送在 005 的鎖外進行。
- 老師快照的其他欄位（001 的活動狀態、003 的 `submissions`、004 的 `ranking`）不受影響。
- 推送內容不含 token、授權碼或試算表網址。
