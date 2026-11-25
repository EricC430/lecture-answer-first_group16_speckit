# Data Model: 006 介面改版

本功能沒有後端資料模型的變動。下列是**介面組成元素**的定義，對應類別圖 [006-ui-refresh-class.puml](../../diagrams/006-ui-refresh-class.puml)。所有資料都只存在瀏覽器記憶體，不寫入 localStorage（老師 token 仍沿用 001 的保存方式）。

## 設計基準值（`css/tokens.css`）

| 群組 | 基準值 | 規則 |
|---|---|---|
| 色彩 | `--color-*`（完整清單與數值見 [research.md](research.md) R2） | 只在 `tokens.css` 定義；其他檔案只能 `var(--color-*)`（FR-004） |
| 字體 | `--font-heading`、`--font-body`、`--font-mono` | 依 R3 的字體堆疊 |
| 字級 | `--text-xs` 13px、`--text-sm` 14px、`--text-base` 16px、`--text-lg` 20px、`--text-xl` 24px、`--text-2xl` 32px、`--text-display` 44px | 內文不小於 16px；說明文字不小於 13px |
| 間距 | `--space-1`～`--space-8`：4、8、16、24、32、40、48、64px | 相鄰點擊元件間距 ≥ `--space-2`（FR-027） |
| 圓角 | `--radius-pill` 999px（按鈕、標籤、分頁）、`--radius-card` 12px、`--radius-field` 8px | 參考範本：膠囊按鈕、12px 卡片 |
| 尺寸 | `--tap-min` 44px、`--layout-max` 1280px、`--sidebar-width` 360px | 點擊目標 ≥ 44×44（FR-027） |
| 動畫 | `--duration-fast` 150ms、`--duration-base` 250ms、`--duration-highlight` 1500ms | 減少動態效果時歸零（FR-016） |

## 共用元件（`css/app.css`）

| 元件 | 類別／屬性 | 狀態 | 對應 FR |
|---|---|---|---|
| 按鈕 | 預設 `button` 為次要（幽靈外框）；`.btn-primary`、`.btn-secondary`、`.btn-danger` | `:disabled`、`[aria-busy="true"]`（處理中）、`:focus-visible` | FR-005、FR-018、FR-026、FR-027 |
| 輸入欄位 | `input`、`select`、`textarea`、`label` | `:disabled`、`[aria-invalid="true"]` | FR-005、FR-028 |
| 卡片 | `.card`；子功能區塊 `section[data-feature]` 預設套用卡片樣式 | — | FR-005 |
| 眉標 | `.eyebrow`（等寬大寫小字，放在區塊標題上方） | — | 視覺方向 |
| 表格 | 既有的 `table`、`.submission-board`、`.export-table` 外包 `.table-scroll` | 窄螢幕時只在 `.table-scroll` 內水平捲動 | FR-019 |
| 狀態標籤 | `.status-label` + `--success`／`--danger`／`--warning`／`--neutral` | 每個標籤有圖示＋文字 | FR-015 |
| 訊息 | `.error-message`、`.error`（既有）、`.notice` | — | FR-005、FR-011 |
| 同步中斷橫幅 | `#sync-banner`（既有） | `[hidden]` | FR-012 |
| 階段進度 | `#stage-progress`（新，老師頁左欄頂端） | `aria-current="step"` 標示目前階段 | FR-017 |
| 空狀態 | `.empty-state`（插圖＋一句說明） | — | FR-022 |

## 狀態標籤對照

畫面文字沿用各子功能既有的文字，不改意義；本表只決定外觀。

| 來源 | 既有標示 | 標籤樣式 | 圖示 |
|---|---|---|---|
| 004 `displayStatus` | `SUCCESS` 搶答成功、`CORRECT` 搶答正確 | `--success` | 勾 |
| 004 `displayStatus` | `WRONG` 答錯 | `--danger` | 叉 |
| 004 `displayStatus` | `FAILED` 搶答失敗 | `--neutral` | 橫線 |
| 004 題目層級 | 未成功（無人提交或全被判錯） | `--neutral` | 橫線 |
| 003 送出 | 已送出（`success-hint`） | `--success` | 勾 |
| 003 送出 | 送出失敗（`.error-message`） | `--danger` | 叉 |
| 003 送出 | 送出中 | `--warning` | 沙漏 |
| 005 寫回 | 寫回成功 | `--success` | 勾 |
| 005 寫回 | 寫回失敗、無法證實 | `--danger`／`--warning` | 叉／驚嘆號 |
| 001 同步 | 同步中斷 | `--warning` | 驚嘆號 |

