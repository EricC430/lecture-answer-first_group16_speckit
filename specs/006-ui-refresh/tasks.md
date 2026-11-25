---

description: "006 介面改版的任務清單"
---

# Tasks: 006 介面改版（User Interviews 風格）

**Input**: Design documents from `/specs/006-ui-refresh/`

**Prerequisites**: [plan.md](plan.md)、[spec.md](spec.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)、[quickstart.md](quickstart.md)

**Tests**: REQUIRED（專案覆寫，憲章 v1.1.0 原則 VI）。每個 Acceptance Scenario 至少一個自動化測試，任務描述標明驗證的 Scenario；本功能不呼叫 Google（真實瀏覽器測試沿用 `tests/browser/conftest.py` 的假替身）。測試先寫、先確認失敗，再實作。

**Diagrams**: REQUIRED（憲章原則 II）。`diagrams/006-ui-refresh-{component,class,sequence}.puml` 與 PNG 已存在（2026-11-25）；Polish 有一致性驗證任務。

**Architecture**: 本功能不改後端核心。前端唯一的「核心」是純函式 `toProjectionView`（`js/projection-view.js`：不讀 DOM、時間、網路、全域狀態），與渲染、連線的 `js/projection.js` 分開列出；相依方向為呈現層 → 既有畫面邏輯 → 後端（組件圖）。

**範圍提醒**：本分支是實驗分支（spec Assumptions），疊在 `feature/9-005-result-export` 上。既有子功能腳本只允許 [contracts/ui-dom.md](contracts/ui-dom.md)「既有腳本允許的修改」列出的修改；所有既有元素 id 不得改名或刪除。

路徑前綴：`static/` = `src/lecture_quiz/adapters/static/`。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可平行（不同檔案、不依賴未完成任務）
- **[Story]**：所屬 User Story（US1～US7）

---

## Phase 1: Setup（共用工具）

- [X] T001 在 `pyproject.toml` 新增選用 extra `fonts = ["fonttools>=4.50", "brotli>=1.1"]`（不放進核心相依或 `dev`；研究 R3）
- [X] T002 [P] 新增 `scripts/build_font_subset.py`：參數 `--source-dir`（已下載的 TTF 目錄，預設讀環境變數 `FONT_SOURCE_DIR`，缺少時明確失敗並說明要下載哪三個檔）與 `--out-dir`（預設 `static/fonts/`）；收集 `static/` 下所有 `*.html`、`*.js` 中出現的 CJK 字元＋ASCII 可見字元，輸出 `NotoSerifTC-600-subset.woff2`（Noto Serif TC 600 字重子集）、`Inter-latin.woff2`（可變字體 Latin 子集）、`IBMPlexMono-400-latin.woff2`、`IBMPlexMono-600-latin.woff2`，並複製 `OFL.txt`；用 `logging`（INFO）輸出每個檔的大小，不用 `print`；型別提示與 Google docstring（憲章技術限制 2）
- [X] T003 依 T002 下載 google/fonts 的 `ofl/notoseriftc/NotoSerifTC[wght].ttf`、`ofl/inter/Inter[opsz,wght].ttf`、`ofl/ibmplexmono/IBMPlexMono-Regular.ttf`、`IBMPlexMono-SemiBold.ttf` 到 repo 外的暫存目錄，執行腳本產生 `static/fonts/*`；確認字型總量 ≤ 600KB（plan Performance Goals），把指令與各檔大小記入 `specs/006-ui-refresh/verification.md`
- [X] T004 [P] 在 `tests/browser/cdp.py` 的 `Page` 新增：`set_viewport(width, height)`（`Emulation.setDeviceMetricsOverride`）、`emulate_media(reduced_motion: bool)`（`Emulation.setEmulatedMedia` 的 `prefers-reduced-motion`）、`screenshot(path)`（`Page.captureScreenshot`，存成 PNG）、`network_urls()`（收集 `Network.requestWillBeSent` 的網址）；不改既有方法的行為

---

## Phase 2: Foundational（所有 User Story 的前置）

**⚠️ 本階段完成前不得開始任何 User Story**

### 測試（先寫、先失敗）

- [X] T005 [P] 新增 `tests/unit/ui/test_contrast.py`：解析 `static/css/tokens.css` 的 `--color-*`，依 [contracts/design-tokens.md](contracts/design-tokens.md) 的「文字對比（≥ 4.5:1）」與「介面圖形對比（≥ 3:1）」逐組計算 WCAG 2.1 對比；含負對照 `#777777` on `#ffffff`（4.48:1）必須被判不合格；契約列出的基準值缺少時測試失敗（FR-025、SC-003）
- [X] T006 [P] 新增 `tests/unit/ui/test_no_hardcoded_colors.py`：掃描 `static/css/app.css`、`static/css/projection.css` 與 `static/*.html` 的 `style` 屬性，出現 `#[0-9a-fA-F]{3,8}`、`rgb(`、`rgba(`、`hsl(` 即失敗（`tokens.css` 除外；允許 `transparent`、`currentColor`）；含負對照：對一段內含 `#fff` 的字串呼叫同一個判定函式必須回報違規（FR-004）
- [X] T007 [P] 新增 `tests/unit/ui/test_font_subset.py`：用 fontTools 讀 `static/fonts/NotoSerifTC-600-subset.woff2` 的 cmap，檢查 `static/` 下 `*.html` 的 `h1`～`h4` 文字與 `*.js` 字串常值中出現的 CJK 字元全部在子集內，缺字時列出缺的字並提示重跑 `scripts/build_font_subset.py`；fontTools 未安裝時**明確失敗**並提示安裝 `.[fonts]`（不得 `importorskip`）；同時確認 `static/fonts/OFL.txt` 存在（研究 R3）

### 實作

