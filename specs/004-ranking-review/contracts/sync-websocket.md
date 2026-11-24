# 快照契約：004 新增的 `ranking` 欄位

**用途**：004 透過 001 的「快照擴充」把結果併入快照頂層的 `ranking` 欄位，隨 001 既有的 WebSocket 推送與 `GET /activities/{code}/snapshot` 送出。連線、認證、重連、版本與 ping 規則全部沿用 001 [`sync-websocket.md`](../../001-activity-session/contracts/sync-websocket.md) 與 003 [`sync-websocket.md`](../../003-round-submission/contracts/sync-websocket.md)，本檔只描述新增欄位。

## 何時有 `ranking`

- 活動還沒有任何**已關輪**的輪次：快照**沒有** `ranking` 欄位。
- 搶答中（本輪未關閉）：`ranking.rounds` 只包含**更早、已定案**的輪次；目前輪不出現（FR-024：搶答中不提供順位或搶答成功者）。
- 關輪後：目前輪的結果出現在 `ranking.rounds`（初始 `resultVersion` 為 1）。

## 形狀

```json
{
  "ranking": {
    "rounds": [
      {
        "roundNumber": 2,
        "fairMode": true,
        "resultVersion": 3,
        "final": false,
        "affectedQuestions": [1, 2],
        "questionOrder": [2, 1, 3],
        "questions": [
          {
            "questionNumber": 2,
            "successGroup": 4,
            "replacedGroup": 1,
            "actions": { "judgeGroup": 4, "undoGroup": 1 },
            "entries": [
              {
                "groupNumber": 4,
                "rank": 1,
                "judgedWrong": false,
                "displayStatus": "SUCCESS",
                "countAtProcessing": 0,
                "reason": "FEWER_SUCCESSES"
              },
              {
                "groupNumber": 1,
                "rank": null,
                "judgedWrong": true,
                "displayStatus": "WRONG",
                "countAtProcessing": null,
                "reason": null
              }
            ]
          },
          { "questionNumber": 3, "successGroup": null, "replacedGroup": null, "actions": { "judgeGroup": null, "undoGroup": null }, "entries": [] }
        ],
        "groupCounts": { "1": 1, "4": 1 }
      }
    ]
  }
}
```

| 欄位 | 說明 |
|---|---|
| `rounds` | 依 `roundNumber` 遞增；每個已關輪的輪次一筆 |
| `fairMode` | 該輪開輪時固定的模式 |
| `resultVersion` | 該輪的結果版本，從 1 起，每次實際判錯變更加 1；與 001 的 `version` 互相獨立（研究 R3） |
| `final` | 該輪是否已定案（001 階段為結果已定案／已結束，或該輪早於目前輪）；`true` 時 `affectedQuestions` 為空 |
| `affectedQuestions` | 最近一次實際變更所影響的題號；初始與定案後為空（Clarifications 第 2 題） |
| `questionOrder` | 關輪時固定的題序；`questions` 依這個順序排列 |
| `successGroup` | 該題搶答成功者的組號；`null` ＝ 「未成功」（無人提交或全被判錯） |
| `replacedGroup` | 因判錯而被下一組取代的前一位搶答成功者中**最近一位**的組號（「被替換的搶答成功者」歷程的最後一位）；撤銷判錯會把最近一位移出歷程（退回上一步），所以會變回更早一位；歷程為空或 `final=true` 時為 `null`；**學生版**在整題無搶答成功者（沒有遞補者）時也為 `null`，**老師版**保留（讓老師仍能「撤銷判錯」）（spec FR-036、data-model `RoundReview.replaced`） |
| `entries` | 該題全部已接受的提交的排名資料：先放有名次者（名次由小到大），再放被判錯者（依接收時間與序號） |
| `rank` | 名次，從 1 起；被判錯者為 `null` |
| `judgedWrong` | 是否被老師判錯 |
| `displayStatus` | `SUCCESS`（搶答成功，結果未定案）、`CORRECT`（搶答正確，`final=true` 時名次 1 的提交）、`WRONG`（答錯）、`FAILED`（搶答失敗，沒搶到，不是答錯）；畫面文字由前端對應 |

