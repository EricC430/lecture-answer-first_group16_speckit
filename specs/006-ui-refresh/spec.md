# Feature Specification: 介面改版——幾何記號（UI Refresh，huashu-design dir-3）

**Feature Branch**: `feature/28-006-ui-huashu`（Issue #28；原從 `origin/feature/9-005-result-export` 開出，005（#25）與 #30 合併 main 後，2026-11-25 依 Issue 的分支策略 rebase 到 main，PR base 為 `main`）

**Created**: 2026-11-25

**Status**: Draft（待非實作者人工驗證，見 quickstart.md）

**Input**: Issue #28「006-ui-refresh 前端介面改版」：在不改變使用者可見行為的前提下改善老師頁、學生頁的介面設計。

**採用的設計**：以 huashu-design skill 產出三個方向（`design-demos/dir-1～3.html`），兩位組員中的 EricC430 於 2026-11-25 選定 **dir-3 幾何記號**（`direction-approved.md`）。本 spec 描述的是 dir-3，**不是**已關閉的 PR #32（taste-skill 版，`feature/28-006-ui-refresh` 分支）。子功能編號與目錄名稱沿用 Issue #28 的 `006-ui-refresh`。

**撰寫順序說明**：本子功能先依 huashu-design 流程完成設計與實作（PR #33 第一個 commit），spec、plan、tasks 與圖表於同日補寫，內容依已實作的程式與測試整理，並在補寫過程中發現且修正了一處與 OpenSpec 的不一致（FR-006，結果版本守衛）。

**OpenSpec Capability**：無對應能力（只改外觀）。下表列出本子功能**畫面會呈現**的 OpenSpec 行為，確認呈現方式不改變其規定。

## OpenSpec Traceability *(mandatory — 憲章原則 I)*

| OpenSpec Requirement | OpenSpec Scenario | 本 spec 對應 | 偏離或新增 |
|---|---|---|---|
| activity-session：階段同步與本機存續 | 關輪同步；重連或重啟 | US1-AS5、FR-001、FR-005 | 無。階段軌與總覽只讀 001 推送的快照，沿用 sync.js 的版本丟棄與同步中斷橫幅 |
| activity-session：關輪與定案順序 | （本文：結果公布不等於定案） | US1-AS2、US1-AS3、FR-003 | 無。總覽的成功題數只計已定案輪次；未定案的勝出組標示「待定案」 |
| round-submission：搶答中依角色限制資料 | 檢查學生資料回應；老師即時看板 | US1-AS1、US3、FR-004、FR-010 | 無。總覽只在老師頁；學生頁新增的只有本組記號與倒數圓環，不含他組資料 |
| round-submission：關輪公開結果與版本一致 | 延遲回應 | US1-AS2、FR-006 | 無。總覽套用 004 的結果版本守衛，較舊的 `resultVersion` 不覆蓋題目狀態 |
| round-submission：倒數與輸入安全顯示 | 無倒數輪次 | US3-AS1、US3-AS2、FR-008、FR-010 | 無。圓環只是輔助，倒數文字與「由老師結束」提示維持 003 原樣；組號等文字一律 `textContent` |
| ranking-review：判錯及撤銷判錯、老師確認定案與歷史鎖定 | （本文） | US2-AS1、FR-007 | 無。順位列只多一個組別記號，按鈕與文字不變 |

**未涵蓋的 OpenSpec Requirement**：不適用——本子功能不實作任何 OpenSpec 行為，只改變呈現方式。

**alignment.md**：依 PROJECT_WORKFLOW 第 10 節，「畫面排版與文字措辭」屬設計方式，不需與 OpenSpec 組討論。本輪總覽只重新排列老師原本就看得到的資料（001 的階段、輪次、組別成功次數，003 的送出狀況，004 的搶答成功者與定案狀態），沒有新增資料種類，也沒有改變學生可見的資料，因此不記入 `docs/alignment.md`。Issue #28 要求「動到畫面上顯示哪些資訊時回到該子功能 spec 確認」：學生頁顯示的資訊不變（004 FR-037 的可見性不受影響）。

## Diagrams *(mandatory — 憲章原則 II)*

| 圖表 | 原始檔 | PNG |
|---|---|---|
| 組件圖 (Component) | `diagrams/006-ui-refresh-component.puml` | `diagrams/006-ui-refresh-component.png` |
| 類別圖 (Class) | `diagrams/006-ui-refresh-class.puml` | `diagrams/006-ui-refresh-class.png` |
| 時序圖 (Sequence) | `diagrams/006-ui-refresh-sequence.puml` | `diagrams/006-ui-refresh-sequence.png` |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 老師一眼掌握本輪狀態（Priority: P1）