- [X] T008 新增 `static/css/tokens.css`：依 [research.md](research.md) R2 的色彩表（含 `--color-on-primary: #ffffff`、`--color-border: #a2cbcd`、`--color-border-strong: #5b7c80`）與 [data-model.md](data-model.md)「設計基準值」表（字級 `--text-xs` 13px～`--text-display` 44px、間距 `--space-1`～`--space-8` 為 4、8、16、24、32、40、48、64px、`--radius-pill: 999px`、`--radius-card: 12px`、`--radius-field: 8px`、`--tap-min: 44px`、`--layout-max: 1280px`、`--sidebar-width: 360px`、`--duration-fast: 150ms`、`--duration-base: 250ms`、`--duration-highlight: 1500ms`）；字體堆疊 `--font-heading`、`--font-body`、`--font-mono` 依研究 R3；`@media (prefers-reduced-motion: reduce)` 內把三個 duration 設為 `0ms`。這是全站唯一出現色碼的檔案
- [X] T009 改寫 `static/css/app.css` 的基礎層：`@font-face`（四個本機字型，`font-display: swap`）、`body`（`--color-canvas` 底、`--font-body`、16px、行高 1.6）、`h1`～`h4`（`--font-heading`）、`.eyebrow`（`--font-mono`、大寫、字距 0.05em、`--text-xs`）、連結、`:focus-visible`（3px `--color-focus` 外框＋2px 間隔）、全域 `prefers-reduced-motion` 規則（`animation: none`、`transition: none`）、保留 `[hidden] { display: none !important; }`；只能用 `var(--…)`（研究 R2、R8）
- [X] T010 在 `static/css/app.css` 實作共用元件（[data-model.md](data-model.md)「共用元件」表）：按鈕（預設 `button` 為幽靈外框樣式；`.btn-primary`、`.btn-secondary`、`.btn-danger`；`:disabled`、`[aria-busy="true"]`；`min-height` 與 `min-width` 為 `var(--tap-min)`、相鄰間距 ≥ `--space-2`、`--radius-pill`）、輸入欄位（`--color-border-strong` 外框、`--radius-field`、`[aria-invalid="true"]`）、`section[data-feature]` 卡片（`--color-card`、`--radius-card`、無陰影）、`.table-scroll`（`overflow-x: auto`）與表格樣式、`.status-label` 與 `--success`／`--danger`／`--warning`／`--neutral`（圖示以 CSS `mask-image` 的 SVG data URI 呈現，SVG 內不得含色碼，底色用 `currentColor`）、`.error-message`、`.error`、`.notice`、`#sync-banner`（sticky、`--color-warning-bg`）、`.empty-state`；既有類別名稱（[contracts/ui-dom.md](contracts/ui-dom.md)）全部保留並改用基準值（FR-005、FR-015、FR-027）
- [X] T011 在 `static/teacher.html`、`static/student.html`、`static/index.html` 的 `<head>` 於 `css/app.css` 之前加入 `<link rel="stylesheet" href="css/tokens.css">`；不改其他內容
- [X] T012 執行 `.venv\Scripts\pytest tests/unit/ui` 確認 T005～T007 通過且負對照被判不合格；再執行 `.venv\Scripts\pytest` 確認既有測試全數通過（只換樣式的回歸檢查），結果數字記入 `verification.md`

**Checkpoint**：基礎完成，User Story 可以開始

---

## Phase 3: User Story 1 - 三個頁面套用一致的新視覺 (Priority: P1) 🎯 MVP

**Goal**：三頁使用同一套樣式，功能與顯示資訊與改版前一致。

**Independent Test**：只完成本階段時，走完整流程，每一步結果與改版前相同、既有測試全過。

### Tests for User Story 1

- [X] T013 [P] [US1] 新增 `tests/browser/test_ui_shared.py::test_pages_use_shared_component_styles`（US1-AS1）：分別開啟 `index.html`、`teacher.html`、`student.html`，以 `getComputedStyle` 檢查 `body` 背景等於 `--color-canvas`、`h1`／`h2` 字體堆疊以 Noto Serif TC 開頭、可見按鈕的 `border-radius` ≥ 22px（膠囊）、`.error-message` 底色等於 `--color-danger-bg`
- [X] T014 [P] [US1] 新增 `tests/browser/test_ui_shared.py::test_information_items_unchanged_through_full_flow`（US1-AS2、FR-001、FR-002、SC-002）：以 `World` 走「建立 → 匯入 → 開放加入 → 兩組加入 → 開輪 → 作答 → 關輪 → 判錯 → 定案 → 結束 → 寫回預覽」，每個階段比對老師頁與學生頁上的資訊元素（`#activity-code`、`#activity-max-groups`、`#activity-stage`、`#activity-questions`、`#groups-body` 列數、`#round-questions`、`#student-code`、`#student-group`、`#student-credential`、`#student-stage`、`#student-open-questions`、`#export-preview-summary` 等）的文字與後端 `GET /snapshot` 回傳一致，且學生頁在搶答中不出現他組答案

### Implementation for User Story 1

- [X] T015 [US1] 在 `static/teacher.html`、`static/student.html` 加入頁首：系統名稱、頁面名稱（`<p class="eyebrow">`＋`<h1>`）；各子功能區塊的 `<h2>` 上方加 `<p class="eyebrow">`（例如「STEP · 匯入」）；不改任何既有 id、`data-feature` 與 script（[contracts/ui-dom.md](contracts/ui-dom.md)）
- [X] T016 [US1] 改寫 `static/css/app.css` 檔尾 001～005 的子功能樣式（`.activity-code`、`.countdown`、`.controls`、`.submission-board`、`.answer-text`、`.published-round`、`.ranking-*`、`.export-*`）只引用基準值，並把 `table` 預設設為在其父容器內可水平捲動；`.ranking-entry.status-*` 的外觀對應到 `.status-label` 的四種樣式（[data-model.md](data-model.md)「狀態標籤對照」）（FR-015、FR-019）
- [X] T017 [US1] 在 `static/teacher.html` 把靜態表格（`#groups-table`、匯入結果、匯入問題、寫回核對、寫回預覽）外包 `<div class="table-scroll">`；JS 產生的表格（`.submission-board`）以 CSS 處理，不改腳本（FR-019）
- [X] T018 [US1] 執行 T013、T014 與全部既有 `tests/browser/` 測試，通過數記入 `verification.md`（US1-AS3）