## 老師頁分頁（`js/teacher-layout.js`）

| 分頁 id | 標籤文字 | 面板內的區塊 | 自動切入的階段 |
|---|---|---|---|
| `tab-import` | 匯入 | `#import-section` | `PREPARING`、`JOINING` |
| `tab-board` | 作答看板 | `#round-submission-section`、`#published-section` | `ROUND_OPEN` |
| `tab-ranking` | 順位與判錯 | `#ranking-review-section` | `RESULT_PENDING`、`RESULT_FINAL` |
| `tab-export` | 寫回 | `#export-section` | `ENDED` |

**分頁狀態**（只在記憶體）：

| 欄位 | 說明 |
|---|---|
| `selected` | 目前選取的分頁 id |
| `lastStage` | 上一次快照的階段；只有與新階段不同時才自動切換（FR-017b） |
| `updated` | 有「有更新」標記的分頁 id 集合（FR-017c） |
| `visible` | 由面板內區塊的 `hidden` 推得；全部隱藏的分頁不顯示標籤（FR-017d） |

**轉換規則**：

1. 收到快照且 `stage !== lastStage` → 選取對照表的分頁；若該分頁不可見，選第一個可見分頁；清除該分頁的「有更新」。`CANCELLED` 不自動切換。
2. 使用者點選或以鍵盤選取 → `selected` 改變，清除該分頁的「有更新」。
3. 非 `selected` 的面板發生 DOM 變動 → 加入 `updated`。
4. `selected` 的分頁變成不可見 → 改選第一個可見分頁。

## 學生頁題號導覽（`js/question-nav.js`）

| 欄位 | 來源 | 說明 |
|---|---|---|
| `questionNumber` | 本組作答卡片 | 只來自本頁已渲染的本組卡片 |
| `state` | 卡片的 `data-submit-state` | `idle`／`error` 顯示「未送出」；`busy` 顯示「送出中」；`done` 顯示「已送出」 |
| `target` | 卡片標題元素 id | 點擊後捲動並把焦點移到標題 |

出現條件：本輪開放題數 ≥ 2。不含他組任何資訊（FR-008a）。

## 投影檢視（`js/projection-view.js` 的 `toProjectionView` 輸出）

完整欄位白名單見 [contracts/projection-view.md](contracts/projection-view.md)。

| 階段 | `mode` | 內容 |
|---|---|---|
| 無快照、沒有老師 token | `unavailable` | 提示文字 |
| `PREPARING`、`JOINING` | `lobby` | 活動代碼、階段 |
| `ROUND_OPEN` | `round` | 活動代碼、階段、輪次、題號、模式、截止時間（或「由老師結束」） |
| `RESULT_PENDING`、`RESULT_FINAL` | `results` | 上列＋目前輪各題的結果卡片 |
| `ENDED` | `ended` | 未成功題號 |
| `CANCELLED` | `cancelled` | — |

**結果卡片**：`questionNumber`、`outcome`（`success`／`unsolved`）、`successGroup`、`replacedGroup`、`entries[]`（`groupNumber`、`order`、`rank`、`displayStatus`、`answers[]`），依 `order`（送出先後）排列；`resultVersion` 用來丟棄較舊結果。

## 插圖

| id | 檔案 | 用途 | 替代文字 | 來源 |
|---|---|---|---|---|
| `hero` | `img/hero.webp` | 首頁主插圖，傳達「課堂分組搶答」 | 「幾組學生圍著桌子舉手搶答，旁邊有一個大計時器」 | AI 生成（組員；工具、提示詞、日期記在 `illustrations.md`） |
| `empty-groups` | `img/illustrations.svg#empty-groups` | 尚未有組別加入 | 裝飾（`aria-hidden`），旁邊有說明文字 | Claude 手寫 |
| `empty-import` | `img/illustrations.svg#empty-import` | 尚未匯入學習單 | 裝飾 | Claude 手寫 |
| `empty-round` | `img/illustrations.svg#empty-round` | 尚未開輪／等待老師 | 裝飾 | Claude 手寫 |
| `empty-results` | `img/illustrations.svg#empty-results` | 尚無結果 | 裝飾 | Claude 手寫 |
