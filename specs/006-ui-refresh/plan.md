# Implementation Plan: 006 介面改版（User Interviews 風格）

**Branch**: `feature/28-006-ui-refresh` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-ui-refresh/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖 [006-ui-refresh-component.puml](../../diagrams/006-ui-refresh-component.puml)：呈現層（三頁版面、投影畫面、共用元件、設計基準值、互動回饋、本機字型與插圖）→ 既有畫面邏輯 → 後端，後端不變。
- 類別圖 [006-ui-refresh-class.puml](../../diagrams/006-ui-refresh-class.puml)：設計基準值、共用元件（含分頁標籤、題號導覽列）、頁面版面（含投影畫面與結果卡片）、插圖、互動回饋。
- 時序圖 [006-ui-refresh-sequence.puml](../../diagrams/006-ui-refresh-sequence.puml)：學生送出的狀態回饋與同步中斷；關輪後判錯時投影畫面的遞補。

**前置條件**：本分支疊在 `feature/9-005-result-export`（PR #25，@ f0f45da）上；001～005 的畫面以該版本為基準。依 spec Assumptions，本功能是**實驗分支**，暫不修改憲章；實作完成並評估後才決定是否併入 main，併入前要先修訂憲章的子功能拆分表。

## Summary

把老師頁、學生頁、首頁改成 User Interviews 風格（暖色畫布、薄荷卡片、深青主色、襯線標題、膠囊按鈕、無陰影、手繪線稿插圖），並加入三項互動：老師頁左右兩欄＋右欄分頁（依階段自動切換）、學生頁題號導覽與四種送出狀態、新的唯讀投影畫面（搶答中只顯示公開資訊，關輪後即時呈現每題結果與遞補）。技術上沿用原生 HTML／CSS／ES modules：設計基準值集中在 `tokens.css`，既有區塊原封搬進新版面（id 不變），新功能都寫成獨立模組，只觀察既有 DOM 與快照；投影畫面沿用老師的同步通道，以純函式白名單轉出投影檢視（研究 R5）。後端不修改。

## Technical Context

**Language/Version**：HTML5、CSS（自訂屬性、`@media`、`position: sticky`）、原生 JavaScript ES modules（瀏覽器直接載入）；測試與工具為 Python 3.11 以上（沿用）

**Primary Dependencies**：執行期不新增任何相依（後端沿用 FastAPI 送出靜態檔）。字型子集化工具 fonttools、brotli 列為選用 extra `fonts`，只在開發者重新產生字型時安裝（研究 R3）

**Storage**：無。介面狀態只存在瀏覽器記憶體；老師 token 沿用 001 的 localStorage 保存方式

**Testing**：pytest；`tests/unit/ui/`（對比、色碼、字型子集，純 Python）；`tests/browser/test_ui_*.py`（shared、student、teacher、status、projection、a11y、home、screens；沿用 `tests/browser/cdp.py` 的真實瀏覽器與真實 uvicorn，Google 用假替身）；既有 `perf` 測試；ruff、ruff format、mypy（`src/`，本功能不新增 Python 原始碼，只新增 `scripts/build_font_subset.py`）

**Target Platform**：Windows 本機，後端只監聽 127.0.0.1；瀏覽器為近期版本的 Chrome／Edge（學生手機瀏覽器同為 Chromium 或 Safari 近期版本）

**Project Type**：單一 web 服務（後端 + 靜態前端），只改靜態前端

**Performance Goals**：狀態變更 2 秒內反映到所有畫面（含投影畫面，FR-034）；新資料提示 ≤ 2 秒；過場不延遲新內容超過 0.3 秒（FR-014）；首頁主插圖 ≤ 300KB、字型總量 ≤ 600KB（離線本機載入）

**Constraints**：不改後端與 API；不改既有元素 id 與子功能腳本的行為（[contracts/ui-dom.md](contracts/ui-dom.md)）；色碼只在 `tokens.css`；離線可用（不載入外部網域的字型、圖片、樣式；Google 匯入本身仍需網路）；WCAG 2.1 AA；`prefers-reduced-motion`；375～1440px；投影 1280×720／1920×1080