**Checkpoint**：MVP——三頁新視覺，功能不變

---

## Phase 4: User Story 2 - 學生在手機上清楚、安心地作答 (Priority: P1)

**Goal**：學生頁在 375px 可完整使用；送出四種狀態、倒數醒目、同步中斷清楚、題號導覽。

**Independent Test**：375px 寬度完成加入與一次作答，並在送出時模擬斷線。

### Tests for User Story 2（`tests/browser/test_ui_student.py`）

- [X] T019 [P] [US2] `test_submit_button_shows_busy_done_and_error_states`（US2-AS1、FR-009）：送出時卡片 `data-submit-state` 依序為 `busy`→`done`；在關輪後送出得到 `error`，錯誤訊息出現在該卡片內、按鈕恢復可操作（未鎖定時）；`busy` 期間按鈕 `disabled`
- [X] T020 [P] [US2] `test_countdown_is_prominent_and_marks_urgent_without_blinking`（US2-AS2、FR-010）：倒數字級 ≥ `--text-xl`；剩餘 ≤ 10 秒時倒數元素有 `data-urgent`，計算後的 `animation-name` 為 `none`；無倒數輪次顯示既有文字「本輪沒有倒數，由老師結束。」
- [X] T021 [P] [US2] `test_html_answer_rendered_as_text`（US2-AS3、FR-011 ↔ OpenSpec「特殊文字答案」）：送出 `<img src=x onerror=alert(1)>` 後，學生頁與老師頁顯示原字串，DOM 中沒有 `img` 元素被建立
- [X] T022 [P] [US2] `test_sync_broken_banner_hides_success_and_does_not_cover_inputs`（US2-AS4、FR-012）：停止後端連線後 `#sync-banner` 可見、`body.sync-broken` 存在、`data-submit-state="done"` 卡片的成功文字與 `.success-hint` 不可見；橫幅的矩形與第一個 `textarea`、送出按鈕的矩形不重疊
- [X] T023 [P] [US2] `test_student_page_shows_only_own_group_while_round_open`（US2-AS5、FR-002 ↔ OpenSpec「檢查學生資料回應」）：第 2 組送出後，第 1 組學生頁的 DOM 文字不含第 2 組答案，題號導覽只反映第 1 組的狀態
- [X] T024 [P] [US2] `test_student_page_fits_375px_with_44px_targets`（US2-AS6、FR-007、FR-027）：`set_viewport(375, 812)` 下 `document.documentElement.scrollWidth <= clientWidth`；所有可見的 `button`、`a`、`input`、`textarea` 的 `getBoundingClientRect` 寬高 ≥ 44（`textarea` 只檢查高度）
- [X] T025 [P] [US2] `test_question_nav_lists_questions_with_own_status_and_moves_focus`（US2-AS7、FR-008a）：開 2 題時 `#question-nav` 出現 2 個項目，文字含「未送出」；送出第 1 題後該項變為「已送出」；點第 2 題後 `document.activeElement` 是第 2 題的標題；只開 1 題時導覽隱藏；捲到底時導覽仍在視窗內且不遮倒數

### Implementation for User Story 2

- [X] T026 [US2] 在 `static/js/submission.js` 的 `renderAnswerForm` 只增加屬性（[contracts/ui-dom.md](contracts/ui-dom.md)「既有腳本允許的修改」）：建立時 `form.dataset.question = questionNumber`、`form.dataset.submitState = "idle"`；`setBusy(true)` 設 `busy`；`showError` 設 `error`；`showSubmitted` 設 `done`；`setBusy(false)` 且未鎖定時回到 `idle`。送出流程、停用規則與文字不變
- [X] T027 [US2] 在 `static/js/countdown.js`（001 共用倒數，實際顯示倒數的模組；原寫 `round-submission.js`，2026-11-25 實作時更正）只增加：剩餘 ≤ 10 秒時對倒數元素設定 `data-urgent`，否則移除；倒數計算不變
- [X] T028 [P] [US2] 新增 `static/js/question-nav.js`：以 `MutationObserver` 監看 `#answer-forms` 的子元素與各 `form[data-question]` 的 `data-submit-state`；題數 ≥ 2 時在 `#question-nav`（`<nav aria-label="題號導覽">`）產生每題一個連結（文字「第 N 題・未送出／送出中／已送出」＋圖示），為卡片 `h4` 補上 `id="q-heading-N"` 與 `tabindex="-1"`，點擊後捲動並 `focus()`；資料只來自本頁本組卡片（[data-model.md](data-model.md)「學生頁題號導覽」）
- [X] T029 [US2] 改寫 `static/student.html` 結構：在 `#round-submission-section` 內 `#answer-forms` 之前加入 sticky 的 `#answer-sticky`（本組、階段、倒數的唯讀鏡像 `#answer-group`、`#answer-stage`、`#answer-countdown`，由 `question-nav.js` 從 001 元素複製文字，001 元素原地不動）與 `<nav id="question-nav" aria-label="題號導覽" hidden></nav>`、尚未開輪時的 `.empty-state`（插圖留到 US5）、頁尾加 `<script type="module" src="js/question-nav.js"></script>`
- [X] T030 [US2] 在 `static/css/app.css` 實作學生版面：本組資訊列與倒數 sticky（倒數 `--text-xl` 以上、`--font-mono`）、`#question-nav` sticky 在資訊列下方且高度 ≤ 56px、作答卡片依 `data-submit-state` 呈現 `.status-label` 對應樣式（`busy`→warning、`done`→success、`error`→danger）、`[data-urgent]` 的警示外觀（不閃爍）、`body.sync-broken [data-submit-state="done"] .submit-status { visibility: hidden; }`、375px 以下單欄與 `textarea` 寬度 100%（FR-007～FR-012）

