# Vibe Coding 課堂搶答系統 Constitution

NCU SE6005 2026 軟體工程期末專題第 16 組 SpecKit 組（jacky0407、EricC430）的專案憲章。
本憲章約束所有子功能的 spec、plan、tasks、圖表與程式碼；與其他文件衝突時以本憲章為準。

## Core Principles

### I. 跨組行為一致（NON-NEGOTIABLE）

- `docs/openspec-reference/` 收錄的 OpenSpec 組規格中的 SHALL 需求與 Scenario，是本系統
  使用者可見行為的唯一基準。
- 每份子功能 spec 必須標註它對應的 OpenSpec Requirement 名稱；每個功能需求（FR）與驗收情境
  都必須能追溯到某個 Requirement 或 Scenario。
- 任何偏離基準或新增的行為，必須先記錄在 `docs/alignment.md`，雙方確認人都已填寫（不得為
  「待確認」）後才能實作。未記錄的口頭共識視為未確定。
- 讀規格時發現的模糊或衝突，列入 `docs/alignment.md` 的待確認清單，不得自行假設答案後實作。

**理由**：課程要求兩組系統功能一致；以對方規格為單一基準並留下書面紀錄，才能避免各自解讀造成
行為分歧。

### II. PlantUML 設計優先 (Design-First with PlantUML)（NON-NEGOTIABLE）

原則 II：圖表生成 (Diagram Generation)
名稱：PlantUML 設計優先 (Design-First with PlantUML)
規則：

- **規格制定階段 (Specification Phase)**：在 `/speckit-specify` 階段，必須使用 PlantUML 語法
  生成組件圖 (Component diagram)、類別圖 (Class diagram) 和時序圖 (Sequence diagram)。
  這些圖表檔案（`.puml`）必須儲存在 `./diagrams/` 目錄中。
- **產物生成 (Artifact Generation)**：檔案建立後，必須使用 PlantUML CLI
  （`java -jar plantuml.jar "./diagrams/*.puml"`）將所有 `.puml` 檔案轉換為 PNG 圖片，
  且輸出的圖片必須儲存在相同的目錄中。
- **規劃階段 (Planning Phase)**：`/speckit-plan` 階段必須將這些圖表作為主要藍圖，用以生成
  應用程式的架構與組件。
- **實作階段 (Implementation Phase)**：在 `/speckit-implement` 階段完成程式碼生成後，必須
  執行驗證步驟，以確保最終的程式碼與圖表完全一致。

補充規定：

- `.puml` 與轉出的 PNG 都必須提交進 repo；`plantuml.jar` 不提交（已列入 `.gitignore`）。
- 圖表檔名以子功能編號開頭（例如 `001-activity-session-sequence.puml`），避免子功能之間互相覆蓋。
- 實作偏離圖表時，必須在同一個 PR 內先更新圖表並重新轉出 PNG，不得只改程式碼。

**理由**：課程規定 SpecKit 組須導入 Diagram First Development；把需求先轉成圖，可以讓 AI 有
明確的規劃依據，也讓組員有可視化的審查依據。

### III. Guided Notes 動態定位

- 匯入與寫回都不得寫死工作表名稱、列號、欄號或儲存格座標；必須依「題號」「作答」等表頭文字、
  儲存格值與合併範圍動態定位。
- 匯入是原子操作：只要有任何一項驗證錯誤，就整份拒絕，並指出出錯的位置與原因；既有成功匯入的
  資料不得被清除或部分覆寫。
- 寫回前（包含每次重試）必須重新讀取來源並驗證結構與匯入時一致；不一致時停止整次寫入，
  不得猜測新位置。
- 答案一律以文字值寫入（不當成公式解析或執行），只寫入目標答案格，不修改其他儲存格、格式或
  合併設定。

**理由**：助教會用另一份學習單測試；寫死位置或部分匯入／寫入，都會在換表後產生錯誤結果，
甚至破壞老師的原始檔案。

### IV. 後端為唯一事實來源

- 接收時間、唯一遞增的接收序號、組別身分、角色權限、輪次識別與結果版本都由後端產生與判定，
  不得採信前端傳來的時間、組別或角色宣稱。
- 截止、關輪、提交、判錯與定案必須在後端以一致的順序處理；同一請求重送不得產生第二筆紀錄。
- 順位計算必須是確定性的：相同的輸入（基準成功次數、固定題序、提交與判錯狀態）每次重算都得到
  相同結果。

**理由**：搶答的公平性取決於「誰先到」，只有後端能提供可信、可重現的判定依據。

### V. 資料可見性與安全

- 搶答進行期間，學生端的頁面與所有 API 回應只能包含自己組的資料；不得出現他組的答案、提交狀態、
  時間、數量、順位，或任何可推知他組進度的統計。
- 組名、答案、錯誤訊息等不可信文字，在 HTML（以文字呈現、不執行標記）、CSV（防止公式注入）、
  Google Sheets（以文字值寫入）中都必須安全處理。
