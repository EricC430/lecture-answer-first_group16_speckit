# 契約：投影檢視白名單（`toProjectionView`）

**用途**：投影畫面（`projection.html`）收到的是老師快照（001 `sync-websocket.md`，含 003 `submissions`、004 `ranking` 擴充）。老師快照在搶答中含有各組答案，**不能直接渲染**。`js/projection-view.js` 匯出純函式 `toProjectionView(snapshot)`，依本契約從快照**複製**允許的欄位成新物件；投影畫面的渲染程式只能讀這個新物件（研究 R5，FR-031、FR-032）。

## 函式介面

```text
toProjectionView(snapshot | null, hasTeacherToken: boolean) -> ProjectionView
```

- 純函式：不讀 DOM、時間、網路或全域狀態；相同輸入一定得到相同輸出。
- 未列在下表的欄位一律不複製。新增欄位必須先改本契約與對應測試。

## 輸出（`ProjectionView`）

| 欄位 | 型別 | 來源（老師快照） | 出現於 `mode` |
|---|---|---|---|
| `mode` | `"unavailable"`｜`"lobby"`｜`"round"`｜`"results"`｜`"ended"`｜`"cancelled"` | `stage` | 全部 |
| `code` | string | `code` | `unavailable` 以外 |
| `stageLabel` | string | `stage`（以 001 的 `STAGE_LABELS` 轉成文字） | `unavailable` 以外 |
| `roundNumber` | int｜null | 目前輪次編號 | `round`、`results` |
| `questionNumbers` | int[] | 目前輪的開放題號 | `round`、`results` |
| `fairMode` | boolean | 目前輪的規則快照 | `round`、`results` |
| `deadline` | ISO 字串｜null | 目前輪的截止時間（null 表示「由老師結束」） | `round` |
| `results` | ResultCard[] | 見下 | `results` |
| `resultVersion` | int | `ranking.rounds[目前輪].resultVersion` | `results` |
| `final` | boolean | `ranking.rounds[目前輪].final` | `results` |
| `unsolved` | int[] | 已結束時的未成功題 | `ended` |

`ResultCard`：

| 欄位 | 來源 |
|---|---|
| `questionNumber` | `ranking.rounds[目前輪].questions[].questionNumber` |
| `successGroup` | 同上 `.successGroup` |
| `replacedGroup` | 同上 `.replacedGroup` |
| `entries[]` | 每筆：`groupNumber`、`rank`、`displayStatus`、`judgedWrong` 取自 `ranking` 的 entry；`order`、`answers` 取自 `submissions.published[目前輪].questions[].entries[]`（以輪次、題號、組號合併） |

## 禁止事項（測試必須涵蓋）

1. `mode === "round"`（搶答中）時，輸出 **MUST NOT** 含任何 `answers`、`entries`、`groupNumber`、`order`、`receivedAt` 或任何計數；函式在這個 mode **不得讀取** `submissions.current`。
2. 任何 mode 都 **MUST NOT** 含 `reason`、`countAtProcessing`、`groupCounts`、`actions`、`ownGroup`、`groups`（組別表、憑證、裝置數）、`teacherToken` 或任何 token。
3. 只輸出**目前輪**的結果；較早輪次的 `published` 與 `ranking` 不輸出。進入下一輪的 `ROUND_OPEN` 時 `results` 必須不存在。
4. 答案以原文字串輸出；渲染時一律用 `textContent`（憲章原則 V）。

## 版本處理（渲染端，不屬於純函式）

- 投影畫面為每個輪次記住最大 `resultVersion`；新的 `ProjectionView` 若是同一輪且 `resultVersion` 較小，不更新結果區（FR-034）。
- 001 的 `version`／`revision` 由 `sync.js` 既有邏輯處理。

## 測試對應

| 測試 | 檢查 |
|---|---|
| `tests/browser/test_ui_projection.py::test_projection_view_whitelist_*`（在瀏覽器中以 ES module 載入 `projection-view.js` 呼叫純函式） | 以真實後端產生的老師快照，逐一驗證禁止事項 1～3 |
| `tests/browser/test_ui_projection.py::test_projection_hides_answers_while_round_open` | 搶答中投影畫面的 DOM 文字不含任何已送出的答案（SC-010） |
| `tests/browser/test_ui_projection.py::test_projection_shows_replacement_within_2s` | 判錯後 2 秒內出現遞補，量 10 次（SC-010） |