**老師版才有**：每題的 `actions`（`judgeGroup`：未定案時的 `successGroup`；`undoGroup`：未定案時的 `replacedGroup`；`final=true` 時皆為 `null`；前端只照它顯示按鈕，由核心純函式產生並測試）、每個 entry 的 `countAtProcessing`（公平模式處理該題當下的成功次數；速度模式為 `null`）與 `reason`（`SOLE_CANDIDATE`、`EARLIER_SUBMISSION`、`FEWER_SUCCESSES`、`BACKEND_ORDER`；被判錯者為 `null`），以及每輪的 `groupCounts`（各組處理完該輪後的暫算次數，key 為組號字串）。

**學生版（所有學生同一份）**：**沒有** `countAtProcessing`、`reason`、`groupCounts`。學生資料對所有參與者公開查詢（含他組的 `rank`、`judgedWrong`、`displayStatus`，與 OpenSpec 一致）；學生畫面只顯示本組狀態、每題目前的搶答成功者（`successGroup`）與剛被判錯的前一組（`replacedGroup`），不逐組列出其他候選（FR-036，研究 R6）；學生畫面所需的資訊都能由 `successGroup`、`replacedGroup`、本組 entry 與 003 的答案取得，不需要順位以外的判準。本組成功次數沿用 001 的 `ownGroup.successCount`，不放在 `ranking`。

## 與 003 `submissions` 的合併

答案原文、接收時間與送出先後在 003 的 `submissions.published[].questions[].entries[]`。前端以（`roundNumber`, `questionNumber`, `groupNumber`）把 004 的 entry 與 003 的 entry 合併。003 的 `judgedWrong` 預留欄位一律為 `false`，**004 的前端不使用它**，以 `ranking` 的 `judgedWrong` 為準（研究 R5）。

## 推送與版本

- 判錯或定案實際變更後，004 在鎖外呼叫 001 的 `SyncPublisher.publish`；001 對每條連線重新裁切快照，**內容與上次相同時不送**，所以重複判錯（`changed=false`）不會推送。
- 001 的 `version`／`revision` 在判錯時不變，快照仍會被前端接受。004 的前端為每個輪次記住已收過的最大 `resultVersion`，收到較小者時不更新結果區塊（FR-016：不以舊版本覆蓋新版本）。
- 關輪那一刻 001 推送快照，擴充函式以純計算導出該輪的初始結果（研究 R2），所以老師與學生看到的第一份結果就是 `resultVersion = 1`。
- 搶答中，學生因他組動態而收到推送的次數必須為 0（001 FR-030）：004 在搶答中不產生任何與他組有關的變動，因為目前輪不出現在 `ranking`。

## 前端行為（驗收依據）

- **老師頁**（`ranking-review-teacher.js`）：每題列出全部候選（名次、組號、答案、處理當下成功次數、理由、顯示狀態）；按鈕只依 `actions` 顯示：**「判錯」只對 `actions.judgeGroup`（目前的搶答成功者）**，判完由遞補的下一組接手，搶答成功者之後的候選沒有按鈕；**「撤銷判錯」只對 `actions.undoGroup`（最近一位被替換者）**，撤銷是「退回上一步」，按完按鈕移到更早一位被替換者旁，直到歷程用完（只是介面限制，API 仍允許對任一提交判錯與撤銷，FR-034）；受影響題目標示「結果已更新」；確認定案按鈕帶著畫面上的 `resultVersion`；顯示活動階段「結果未定案／結果已定案」（FR-031）。
- **學生頁**（`ranking-review.js`）：每題顯示本組的狀態（搶答成功、搶答正確、答錯、搶答失敗；整題無人成功為「未成功」）、目前的搶答成功者（組號、答案、狀態），以及有 `replacedGroup` 時剛被判錯的那一組（組號、答案、「答錯」）與遞補者一起顯示；`replacedGroup` 為 `null`（含定案後、無搶答成功者）時不顯示；不顯示理由與他組成功次數，也不列出其他候選或更早被判錯的組別。沒有提交的組別不顯示該題狀態。
- 所有文字（組號、答案、訊息）一律 `textContent`，保留換行（FR-028）。
- 判錯與定案回應成功才更新畫面；同步中斷時沿用 001 的「同步中斷」提示。