- 密碼、金鑰、OAuth client secret、授權 token 與憑證檔不得進入 repo、log、Issue 或 PR；
  repo 只提供含變數名稱與假值的 `.env.example`。

**理由**：課程要求學生在搶答結束前看不到其他組的作答狀況，也禁止洩漏機敏資料。

### VI. 驗收情境驅動測試

- 每個驗收 Scenario（含 OpenSpec 對應 Scenario）至少要對應一個自動化測試，測試名稱或註解需標明
  它驗證的是哪一個 Scenario。
- 自動化測試不得呼叫真實的外部服務；Google OAuth 與 Google Sheets API 一律用 mock 或假物件替代。
- 每個子功能合併前，由非實作者依驗收條件人工驗證一次，並在 PR（或子功能目錄下的驗證紀錄）寫下
  日期、實際執行的指令或操作，以及結果數字；沒有實際執行就不得宣稱完成。

**理由**：課程同時要求 AI 自動驗證與人工驗證；以 Scenario 為單位測試，才能證明行為與跨組基準一致。

### VII. 簡單與本機運作

- 系統只需在本機執行，不架設可供外部裝置連線的正式伺服器。
- 活動狀態只存放在後端記憶體中，後端重啟後全部清空；不引入資料庫或持久化儲存。
- 不實作需求以外的功能或抽象層；任何額外複雜度都要在 plan 的 Complexity Tracking 說明理由。

**理由**：期限短（2026-11-30），而且課程只要求本機展示；保持簡單才能確保規格、圖表與程式碼
彼此一致。

## 技術限制與範圍

### 技術棧

- 語言與框架：Python 3 + FastAPI。
- Google Sheets 匯入與寫回：使用 Google Sheets API，以 OAuth 由使用者（老師）自行授權。
- 即時同步：狀態變更必須在 2 秒內反映到老師與各組學生畫面；採 WebSocket 或 SSE 由各子功能的
  plan 決定並說明理由。
- 課程不要求兩組技術相同，只要求功能一致；技術選擇不需與 OpenSpec 組對齊，行為則必須對齊（原則 I）。

### 子功能拆分

與 OpenSpec 組的能力一對一對應，依相依順序開發：

| 子功能目錄 | 對應 OpenSpec 能力 | 相依 |
|---|---|---|
| `specs/001-activity-session/` | activity-session | — |
| `specs/002-guided-notes-import/` | guided-notes-import | 001 |
| `specs/003-round-submission/` | round-submission | 001、002 |
| `specs/004-ranking-review/` | ranking-review | 003 |
| `specs/005-result-export/` | result-export | 002、004 |

核心功能與額外功能（題組、CSV 匯出、公平模式、判錯）都在範圍內。

## 開發流程與品質關卡

- 開發流程遵循 [`docs/PROJECT_WORKFLOW.md`](../../docs/PROJECT_WORKFLOW.md)：先建 Issue，再從最新的
  `main` 建立 `<type>/<issue>-<name>` 分支；commit 格式為 `<type>: <summary>`；PR 以 Squash and
  merge 合併；作者不得核准自己的 PR。
- 每個子功能依序執行 `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks`
  → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`。
- 品質關卡（合併前全部須通過）：
  1. spec 標註對應的 OpenSpec Requirement，偏離項目已在 `docs/alignment.md` 經雙方確認（原則 I）。
  2. `./diagrams/` 內有該子功能的組件圖、類別圖、時序圖及對應 PNG，且與程式碼一致（原則 II）。
  3. plan 的 Constitution Check 逐條檢查本憲章 7 項原則並全部通過，或在 Complexity Tracking 說明理由。
  4. 自動化測試全數通過，並記錄執行指令與結果數字（原則 VI）。
  5. 非實作者完成人工驗證並留下紀錄（原則 VI）。
  6. `git diff --staged` 確認沒有夾帶機敏資料或課程說明、提案草稿等不追蹤檔案（原則 V）。
- spec、plan、tasks、圖表、程式碼任一方有改動時，必須在同一個 PR 內同步其餘部分。

## Governance

- 本憲章優先於其他專案慣例；執行期的開發指引見 `CLAUDE.md` 與 `docs/PROJECT_WORKFLOW.md`。
- **修訂程序**：修改憲章必須開 Issue 並走 PR，經兩位組員（jacky0407、EricC430）都同意後才可合併；
  PR 描述必須說明這次修訂影響哪些既有規格（spec、plan、tasks、圖表），並在同一個 PR 或後續追蹤
  Issue 中同步更新。
- **版本規則**：依語意化版本遞增。MAJOR：移除或重新定義原則、不相容的治理變更；MINOR：新增原則
  或章節，或大幅擴充規範；PATCH：措辭澄清、錯字修正等不改變語意的調整。
- **合規檢查**：每個 PR 的審查者都必須確認變更符合本憲章；`/speckit-plan` 的 Constitution Check 與
  `/speckit-analyze` 的結果需由審查者讀過。違反原則而未在 Complexity Tracking 說明理由的變更，不得合併。

**Version**: 1.0.0 | **Ratified**: 2026-11-20 | **Last Amended**: 2026-11-20