老師把筆電接上投影機，需要在後排也看得出現在第幾輪、在哪個階段、每題誰搶到了、哪些題還沒解。

**Why this priority**：老師是整場活動的操作者，原本這些資訊分散在活動區塊、作答看板與順位區塊，要往下捲才拼得出全貌。

**Independent Test**：建立活動、開一輪、送出、關輪、定案，在老師頁檢查總覽內容（`tests/browser/test_pages.py::test_teacher_overview_shows_stage_winners_and_solved_count`）。

**Acceptance Scenarios**：

1. **Given** 第 1 輪搶答中、題 3 已有 1 組送出，**When** 老師頁收到快照，**Then** 總覽顯示輪次、「搶答中」與倒數（無倒數時顯示「本輪沒有倒數，由老師關輪」），題 3 方塊顯示「作答中・1 組送出」。
2. **Given** 已關輪、結果未定案，**When** 題 3 有暫定搶答成功者第 2 組，**Then** 方塊顯示「第 2 組・待定案」與第 2 組記號，成功題數不增加。
3. **Given** 老師確認定案，**When** 快照更新，**Then** 題 3 方塊顯示「第 2 組・第 1 輪」，成功題數加一；本輪沒有人成功的題顯示「第 1 輪未成功」。
4. **Given** 題目從未開過，**Then** 方塊顯示「未出題」（有格數時前面加格數）。
5. **Given** 任一階段，**Then** 頁首階段軌把目前階段標為目前步驟（`aria-current="step"`）、之前的階段標為已完成；沒有活動時全部清除；已取消時另外標示「已取消」。

### User Story 2 - 用幾何記號辨識組別（Priority: P1）

每組有固定的形狀（第 1 組紅圓、第 2 組黑方……），老師投影與學生手機用同一個記號，學生能快速認出「這是我們」。

**Why this priority**：組號只是數字，投影上要逐字讀；形狀可以一眼辨認。

**Independent Test**：`tests/unit/frontend/test_glyph.py`（node 執行真正的 `glyph.js`）與 `tests/browser/test_pages.py::test_group_glyphs_accompany_group_numbers_on_both_pages`。

**Acceptance Scenarios**：

1. **Given** 有組別加入並送出，**Then** 老師頁組別表、作答看板表頭、順位列，以及學生頁本組標示都出現該組的記號。
2. **Given** 任一記號，**Then** 它是裝飾（`aria-hidden`、不帶文字），旁邊一律仍寫「第 N 組」；既有文字內容不變。
3. **Given** 組號 1～99，**Then** 第 1～6 組各一種形狀，第 7～12 組換一組顏色重複，第 13 組起回到第一組顏色，同一組號在所有畫面記號相同。

### User Story 3 - 學生看得懂剩餘時間（Priority: P2）

**Why this priority**：學生在時間壓力下作答，圓環比一行文字更快讀出「還剩多少」。

**Independent Test**：`tests/browser/test_pages.py::test_student_countdown_ring_follows_deadline_only_while_round_is_open`。

**Acceptance Scenarios**：

1. **Given** 搶答中且有倒數，**Then** 學生頁顯示圓環與剩餘秒數，圓環比例隨時間縮短。
2. **Given** 不在搶答中，或本輪沒有倒數，**Then** 圓環隱藏，003 的「本輪沒有倒數，由老師結束」提示照常顯示。
3. **Given** 任一情況，**Then** 截止判定、表單停用時機與 001 的倒數文字都不變（圓環只讀快照的 `deadline`）。

### User Story 4 - 一致的視覺基準與可讀性（Priority: P2）

**Independent Test**：`tests/architecture/test_ui_tokens.py`、`tests/browser/test_pages.py::test_pages_fit_phone_width_without_horizontal_scroll`，以及 001～005 既有的全部測試。

**Acceptance Scenarios**：

1. **Given** `app.css` 與三個頁面，**Then** 色碼只定義在 `:root`，其餘一律引用 CSS 變數，頁面沒有 `style` 屬性。
2. **Given** 畫面使用的文字／背景配對，**Then** 對比度都至少 4.5:1（WCAG AA）。
3. **Given** 375 寬的手機，**Then** 首頁、老師頁、學生頁都沒有整頁水平捲動（寬表格在自己的捲動區內）。
4. **Given** 001～005 的所有功能，**Then** DOM id、按鈕行為、API 呼叫、文字內容不變，既有測試全部通過。

### Edge Cases

