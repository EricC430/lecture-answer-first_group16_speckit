# 契約：頁面結構與 DOM 識別

**用途**：001～005 的畫面腳本與 `tests/browser/` 都以元素 id 與 `section[data-feature]` 操作畫面。改版可以搬移元素位置、增加外層容器與類別，但不能破壞下列約定（FR-001、FR-003；研究 R4）。

## 必須保留（不得改名、刪除或改變語意）

- 所有既有元素的 `id`（`teacher.html`、`student.html` 中的全部 id，以 2026-11-25 `feature/9-005-result-export` @ f0f45da 為準）。
- 每個子功能區塊的 `<section id="…" data-feature="…">`，以及區塊的 `hidden` 由原子功能腳本控制。
- 既有類別：`activity-code`、`countdown`、`controls`、`error-message`、`error`、`muted`、`success-hint`、`submission-board`、`answer-text`、`published-round`、`ranking-round`、`ranking-entries`、`ranking-entry`、`status-*`、`export-table`、`export-answer`、`export-impact-replace`、`submit-status`。可以增加新類別，不可移除。
- `#sync-banner`、`#sync-status` 的存在與 `body.sync-broken` 的行為（001 FR-028）。
- 各 `<script type="module">` 的載入，以及「每個子功能一行」的順序。

## 新增的結構

| 頁面 | 元素 | 說明 |
|---|---|---|
| `teacher.html` | `.teacher-layout` > `#teacher-sidebar` + `#teacher-workspace` | 兩欄版面；1024px 以下為單欄 |
| `teacher.html` | `#stage-progress` | 左欄頂端的階段進度（`<ol>`，目前階段 `aria-current="step"`） |
| `teacher.html` | `#open-projection` | 「開啟投影畫面」按鈕；活動建立後才顯示 |
| `teacher.html` | `#teacher-tabs`（`role="tablist"`）、`#tab-import`、`#tab-board`、`#tab-ranking`、`#tab-export`（`role="tab"`）、`#panel-import`、`#panel-board`、`#panel-ranking`、`#panel-export`（`role="tabpanel"`） | 分頁，對照見 data-model |
| `teacher.html` | `.tab-badge` | 「有更新」標記（文字＋圖示） |
| `student.html` | `#question-nav`（`<nav aria-label="題號導覽">`） | 題號導覽，題數 ≥ 2 時顯示 |
| `student.html` | 作答卡片的 `data-submit-state` | `idle`／`busy`／`done`／`error`，由 `submission.js` 設定 |
| `student.html`、`teacher.html` | 倒數元素（`#student-countdown`、`#round-countdown`）的 `data-urgent` | 剩餘 ≤ 10 秒時存在，由 `countdown.js` 設定 |
| `student.html` | `#answer-sticky` > `.answer-status`（`#answer-group`、`#answer-stage`、`#answer-countdown`）＋`#question-nav` | 作答區上方的固定列；資訊是 001 元素文字的唯讀鏡像（`aria-hidden`），由 `question-nav.js` 維護（FR-008） |
| 三頁 | `.empty-state` | 空狀態插圖與說明 |
| `projection.html` | `#projection-root`、`#projection-code`、`#projection-stage`、`#projection-countdown`、`#projection-results` | 投影畫面（新頁面，路徑 `projection.html?code=XXXX`） |
| `index.html` | `#role-teacher`、`#role-student` | 首頁的兩個入口連結 |

## 既有腳本允許的修改

| 檔案 | 修改 | 不得改變 |
|---|---|---|
| `js/submission.js` | 建立卡片時設定 `data-question`（題號）與 `data-submit-state="idle"`；在 `setBusy`、錯誤、成功三處更新 `data-submit-state` | 送出流程、按鈕停用規則、文字內容 |
| `js/countdown.js`（001 共用倒數） | 剩餘 ≤ 10 秒時在倒數元素設定 `data-urgent`，沒有截止時移除（2026-11-25 實作時發現倒數由此模組顯示，不在 `round-submission.js`） | 倒數計算、文字內容 |
| `js/result-export.js` | 寫回狀態文字 `#export-status-text` 設定 `data-status`（`IN_PROGRESS`／`SUCCESS`／`FAILED`／`PENDING`），讓狀態標籤樣式一致（FR-015；2026-11-25 實作 US4 時新增） | 寫回流程、文字內容 |
| `js/teacher.js` | **僅在需要時**：把 `STAGE_LABELS` 搬到無副作用的 `js/stage-labels.js` 並從 `teacher.js` 重新匯出（tasks T066），讓投影畫面可以匯入階段文字而不觸發老師頁的初始化 | 匯出名稱、階段文字、其他所有行為 |

其他子功能腳本不修改。若實作時發現必須修改，先更新本契約與 plan，並在 PR 說明理由。
