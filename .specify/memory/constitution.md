# Vibe Coding 課堂搶答系統 Constitution

NCU SE6005 2026 軟體工程期末專題第 16 組 SpecKit 組（jacky0407、EricC430）的專案憲章。
本憲章約束所有子功能的 spec、plan、tasks、圖表、程式碼與 Demo 影片；與其他文件衝突時以本憲章為準。
原則只規定目的與可檢驗的規則；只屬於單一子功能的實作細節，寫在該子功能的 spec 與 plan。

## Core Principles

### I. 跨組行為一致（NON-NEGOTIABLE）

- `docs/openspec-reference/` 收錄的 OpenSpec 組規格中的 SHALL 需求與 Scenario，是本系統使用者
  可見行為的基準。
- 每份子功能 spec 必須標註它對應的 OpenSpec Requirement；每個功能需求與驗收情境都必須能追溯到
  某個 Requirement 或 Scenario。
- 任何偏離或新增的行為，必須先記錄在 `docs/alignment.md`，經雙方確認（確認人欄位不得為「待確認」）
  後才能實作。
- 未記錄的口頭共識視為未確定；讀規格時發現的模糊或衝突，列入 `docs/alignment.md` 的待確認清單，
  不得自行假設答案。

**理由**：課程要求兩組系統功能一致；以對方規格為單一基準並留下書面紀錄，才能避免各自解讀造成
行為分歧。

### II. 圖表生成 (Diagram Generation)（NON-NEGOTIABLE）

原則 II：圖表生成 (Diagram Generation)
名稱：PlantUML 設計優先 (Design-First with PlantUML)
規則：

- **規格制定階段 (Specification Phase)**：在 `/speckit-specify` 階段，必須使用 PlantUML 語法生成
  組件圖 (Component diagram)、類別圖 (Class diagram) 和時序圖 (Sequence diagram)。這些圖表檔案
  (.puml) 必須儲存在 `./diagrams/` 目錄中。
- **產物生成 (Artifact Generation)**：檔案建立後，必須使用 PlantUML CLI
  (`java -jar plantuml.jar "./diagrams/*.puml"`) 將所有 .puml 檔案轉換為 PNG 圖片，且輸出的圖片
  必須儲存在相同的目錄中。
- **規劃階段 (Planning Phase)**：`/speckit-plan` 階段必須將這些圖表作為主要藍圖，用以生成應用程式
  的架構與組件。
- **實作階段 (Implementation Phase)**：在 `/speckit-implement` 階段完成程式碼生成後，必須執行驗證
  步驟，以確保最終的程式碼與圖表完全一致。

註：以上四段依課程說明附錄原文；原文的 `speckit.specify`、`speckit.plan`、`speckit.implement`
已配合 Spec Kit v1.2.1 改寫為 `/speckit-specify`、`/speckit-plan`、`/speckit-implement`，語意不變。

補充規定：

1. `.puml` 與轉出的 PNG 都必須提交；`plantuml.jar` 不提交（已列入 `.gitignore`）。
2. 圖表檔名以子功能編號開頭（例如 `001-activity-session-sequence.puml`），避免子功能之間互相覆蓋。
3. 實作偏離圖表時，必須在同一個 PR 先更新圖表並重新轉出 PNG，不得只改程式碼。

**理由**：課程規定 SpecKit 組須導入 Diagram First Development；把需求先轉成圖，可以讓 AI 有明確的
規劃依據，也讓組員有可視化的審查依據。

### III. Guided Notes 動態定位

- 匯入與寫回都不得寫死工作表名稱或儲存格座標，必須依表頭與合併範圍動態定位。
- 匯入是原子操作：有任何驗證錯誤就整份拒絕，並且不清除既有的成功匯入資料。
- 寫回前（包含每次重試）必須重新驗證來源結構；與匯入時不一致就停止，不得猜測新位置。
- 答案以文字值寫入，不當成公式執行，也不修改非目標儲存格。
- **驗證要求**：匯入與寫回至少要用兩份版面不同的學習單測試（例如起始列欄不同、工作表名稱不同、
  單題與題組混合）。