**Checkpoint**：學生端在手機可用，US1＋US2 各自可測

---

## Phase 5: User Story 3 - 老師一眼掌握活動進度並找到下一步 (Priority: P2)

**Goal**：老師頁兩欄＋分頁、階段進度、每階段一個主要按鈕、表格易讀、新資料提示。

**Independent Test**：以老師身分走完整流程，每個階段檢查階段指示、主要按鈕、分頁切換。

### Tests for User Story 3（`tests/browser/test_ui_teacher.py`）

- [X] T031 [P] [US3] `test_stage_progress_marks_current_stage_with_text`（US3-AS1、FR-017）：各階段 `#stage-progress [aria-current="step"]` 的文字等於 001 `STAGE_LABELS` 對應文字
- [X] T032 [P] [US3] `test_exactly_one_primary_button_per_stage`（US3-AS2、FR-018）：每個階段左欄與作用中分頁內可見的 `.btn-primary` 計算樣式（背景色為 `--color-primary`）恰好一個，且是下列對照的按鈕：`PREPARING`→`#open-joining`、`JOINING`→`#open-round-panel button[type=submit]`、`ROUND_OPEN`→`#close-round`、`RESULT_PENDING`→`.ranking-finalize`、`RESULT_FINAL`→`#open-round-panel button[type=submit]`、`ENDED`→`#export-preview-button`；`#cancel-activity`、`#end-activity` 呈現危險樣式
- [X] T033 [P] [US3] `test_new_submission_row_is_highlighted_without_stealing_focus`（US3-AS3、FR-020）：老師焦點在某按鈕時學生送出，作答看板新增的列帶 `.is-new`，2 秒內移除，`document.activeElement` 不變
- [X] T034 [P] [US3] `test_ranking_status_labels_and_judge_button_adjacent`（US3-AS4）：關輪後每個候選列有 `.status-label`（文字＋圖示）；「判錯」按鈕與目前成功者在同一列
- [X] T035 [P] [US3] `test_export_confirm_disabled_until_preview_and_replacements_marked`（US3-AS5）：預覽前 `#export-confirm-button` 為 `disabled`；預覽後覆寫列的 `.export-impact-replace` 以危險色呈現
- [X] T036 [P] [US3] `test_import_issues_table_readable`（US3-AS6）：以會失敗的學習單匯入，`#import-issues-body` 每列五欄都有內容，表格在 `.table-scroll` 內
- [X] T037 [P] [US3] `test_two_column_layout_with_sticky_sidebar`（US3-AS7、FR-017a）：1280 寬時 `#teacher-sidebar` 與 `#teacher-workspace` 左右並排；捲動右欄後側欄仍在視窗內
- [X] T038 [P] [US3] `test_tabs_auto_switch_only_on_stage_change`（US3-AS8、FR-017b）：各階段自動選取對照分頁（[data-model.md](data-model.md)「老師頁分頁」）；老師手動切到「匯入」後，同一階段內收到新快照不會被切走，下一次階段改變才切
- [X] T039 [P] [US3] `test_updated_badge_on_background_tab`（US3-AS9、FR-017c）：老師停在「匯入」時學生送出，「作答看板」標籤出現 `.tab-badge`（含文字「有更新」）且不自動跳轉；打開後標記消失
- [X] T040 [P] [US3] `test_tab_visibility_follows_section_visibility`（US3-AS10、FR-017d）：活動取消後沒有「寫回」分頁；各分頁可見與否等於面板內區塊的 `hidden`
- [X] T041 [P] [US3] `test_single_column_below_1024`（US3-AS11）：`set_viewport(1000, 800)` 時側欄在上、分頁在下，沒有整頁水平捲動
- [X] T042 [P] [US3] `test_tabs_keyboard_navigation`（FR-017e）：焦點在分頁列時方向鍵移動焦點、Enter 選取；`aria-selected`、`aria-controls`、`tabindex` 正確

### Implementation for User Story 3

- [X] T043 [US3] 改寫 `static/teacher.html` 結構（[contracts/ui-dom.md](contracts/ui-dom.md)「新增的結構」）：`<div class="teacher-layout">` 內左欄 `<aside id="teacher-sidebar">` 放 `<ol id="stage-progress">`、原 `#activity-section`（含 `#open-round-panel`）與 `<button id="open-projection" type="button" hidden>開啟投影畫面</button>`；右欄 `<div id="teacher-workspace">` 放 `<div id="teacher-tabs" role="tablist">` 四個 `role="tab"` 按鈕與四個 `role="tabpanel"`：`#panel-import` 放 `#import-section`、`#panel-board` 放 `#round-submission-section` 與 `#published-section`、`#panel-ranking` 放 `#ranking-review-section`、`#panel-export` 放 `#export-section`；既有 section 原封搬移；頁尾加 `js/teacher-layout.js` 與 `js/feedback.js` 的 script（排在既有 script 之後）
- [X] T044 [US3] 新增 `static/js/teacher-layout.js`（研究 R4、[data-model.md](data-model.md)「老師頁分頁」轉換規則 1～4）：`MutationObserver` 監看各面板內 `section` 的 `hidden` 決定分頁標籤顯示；`onTeacherSnapshot` 取得 `stage`，只在 `stage !== lastStage` 時依對照表切換（`CANCELLED` 不切換；目標不可見時選第一個可見分頁）；非作用中面板的 DOM 變動加 `.tab-badge`（文字「有更新」＋圖示）；WAI-ARIA Tabs 鍵盤操作（左右方向鍵、Home／End 移動焦點，Enter／空白鍵選取）；把 `document.body.dataset.stage` 設為目前階段；依 001 `STAGE_LABELS` 產生 `#stage-progress` 並在目前階段設 `aria-current="step"`；活動存在時顯示 `#open-projection`
- [X] T045 [US3] 在 `static/css/app.css` 實作老師版面：`.teacher-layout` 在 ≥ 1024px 為 `var(--sidebar-width)` ＋ 彈性右欄的 grid，側欄 `position: sticky`；< 1024px 單欄；分頁列（膠囊標籤、選取中以 `--color-primary` 底線、`.tab-badge`）；`#stage-progress` 的步驟樣式（目前階段以文字＋粗體＋主色標記，不只靠顏色）；依 `body[data-stage]` 把 T032 對照表中的按鈕套用主要按鈕外觀，`#cancel-activity`、`#end-activity` 套用危險外觀（FR-017、FR-017a、FR-018）
- [X] T046 [P] [US3] 新增 `static/js/feedback.js`（研究 R7）：`MutationObserver` 監看 `#submission-board`、`#published-list`、`#ranking-review-list`、`#projection-results`（存在者），對新加入的列元素加 `.is-new`，`--duration-highlight` 後移除；不呼叫 `focus()`；`app.css` 中 `.is-new` 為背景淡出動畫，減少動態效果時改為靜態外框（FR-016、FR-020）

