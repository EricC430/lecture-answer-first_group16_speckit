# 同步契約：003 在 001 快照中新增的欄位

**用途**：提交資料隨 001 的快照推送（研究 R4）。連線、認證、ping、關閉碼與版本規則沿用 001 [`sync-websocket.md`](../../001-activity-session/contracts/sync-websocket.md)。

## 推送時機

| 事件 | 老師 | 提交組的裝置 | 其他組的裝置 | 版本 |
|---|---|---|---|---|
| 提交被接受 | 收到（`revision + 1`） | 收到（內容變了，`version` 不變） | **不收到**（內容不變，hub 去重） | `version` 不變 |
| 本組已送出／被拒 | 不推送 | 不推送 | 不推送 | 不變 |
| 關輪 | 收到 | 收到 | 收到 | `version + 1` |

**欄位出現的條件**：活動還沒有格數資料（尚未成功匯入題目）時，快照不帶任何 003 欄位（`questionShapes`、`submissions`），與 001 原本的快照完全相同；前端遇到欄位不存在時視為空。

## 老師快照新增欄位

```json
{
  "questionShapes": {"1": 2, "2": 2, "3": 1, "4": 1},
  "submissions": {
    "current": {
      "roundNumber": 2,
      "open": true,
      "questions": [
        {
          "questionNumber": 1,
          "noSubmission": false,
          "entries": [
            {"groupNumber": 3, "answers": ["…", "…"], "receivedAt": "…", "order": 1},
            {"groupNumber": 1, "answers": ["…", "…"], "receivedAt": "…", "order": 2}
          ]
        }
      ]
    },
    "published": [ { "roundNumber": 1, "questions": [ … 同上，另含 "judgedWrong": false … ] } ]
  }
}
```

- `entries` 依（接收時間, 接收序號）排序；`order` 是送出先後（1 起算），**不是**順位（Q-21：搶答中不顯示暫估順位）。
- 沒有提交的組不出現在 `entries`；老師頁依 `maxGroups` 與 `groups` 畫出「尚未送出」。

## 學生快照新增欄位

```json
{
  "questionShapes": {"1": 2, "2": 2},
  "submissions": {
    "current": {
      "roundNumber": 2,
      "open": true,
      "own": [
        {"questionNumber": 1, "answers": ["…", "…"], "receivedAt": "…"}
      ]
    },
    "published": [ { "roundNumber": 1, "questions": [ … 全部組，含 "order"、"noSubmission"、"judgedWrong" … ] } ]
  }
}
```

- `current.open` 為真時（本輪開放中），`current` 只有 `own`（本組），**沒有**他組的答案、狀態、時間、數量或先後（FR-021）。
- `questionShapes` 只有本輪開放題。
- `ownGroup.successCount` 照 001，搶答中也可見（Q-22，研究 R9）；學生快照沒有任何排名或他組成功次數。
- 關輪後本輪移到 `published`，所有組可見；`judgedWrong` 由 004 提供（Q-26：學生可見）。

## 前端排序

沿用 001 `sync.js`：丟棄 `version` 較小的快照；老師快照同版本再比 `revision`。學生快照同版本照常套用（同一條連線上的訊息有序）。