**理由**：助教會用另一份學習單測試；寫死位置或部分匯入、部分寫入，換表後就會產生錯誤結果，甚至
破壞老師的原始檔案。

### IV. 後端為唯一事實來源

- 提交的先後判定、組別身分、角色權限與輪次狀態，只依據後端產生的資料，不採信前端的宣稱。
- 處理順序在後端保持一致；同一請求重送不得產生重複紀錄。
- 順位計算必須是確定性的：相同的輸入一定得到相同的結果。
- 具體機制（例如接收序號、結果版本）寫在各子功能的 spec 與 plan。

**理由**：搶答的公平性取決於「誰先到」，只有後端能提供可信、可重現的判定依據。

### V. 資料可見性與安全

- 搶答期間，學生只能取得自己組的資料，也不能從任何回應推知他組的進度。
- 不可信的文字輸出到任何格式（畫面、匯出檔、試算表），都必須安全處理，不被當成標記、腳本或公式
  執行；各格式的具體手法寫在子功能的 spec 與 plan。
- 金鑰、token 與憑證不得進入 repo、log、Issue、PR；repo 只提供 `.env.example`。
- **輸入驗證與錯誤處理**：所有外部輸入（活動代碼、組名、答案、匯入資料等）都必須在後端驗證。
  驗證失敗時不得產生部分結果或狀態變更；錯誤訊息要讓使用者看得懂、知道如何修正，且不得暴露堆疊
  追蹤、檔案路徑、憑證或其他內部細節。

**理由**：課程要求學生在搶答結束前看不到其他組的作答狀況，也禁止洩漏機敏資料；輸入錯誤若留下
半套狀態，會破壞搶答結果的可信度。

### VI. 驗收情境驅動測試

- 每個驗收 Scenario 至少對應一個自動化測試，並標明它驗證的是哪一個 Scenario。
- 自動化測試不得呼叫真實的外部服務；Google API 一律用 mock。
- **真實路徑驗證**：凡是用到 Google 的子功能，合併前至少要用真實 Google 試算表（兩份版面）完成
  一次匯入與寫回。形式可以是明確標記、需手動啟動的整合測試，或寫進人工驗證步驟，並記錄結果；
  憑證只放在本機。
- 合併前由非實作者人工驗證，記錄日期、指令或操作，以及結果數字；沒有實際執行就不得宣稱完成。

**理由**：課程同時要求 AI 自動驗證與人工驗證；mock 能讓測試穩定，但正式的 Google 路徑至少要真實
跑過一次，才能證明它真的能用。

### VII. 簡單與本機運作

- 系統只在本機執行，不架設可供外部裝置連線的伺服器。
- 活動狀態只存在後端記憶體，不引入資料庫或持久化儲存，後端重啟就清空。這是全專案的架構限制。
- 不做超出需求的設計；額外的複雜度必須在 plan 的 Complexity Tracking 說明理由。

**理由**：期限短（2026-11-30），而且課程只要求本機展示；保持簡單，才能讓規格、圖表與程式碼彼此
一致。

## 技術限制與範圍

本章是全專案共通、不會因子功能而改變的限制。個別子功能的技術選擇（例如 WebSocket 或 SSE、
Sheets 存取套件）由各子功能的 plan 決定並說明理由。課程不要求兩組技術相同，只要求功能一致。

### 1. 堆疊與執行環境

- Python 3.11 以上 + FastAPI。
- Google Sheets 匯入與寫回使用 Google Sheets API，以 OAuth 由老師自行授權。
- 在組員的 Windows 本機執行；後端只監聽本機位址（localhost），不對外開放。
- 以多個瀏覽器分頁模擬老師與各組學生。

### 2. 程式碼風格

- 遵循 PEP 8。
- 公開的函式、類別、方法都必須有型別提示（Type Hints）與 docstring。
- lint 與格式化工具由 `001-activity-session` 的 plan 決定；定案後依修訂程序補進本章，後續子功能
  都沿用。

### 3. 合規與日誌

- 使用 Python 內建的 `logging` 模組，不得用 `print` 當作日誌。
- 日誌層級固定為 `INFO`，只輸出到 stdout，不寫入檔案。
- 不得記錄 OAuth 授權碼、token、client secret 等機敏資料（對應原則 V）。