**Checkpoint**：老師頁新版面完整，US1～US3 各自可測

---

## Phase 6: User Story 4 - 狀態變化有一致的視覺語意與適度動畫 (Priority: P2)

**Goal**：所有狀態在兩頁使用同一套標籤；尊重減少動態效果；重連後不閃回舊資料。

**Independent Test**：含判錯與撤銷的流程檢查標籤一致；開啟減少動態效果再走一次。

### Tests for User Story 4（`tests/browser/test_ui_status.py`）

- [X] T047 [P] [US4] `test_status_labels_consistent_across_pages`（US4-AS1、FR-015）：搶答成功、答錯、搶答失敗、未成功、已送出、送出失敗在老師頁與學生頁的元素計算樣式（文字色、底色）相同，且每個標籤有非空的圖示（`::before` 的 `mask-image` 不為 `none`）與文字
- [X] T048 [P] [US4] `test_reduced_motion_disables_animation`（US4-AS2、FR-016）：`emulate_media(reduced_motion=True)` 後，`.is-new`、分頁切換、投影遞補元素的計算 `animation-duration` 與 `transition-duration` 皆為 `0s`
- [X] T049 [P] [US4] `test_reconnect_shows_latest_without_flashback`（US4-AS3、FR-014 ↔ OpenSpec「重連或重啟」「延遲回應」）：中斷再恢復後，在 0.3 秒內的多次取樣中結果區不出現比最新 `resultVersion` 舊的成功者

### Implementation for User Story 4

- [X] T050 [US4] 在 `static/css/app.css` 完成狀態對照：依 [data-model.md](data-model.md)「狀態標籤對照」把 004 的 `.ranking-entry.status-success|correct|wrong|failed`、003 的 `.success-hint` 與 `.submit-status.error-message`、005 的寫回狀態文字容器（`#export-status-text`）、001 的 `#sync-banner` 套用 `.status-label` 的同一組樣式與圖示；不修改 003～005 的腳本
- [X] T051 [US4] 在 `static/css/app.css` 檢查並統一所有過場只使用 `opacity`、`background-color`、`transform` 與 `--duration-*`；確認過場在內容更新後才播放（`.is-new` 由新節點觸發，不延遲渲染）（FR-014、研究 R8）

**Checkpoint**：狀態語意一致

---

## Phase 7: User Story 7 - 老師可以投影給全班看的唯讀畫面 (Priority: P2)

**Goal**：唯讀投影畫面，搶答中只顯示公開資訊；關輪後即時呈現每題結果與遞補。

**Independent Test**：從老師頁開啟投影，走開放加入 → 開輪 → 作答 → 關輪 → 判錯 → 撤銷 → 定案，每階段檢查內容。

### Tests for User Story 7（`tests/browser/test_ui_projection.py`）