- 老師頁在換活動時：總覽、階段軌、倒數一併清除（`onTeacherReset`），新活動第一份快照到達才再顯示。
- 題數很多（例如 50 題）：題目方塊自動換行排列，不固定為 4 格。
- 組數超過 6：記號換色重複，仍以「第 N 組」文字區分。
- 同步中斷：沿用 sync.js 的橫幅與「成功提示隱藏」規則（`body.sync-broken .success-hint`），本子功能沒有新增成功提示。
- 學生頁在倒數途中重新整理：圓環的分母改為重新整理當下的剩餘秒數（比例從滿圈開始），秒數仍正確；這是展示上的取捨，見 Assumptions。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**：頁首 MUST 顯示活動階段軌（準備中、開放加入、搶答中、結果未定案、結果已定案、已結束），依快照標示目前與已完成的階段；已取消另外標示。
- **FR-002**：老師頁 MUST 在有活動時顯示本輪總覽：輪次與模式、階段（搶答中時加倒數）、已定案成功題數／總題數、每題狀態方塊、各組成功次數。
- **FR-003**：總覽的「已成功」與成功題數 MUST 只計已定案輪次的搶答成功者；未定案輪的勝出組 MUST 標示「待定案」。
- **FR-004**：總覽 MUST 只出現在老師頁，只讀老師版快照，不呼叫任何 API、不改變其他模組的狀態。
- **FR-005**：總覽 MUST 依 sync.js 已接受的最新快照更新，換活動時清除。
- **FR-006**：總覽 MUST 套用 004 的結果版本守衛（`acceptRankingRounds`）：收到較舊的 `resultVersion` 時不更新題目方塊與成功題數。
- **FR-007**：組別記號 MUST 由組號決定（6 種形狀 × 2 組顏色循環），出現在組別表、作答看板表頭、順位列與學生頁本組；記號 MUST 為裝飾（`aria-hidden`），旁邊 MUST 保留「第 N 組」文字。
- **FR-008**：學生頁 MUST 在搶答中且有倒數時顯示倒數圓環與剩餘秒數，其他時候隱藏；截止判定以後端為準，不改變 003 的表單停用時機。
- **FR-009**：所有色彩 MUST 定義為 `app.css` `:root` 的 CSS 變數；文字與背景對比 MUST 至少 4.5:1。
- **FR-010**：所有新增的文字輸出 MUST 使用 `textContent`，不使用會解析 HTML 的 API（憲章原則 V）。
- **FR-011**：既有頁面的所有 DOM id、`data-feature` 區塊與 script 載入 MUST 保留；001～005 的行為不變。
- **FR-012**：版面 MUST 在 1440 寬與 375 寬都可用，手機寬度沒有整頁水平捲動。

### Key Entities

- **組別記號（Glyph）**：組號 → `{shape: 1..6, tone: a|b}`，以 `data-shape`、`data-tone` 交給 CSS 畫出。
- **題目狀態（QuestionState）**：`idle`（未出題）、`open`（作答中）、`pending`（待定案）、`solved`（已成功）、`missed`（某輪未成功），附勝出組號、輪次、送出組數。只在前端由快照推得，不保存。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：既有測試與新增測試全部通過（`pytest`、`ruff check`、`ruff format --check`、`mypy`），紀錄在 quickstart.md。
- **SC-002**：畫面使用的 11 組文字／背景配對對比度全部 ≥ 4.5:1（`test_ui_tokens.py`）。
- **SC-003**：兩輪真實流程（建立、匯入、6 組加入、作答、關輪、判錯、定案）的截圖中，頁面 JS 錯誤為 0；改版前後截圖存於 `screenshots/before`、`screenshots/after`。
- **SC-004**：非實作者在 1440 寬與手機上依 quickstart.md 操作一次，確認 US1～US4 並留下紀錄。
- **SC-005**：投影到教室螢幕時，後排可讀出輪次、階段、各題勝出組別（人工驗證，記錄距離與結果）。

## Assumptions

- 字型使用 Windows 內建（微軟正黑體、Bahnschrift、Consolas），不載入外部字型或 CDN，本機離線可用。
- 圓環的分母是「第一次看到這個截止時間時的剩餘秒數」，因為快照只提供 `deadline`、沒有開輪秒數；圓環只是輔助，確切秒數由數字顯示。若日後快照提供倒數總秒數，再改用它。
- 學生頁不新增本輪總覽，也不顯示他組記號以外的資訊；學生頁順位區塊沿用 004 FR-037 的可見範圍，只多記號。
- 首頁只是入口，沒有功能規格；改版後仍提供「老師頁」「學生頁」兩個連結。