### 4. 效能與架構限制

- **效能**：活動階段等狀態變更，必須在 2 秒內反映到老師與各組學生畫面；同步機制由 plan 決定。
  效能驗證至少涵蓋「老師加上 N 組學生」同時連線，N 由 `001-activity-session` 的 plan 決定。
  同時參與組數的上限屬於使用者可見行為，在 `docs/alignment.md` 的 Q-07 確認之前，系統不得自訂上限。
- **架構（NON-NEGOTIABLE）**：核心業務邏輯（學習單結構解析、提交判定、順位計算）必須寫成不依賴
  網路、Web 框架與系統時鐘的純函式，時間由呼叫端傳入。外部服務（Google Sheets、OAuth）與畫面、
  API 放在外層轉接層，相依方向只能由外層指向核心。

### 子功能拆分

與 OpenSpec 組的能力一對一對應，依相依順序開發。核心功能與所有額外功能（題組、CSV 匯出、
公平模式、判錯）都在範圍內。調整拆分必須走本憲章的修訂程序。

| 子功能目錄 | 對應 OpenSpec 能力 | 相依 |
|---|---|---|
| `specs/001-activity-session/` | activity-session | — |
| `specs/002-guided-notes-import/` | guided-notes-import | 001 |
| `specs/003-round-submission/` | round-submission | 001、002 |
| `specs/004-ranking-review/` | ranking-review | 003 |
| `specs/005-result-export/` | result-export | 002、004 |

## 開發流程與品質關卡

- 開發流程遵循 [`docs/PROJECT_WORKFLOW.md`](../../docs/PROJECT_WORKFLOW.md)：先建 Issue；分支名稱為
  `<type>/<issue>-<name>`；commit 格式為 `<type>: <summary>`；PR 用 Squash and merge；作者不得核准
  自己的 PR。
- 每個子功能依序執行 `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks`
  → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`。
- **合併前的品質關卡**（全部都要通過）：
  1. spec 已標註對應的 OpenSpec Requirement，偏離項目已在 `docs/alignment.md` 經雙方確認（原則 I）。
  2. `./diagrams/` 有該子功能的組件圖、類別圖、時序圖及 PNG，且與程式碼一致（原則 II）。
  3. plan 的 Constitution Check 逐條通過，或在 Complexity Tracking 說明理由。
  4. 自動化測試全數通過，並記錄執行指令與結果數字（原則 VI）。
  5. 涉及 Google 的子功能已完成真實路徑驗證（原則 VI）。
  6. 非實作者已完成人工驗證並留下紀錄（原則 VI）。
  7. 確認沒有夾帶機敏資料或不追蹤的檔案（原則 V）。
- **一致性**：spec、plan、tasks、圖表、程式碼、Demo 影片任一方有改動，都必須同步其餘部分；
  程式碼與文件的同步要在同一個 PR 內完成。錄製 Demo 影片前，依規章第 11 節鎖定該版本的 Git tag，
  確保影片、程式碼與文件一致。
- **執行提醒**：憲章不保證會被自動遵守。原則 III、V、VI 與架構限制，必須在各子功能的
  `/speckit-specify`、`/speckit-plan` prompt 中再明確寫一次。

## Governance

- 本憲章優先於其他專案慣例；執行期的開發指引見 `CLAUDE.md` 與 `docs/PROJECT_WORKFLOW.md`。
- **修訂程序**：修改憲章必須開 Issue 並走 PR，經兩位組員（jacky0407、EricC430）都同意後才可合併；
  PR 必須說明這次修訂影響了哪些既有規格（spec、plan、tasks、圖表）。
- **版本規則**：依語意化版本遞增。MAJOR：移除或重新定義原則；MINOR：新增原則或章節、大幅擴充規範；
  PATCH：措辭澄清。
- **合規檢查**：每個 PR 的審查者都必須確認變更符合本憲章；`/speckit-plan` 的 Constitution Check 與
  `/speckit-analyze` 的結果必須由審查者讀過。

**Version**: 1.0.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21