- [X] T052 [P] [US7] `test_projection_view_whitelist_round_open`（[contracts/projection-view.md](contracts/projection-view.md) 禁止事項 1、FR-032）：在瀏覽器以 ES module 載入 `js/projection-view.js`，把搶答中真實後端產生的老師快照（含 `submissions.current` 各組答案）交給 `toProjectionView`，輸出 `mode === "round"`，序列化後不含任何已送出答案字串，也沒有 `answers`、`entries`、`groupNumber`、`order`、`receivedAt` 鍵
- [X] T053 [P] [US7] `test_projection_view_whitelist_never_leaks_private_fields`（禁止事項 2、FR-031）：對各階段的老師快照，輸出序列化後不含 `reason`、`countAtProcessing`、`groupCounts`、`actions`、`ownGroup`、`groups`、`credential`、`token` 鍵
- [X] T054 [P] [US7] `test_projection_view_only_current_round`（禁止事項 3、US7-AS7）：第一輪定案後開第二輪，輸出 `mode === "round"` 且沒有 `results`；第二輪關輪後 `results` 只含第二輪題號
- [X] T055 [P] [US7] `test_open_projection_from_teacher_page`（US7-AS1、FR-030）：點 `#open-projection` 開啟 `projection.html?code=…` 新分頁，頁面沒有任何 `button`、`input`、`form`
- [X] T056 [P] [US7] `test_projection_lobby_shows_large_code`（US7-AS2、FR-036）：`set_viewport(1920, 1080)` 時 `#projection-code` 高度 ≥ 1080 × 8%、其餘文字 ≥ 24px；1280×720 時不捲動即可看到代碼
- [X] T057 [P] [US7] `test_projection_hides_answers_while_round_open`（US7-AS3、FR-032、SC-010 ↔ OpenSpec「檢查學生資料回應」）：兩組送出後，投影畫面 DOM 文字只有代碼、階段、題號、模式、倒數，不含任何答案、組號或送出數量；重新整理投影畫面後再檢查一次（spec Edge Case）
- [X] T058 [P] [US7] `test_projection_results_cards_after_close`（US7-AS4、FR-033 ↔ OpenSpec「結果公布與後續輪次」）：關輪後每題一張卡片，依送出先後列出組號、答案（純文字）、順位、`.status-label`；目前成功者有醒目樣式；無人提交題顯示「未成功」
- [X] T059 [P] [US7] `test_projection_shows_replacement_within_2s`（US7-AS5、FR-034、FR-035、SC-010）：判錯目前成功者，投影畫面在 2 秒內把該組標「答錯」、下一組標「搶答成功」並出現「第 N 組遞補」；重複量測 10 次，記錄最大延遲
- [X] T060 [P] [US7] `test_projection_undo_restores_within_2s`（US7-AS6）：撤銷判錯後 2 秒內恢復原成功者
- [X] T061 [P] [US7] `test_projection_final_and_next_round`（US7-AS7）：定案後顯示「結果已定案」；開下一輪時結果卡片立即消失（spec Edge Case「下一輪開輪的瞬間」）
- [X] T062 [P] [US7] `test_projection_ended_and_cancelled`（US7-AS8）：結束時顯示未成功題；取消時顯示已取消
- [X] T063 [P] [US7] `test_projection_sync_broken_hides_winner`（US7-AS9）：中斷時顯示中斷提示，成功者標示不可見
- [X] T064 [P] [US7] `test_projection_without_teacher_token_shows_hint`（spec Edge Case「投影畫面的連結被學生打開」）：清除 localStorage 後開啟投影畫面，只顯示「請從老師頁開啟投影畫面」，沒有建立 WebSocket 連線
- [X] T065 [P] [US7] `test_projection_stale_result_version_ignored`（contracts「版本處理」、OpenSpec「延遲回應」）：以較小 `resultVersion` 的快照呼叫渲染入口，結果區不變

### Implementation for User Story 7

- [X] T066 [P] [US7] 新增 `static/js/projection-view.js`：匯出純函式 `toProjectionView(snapshot, hasTeacherToken)`，嚴格依 [contracts/projection-view.md](contracts/projection-view.md) 的輸出表建立新物件；`mode === "round"` 時**不讀取** `submissions.current`；只輸出目前輪；不讀 DOM、時間、網路或全域狀態；階段文字從 `teacher.js` 匯出的 `STAGE_LABELS` 取得（若 import `teacher.js` 會觸發副作用，改為把 `STAGE_LABELS` 搬到新的無副作用模組 `js/stage-labels.js` 並由 `teacher.js` 重新匯出，`teacher.js` 的行為不變）
- [X] T067 [US7] 新增 `static/projection.html`（`#projection-root`、`#projection-code`、`#projection-stage`、`#projection-countdown`、`#projection-results`、`#sync-banner`，不含任何操作元件；載入 `css/tokens.css`、`css/app.css`、`css/projection.css`）與 `static/js/projection.js`：從 `location.search` 取 `code`，以 `identity.getTeacherToken(code)` 取得 token，沒有則顯示提示且不連線；有則 `sync.connectSync` 連線，`onSnapshot` 只把 `toProjectionView` 的輸出交給渲染；渲染一律 `textContent`；各輪記住最大 `resultVersion`，較小者不更新；倒數依 `deadline` 每秒更新（無截止顯示「由老師結束」）
- [X] T068 [US7] 在 `static/js/projection.js` 實作遞補呈現：比較同一題前後兩次的 `successGroup`，改變且 `replacedGroup` 存在時在卡片上顯示「第 N 組遞補」，原成功者轉為「答錯」標籤，套用 `--duration-base` 的過場（減少動態效果時直接切換）（FR-035）
- [X] T069 [US7] 新增 `static/css/projection.css`：1920×1080 下 `#projection-code` 與 `#projection-countdown` 字高 ≥ 8vh、其餘文字 ≥ 24px；結果卡片網格；題數或組數放不下時自動輪播卡片（每 8 秒換一組卡片，目前成功者固定可見；減少動態效果時改為無動畫的分頁切換）（FR-036、FR-037）
- [X] T070 [US7] 在 `static/js/teacher-layout.js` 讓 `#open-projection` 以 `window.open("projection.html?code=" + encodeURIComponent(code), "_blank", "noopener")` 開啟（token 不放網址）

**Checkpoint**：投影畫面完成，搶答中不洩漏、關輪後即時遞補

---

## Phase 8: User Story 6 - 符合無障礙基本要求 (Priority: P2)

**Goal**：鍵盤可完成所有操作、對比 AA、錯誤訊息靠近欄位、200% 縮放可用。

**Independent Test**：只用鍵盤走老師與學生主要流程；對比測試全過。

### Tests for User Story 6（`tests/browser/test_ui_a11y.py`）

- [X] T071 [P] [US6] `test_keyboard_only_teacher_and_student_flow`（US6-AS1、FR-026、SC-004）：以 CDP `Input.dispatchKeyEvent` 只用 Tab／Shift+Tab／Enter／空白鍵／方向鍵完成「建立 → 開放加入 → 開輪 → 關輪」與學生「加入 → 送出」；每次 Tab 後 `document.activeElement` 的 `:focus-visible` 外框寬度 ≥ 3px
- [X] T072 [P] [US6] `test_contrast_tokens_meet_aa`（US6-AS2、FR-025）：執行 T005 的判定並額外以 `getComputedStyle` 抽查三頁實際渲染的文字／背景組合 ≥ 4.5:1
- [X] T073 [P] [US6] `test_field_errors_near_field_and_announced`（US6-AS3、FR-028）：學生加入時輸入錯誤活動代碼，錯誤訊息位於表單內、有 `role="alert"`，各欄位有可見 `label`
- [X] T074 [P] [US6] `test_zoom_200_percent_no_overlap`（FR-029）：以 `set_viewport(720, 450)` 加上 `deviceScaleFactor` 模擬 200% 縮放，三頁沒有整頁水平捲動，主要按鈕的矩形互不重疊