**Scale/Scope**：三個既有頁面＋一個新頁面；最多 99 組、50 題（001 A2、005）；新增 5 個 JS 模組（`teacher-layout.js`、`question-nav.js`、`feedback.js`、`projection.js`、`projection-view.js`），修改 2 個既有模組各一處

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致 | 不新增、刪除或改變 OpenSpec 規定的功能（FR-001）；spec 的 Traceability 列出呈現方式受影響的 Requirement 作為回歸條件；投影畫面只呈現 OpenSpec「關輪公開結果」範圍內的資料，屬畫面設計，不需記入 alignment.md（spec Clarifications 第 2 題） | 通過 |
| II 圖表生成 | 三張圖已在 specify／clarify 階段產出並轉 PNG（`diagrams/006-*`）；本 plan 以圖為藍圖；implement 後需比對程式與圖（tasks 要列） | 通過 |
| III Guided Notes 動態定位 | 不改匯入與寫回的邏輯；兩份版面學習單的既有測試照跑（FR-003） | 不適用（回歸由既有測試保證） |
| IV 後端為唯一事實來源 | 送出狀態、結果、遞補都只依後端回應與快照顯示；前端不自行判定成功（研究 R6、R7）；投影畫面以 `resultVersion` 丟棄舊結果 | 通過 |
| V 資料可見性與安全 | 學生頁不新增他組資訊（FR-002、FR-008a）；投影畫面以白名單純函式隔離老師快照，搶答中不讀 `submissions.current`（研究 R5、[contracts/projection-view.md](contracts/projection-view.md)）；不可信文字一律 `textContent`；token 不進網址、畫面或 console；不新增任何輸入或驗證規則，既有錯誤訊息照原文顯示 | 通過 |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 對應 `tests/browser/test_ui_*.py` 或 `tests/unit/ui/` 的測試（tasks 列對照）；不呼叫真實 Google；不涉及新的 Google 路徑（真實路徑驗證不適用）；非實作者人工驗證依 quickstart C | 通過 |
| VII 簡單與本機運作 | 不加框架、建置步驟、資料庫；只在本機；額外複雜度見 Complexity Tracking | 通過（有記錄） |
| 技術限制 1～3 | Python 端只新增工具腳本（型別提示、docstring、logging）；ruff／mypy 照跑；不記錄 token | 通過 |
| 技術限制 4（效能、架構） | 後端核心不動；2 秒同步以既有 perf 測試重驗（SC-008）；投影的白名單函式是前端純函式，依賴方向為呈現層 → 既有畫面邏輯 | 通過 |
| 子功能拆分 | 憲章拆分表只列 001～005，006 沒有對應的 OpenSpec 能力 | **偏離，見 Complexity Tracking** |

**Phase 1 設計後重新檢查**：data-model、三份 contracts、quickstart 沒有引入新的後端需求或資料範圍；投影白名單的禁止事項都有對應測試（contracts/projection-view.md「測試對應」）；結論不變。

## Project Structure

### Documentation (this feature)

```text
specs/006-ui-refresh/
├── spec.md
├── plan.md              # 本檔
├── research.md          # R1～R12
├── data-model.md        # 介面組成元素
├── quickstart.md        # 驗證步驟
├── contracts/
│   ├── ui-dom.md            # 保留的 id、新增結構、既有腳本允許的修改
│   ├── projection-view.md   # 投影檢視白名單
│   └── design-tokens.md     # 基準值名稱與對比檢查組合
├── checklists/requirements.md
├── illustrations.md     # （implement）插圖來源紀錄：AI 工具、提示詞、日期
├── screenshots/         # （implement）A4 產生的截圖
├── verification.md      # （implement）驗證紀錄
└── tasks.md             # /speckit-tasks 產生
```

### Source Code (repository root)