### Implementation for User Story 6

- [X] T075 [US6] 依 T071～T074 的失敗結果修正 `static/css/app.css` 與各 HTML 的 `label`／`aria-*`（只能加屬性與樣式，不改 id 與腳本）；全部修正後重跑並記錄

**Checkpoint**：無障礙底線達成

---

## Phase 9: User Story 5 - 首頁與空狀態使用手繪插圖 (Priority: P3)

**Goal**：首頁有主插圖與兩個入口；空狀態有小插圖與說明；離線完整。

**Independent Test**：開首頁與兩頁初始狀態，拔網路後仍完整。

### Tests for User Story 5（`tests/browser/test_ui_home.py`）

- [X] T076 [P] [US5] `test_home_has_title_illustration_and_role_links`（US5-AS1、FR-021）：首頁有系統名稱、說明、主插圖（`img` 有非空 `alt`）、`#role-teacher` 與 `#role-student` 兩個連結，可用 Tab 到達、尺寸 ≥ 44×44
- [X] T077 [P] [US5] `test_empty_states_show_illustration_and_next_step`（US5-AS2、FR-022）：老師頁尚無組別、尚未匯入，學生頁尚未開輪時，對應 `.empty-state` 可見且含說明文字與 `use` 元素
- [X] T078 [P] [US5] `test_pages_load_no_external_resources`（US5-AS3、FR-006、SC-009）：以 `network_urls()` 收集首頁、老師頁、學生頁、投影畫面載入的網址，除 `127.0.0.1` 以外為 0（老師頁的 Google Picker 只在按下匯入後才載入，不在此檢查範圍）；`document.fonts` 中四個字型狀態為 `loaded`
- [X] T079 [P] [US5] `test_decorative_illustrations_hidden_from_assistive_tech`（US5-AS4、FR-024）：所有 `.empty-state svg` 有 `aria-hidden="true"`；主插圖有替代文字

### Implementation for User Story 5

- [X] T080 [P] [US5] 新增 `static/img/illustrations.svg`：手寫 `<symbol>` `empty-groups`、`empty-import`、`empty-round`、`empty-results`（單一線寬的手繪線稿，輪廓 `stroke: currentColor`，平塗用 `var(--illus-fill-1)`、`var(--illus-fill-2)`，在 `tokens.css` 對應 `--color-accent`、`--color-rose`；檔內不得有色碼），主題為本系統情境；另加 `hero-placeholder` 供主插圖交付前使用（研究 R9）
- [X] T081 [P] [US5] 撰寫首頁主插圖的 AI 提示詞與規格（1600×1000、WebP、≤ 300KB、色票取自 `tokens.css`、主題「幾組學生圍桌舉手搶答，旁邊有大計時器」、手繪單線條＋青與玫瑰平塗、無文字無 logo、不模仿任何品牌插圖），寫入 `specs/006-ui-refresh/illustrations.md`，並在對話中交給組員
- [ ] T082 [US5] **（組員）** 依 T081 的提示詞以 AI 生成主插圖，下載原檔交給 Claude；在 `illustrations.md` 記錄生成工具、日期，以及確認該服務允許用於課堂專題與 Demo 影片
- [ ] T083 [US5] 把組員交付的原檔轉為 `static/img/hero.webp`（寬 1600、≤ 300KB），更新 `illustrations.md` 的檔名與大小；在 T082 完成前首頁使用 `hero-placeholder`
- [X] T084 [US5] 改寫 `static/index.html`：系統名稱、說明、主插圖（`<img src="img/hero.webp" alt="幾組學生圍著桌子舉手搶答，旁邊有一個大計時器" width height>`，未交付前為 `<svg><use href="img/illustrations.svg#hero-placeholder">` 並附 `role="img"` 與 `aria-label`）、`<a id="role-teacher" href="teacher.html">` 與 `<a id="role-student" href="student.html">` 大按鈕
- [X] T085 [US5] 在 `static/teacher.html`、`static/student.html` 加入 `.empty-state`（`<svg aria-hidden="true"><use href="img/illustrations.svg#…"></use></svg>`＋一句說明下一步）：老師頁 `#groups-empty` 旁用 `empty-groups`、`#panel-import` 尚未匯入用 `empty-import`、`#panel-ranking` 尚無結果用 `empty-results`；學生頁尚未開輪用 `empty-round`。顯示與否用 CSS 依既有元素的 `hidden` 或內容是否為空判斷，不改腳本

**Checkpoint**：所有 User Story 完成

---

## Phase 10: Polish & Cross-Cutting Concerns

- [ ] T086 [P] 新增 `tests/browser/test_ui_screens.py::test_capture_screenshots`：依 quickstart B，三頁 × 375／768／1024／1440 與投影 × 1280×720／1920×1080，在各主要階段存截圖到 `specs/006-ui-refresh/screenshots/`；人實際打開每一張檢查文字重疊、截斷、整頁水平捲動，結果記入 `verification.md`（SC-002、SC-005）
- [X] T087 [P] 更新 `docs/DEVELOPMENT.md` 的前端擴充約定：老師頁新區塊要放進右欄分頁面板（或在 `teacher-layout.js` 對照表登記新分頁）、新樣式只能用 `tokens.css` 的基準值、`projection-view.js` 白名單修改要同步契約與測試（研究 R11）
- [X] T088 程式碼與圖表一致性驗證：逐一比對 `diagrams/006-ui-refresh-{component,class,sequence}.puml` 與實作（頁面、模組、元件類別、分頁、題號導覽、投影畫面與結果卡片、送出與遞補時序）；有差異時先更新圖表並以 `java -jar plantuml.jar -charset UTF-8 "./diagrams/006-*.puml"` 重新轉出 PNG，打開確認（憲章原則 II）
- [X] T089 執行 `.venv\Scripts\pytest` 全部自動化測試（含 001～005 既有測試與 `tests/browser/`、`tests/unit/ui/`），記錄指令與通過／失敗／略過數（憲章原則 VI、FR-003、SC-001）
- [X] T090 效能驗證：執行 `.venv\Scripts\pytest -m perf`（老師 + 6 組、每組 2 條連線），確認狀態變更 2 秒內反映，記錄數字；另記錄 T059 的 10 次遞補延遲最大值（SC-008、SC-010、憲章技術限制 4）
- [X] T091 執行 `.venv\Scripts\ruff check .`、`.venv\Scripts\ruff format --check .`、`.venv\Scripts\mypy`，全部通過並記錄（憲章技術限制 2）
- [X] T092 檢查日誌與機敏資料：`scripts/build_font_subset.py` 只用 `logging`；前端沒有 `console.log` 輸出 token；`projection.html` 網址不含 token；`git status` 沒有夾帶字型來源 TTF、`.env` 或憑證（憲章技術限制 3、原則 V）
- [X] T093 （憲章原則 III）本功能不改匯入與寫回邏輯：確認 002、005 以兩份版面學習單的既有測試（`tests/fixtures/guided_notes_layouts.py` 的 `layout_a`、`layout_b`）在 T089 中全部通過
- [ ] T094 非實作者依 [quickstart.md](quickstart.md) C 的 14 個步驟人工驗證，記錄日期、操作、結果數字（SC-004 鍵盤、SC-006 學生 1 分鐘內送出、SC-007 老師 5 秒內找到下一步、SC-011 8 公尺讀取代碼）到 `verification.md`（憲章原則 VI）
- [ ] T095 評估與決定：依 `verification.md` 與截圖，兩位組員決定是否併入 main；若併入，先修訂憲章「子功能拆分」表（加入 006、註明無對應 OpenSpec 能力）並經兩位組員同意，再更新 CLAUDE.md「專案現況」；若不併入，保留分支並在 Issue #28 記錄結論（spec Assumptions、plan Complexity Tracking）
- [X] T096 本功能沒有新的 Google 路徑：真實 Google 路徑驗證不適用（憲章原則 VI）；在 `verification.md` 註明理由

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：無相依。T003 依賴 T001、T002。
- **Foundational（Phase 2）**：依賴 Setup；T005～T007 先寫並確認失敗，再做 T008～T011；T012 為檢查點。**阻擋所有 User Story。**
- **US1（Phase 3）**：依賴 Phase 2。
- **US2（Phase 4）**：依賴 Phase 2；與 US1 改不同區塊，但 `app.css` 共用，建議在 US1 之後。
- **US3（Phase 5）**：依賴 Phase 2；T043 改 `teacher.html` 結構，需在 US1 的 T015、T017 之後。
- **US4（Phase 6）**：依賴 US2（`data-submit-state`）與 US3（`feedback.js`）。
- **US7（Phase 7）**：依賴 Phase 2 與 US3 的 T044（`#open-projection`）；T066 可在 Phase 2 後立即開始。
- **US6（Phase 8）**：依賴 US1～US4、US7 的畫面完成。
- **US5（Phase 9）**：依賴 Phase 2；T082 由組員執行，可隨時進行；T083 依賴 T082。
- **Polish（Phase 10）**：依賴所有要交付的 User Story。

### Within Each User Story

- 測試先寫、先確認失敗，再實作。
- HTML 結構 → 模組 → 樣式。
- 每個階段完成後在檢查點驗證，再進下一個。

### Parallel Opportunities

- Phase 1：T002、T004 可平行。
- Phase 2：T005、T006、T007 可平行。
- 每個 User Story 的測試任務都標 [P]（同一測試檔內的不同測試函式，可由同一人一次寫完，或分批寫）。
- T066（純函式）與 US3 的實作可平行；T080、T081 與其他 Story 可平行；T082 由組員平行進行。

---

## Parallel Example: User Story 7

```text
# 先平行寫測試（同一檔案 tests/browser/test_ui_projection.py 內的不同函式）：
T052 白名單：搶答中
T053 白名單：私有欄位
T054 白名單：只有目前輪

# 純函式與 HTML 可平行：
T066 static/js/projection-view.js
T067 static/projection.html + static/js/projection.js
```

---

## Implementation Strategy

### MVP First（US1）

1. Phase 1 → Phase 2（基準值、字型、共用元件；既有測試全過）。
2. Phase 3（US1）：三頁新視覺、功能不變。
3. **停下驗證**：T018 全過、截圖看過，再繼續。

### Incremental Delivery

1. US1 → US2（學生作答，P1）→ 驗證
2. US3 → US4（老師頁與狀態語意）→ 驗證
3. US7（投影畫面）→ 驗證，特別是搶答中不洩漏
4. US6（無障礙）→ US5（插圖）→ Polish
5. 11/29 凍結前未完成的部分不併入（spec Assumptions）；T095 決定是否併入 main。

---

## Notes

- 每個任務完成後 commit（`<type>: <summary>`，例如 `style: 老師頁改為兩欄與分頁 (#28)`）。
- 勾選任務前必須實際執行對應驗證，並在 `verification.md` 留下日期、指令、數字。
- 既有子功能腳本只能做 [contracts/ui-dom.md](contracts/ui-dom.md) 允許的修改；需要更多修改時，先更新契約與 plan。