```text
src/lecture_quiz/adapters/static/
├── index.html                 # 改：首頁（主插圖、老師／學生入口）
├── teacher.html               # 改：兩欄＋分頁；既有 section 原封搬入面板
├── student.html               # 改：本組資訊列、題號導覽容器、空狀態
├── projection.html            # 新：唯讀投影畫面
├── css/
│   ├── tokens.css             # 新：唯一定義數值的地方
│   ├── app.css                # 改寫：基礎、共用元件、老師／學生版面（類別名稱保留）
│   └── projection.css         # 新：投影版面
├── fonts/                     # 新：NotoSerifTC-subset.woff2、Inter、IBMPlexMono、OFL.txt
├── img/
│   ├── illustrations.svg      # 新：空狀態插圖精靈圖（Claude 手寫）
│   └── hero.webp              # 新：首頁主插圖（組員以 AI 生成）
└── js/
    ├── teacher-layout.js      # 新：分頁、階段自動切換、「有更新」、階段進度、開啟投影
    ├── question-nav.js        # 新：學生題號導覽
    ├── feedback.js            # 新：新資料提示（MutationObserver）
    ├── projection-view.js     # 新：toProjectionView 純函式（白名單）
    ├── projection.js          # 新：投影畫面連線與渲染
    ├── submission.js          # 改一處：data-submit-state
    └── round-submission.js    # 改一處：data-urgent
scripts/
└── build_font_subset.py       # 新：字型子集化（開發者手動執行）
tests/
├── unit/ui/
│   ├── test_contrast.py
│   ├── test_no_hardcoded_colors.py
│   └── test_font_subset.py
└── browser/
    ├── test_ui_shared.py、test_ui_student.py、test_ui_teacher.py、test_ui_status.py
    └── test_ui_projection.py、test_ui_a11y.py、test_ui_home.py、test_ui_screens.py
docs/DEVELOPMENT.md            # 改：前端擴充約定（研究 R11）
pyproject.toml                 # 改：新增選用 extra `fonts`
```

**Structure Decision**：沿用既有的單一 web 服務與 `adapters/static/` 結構；新增程式全部在呈現層。後端（`core/`、`app/`、`adapters/web`、`adapters/google`）不修改；`main.py` 已以 `StaticFiles` 送出整個 `static/`，新頁面與資源不需要新增路由。

## 實作順序（給 /speckit-tasks 參考）

1. **基礎**：`tokens.css`、字型子集、`app.css` 共用元件；`tests/unit/ui/` 三個測試先寫並確認負對照失敗（US1）。
2. **學生頁**（P1）：版面、送出狀態、倒數提示、題號導覽、375px（US2）。
3. **老師頁**：兩欄、分頁、階段進度、主要操作樣式、表格（US3）；狀態標籤與新資料提示（US4）。
4. **投影畫面**：白名單純函式與測試 → 頁面 → 遞補過場（US7）。
5. **首頁與插圖**：手寫 SVG 空狀態；提供主插圖提示詞給組員；暫代 SVG（US5）。
6. **無障礙與回歸**：鍵盤、對比、200% 縮放、減少動態效果、離線、截圖、perf、圖與程式一致性檢查（US6、憲章原則 II）。
7. **評估**：依 quickstart C 做人工驗證，寫 verification.md，決定是否併入 main（併入才修訂憲章）。

## Complexity Tracking

| 偏離 | 為什麼需要 | 為什麼不用更簡單的做法 |
|---|---|---|
| 新增憲章拆分表沒有的子功能 006（沒有對應的 OpenSpec 能力） | 介面改版跨越 001～005 的所有畫面，不屬於任何單一子功能；用獨立的 spec／plan／tasks 才能追蹤與評估 | 分散到 001～005 各自修改會讓五份 spec 同時變動且難以整體回退；2026-11-25 決定先以實驗分支進行，評估後若併入 main，合併前修訂憲章拆分表並經兩位組員同意 |
| 投影畫面在前端過濾老師快照，而不是由後端提供公開檢視 | FR-031 規定不得新增後端資料或權限；老師快照已含全部所需資料，且只在老師自己的瀏覽器執行 | 後端新增「投影檢視者」角色最安全，但要改 001 的身分模型與快照裁切，違反 FR-031 與「只改呈現」的範圍；以白名單純函式＋搶答中 DOM 檢查測試控制風險（研究 R5） |
| 新增選用 extra `fonts`（fonttools、brotli）與子集化腳本 | 中文襯線標題要離線可用，完整字型檔過大 | 直接用系統字體：Windows 沒有適合的中文襯線字；用 CDN：違反 FR-006 |
