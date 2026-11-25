# Tasks: 介面改版——幾何記號（UI Refresh，huashu-design dir-3）

**Input**：`specs/006-ui-refresh/` 的 spec.md、plan.md、三張圖

**說明**：本子功能先依 huashu-design 流程設計與實作，tasks 於 2026-11-25 補寫，已完成的項目附上證據（commit 或測試）。依憲章原則 VI，每個 User Story 都有測試任務。

## Format: `[ID] [P?] [Story] Description`

## Phase 1: 設計方向（huashu-design 三方向門）

- [x] T001 寫設計需求 `design-spec.md`（受眾、核心資訊、輸出格式、約束）
- [x] T002 寫六張方向卡 `directions.md`（最佳設計師 ×2、現實參照 ×2、秒數輪盤 ×2），挑三張做完整初稿
- [x] T003 [P] 做三個初稿 `design-demos/dir-1～3.html` 並截圖，打磨一輪（`polish-log.md`）
- [x] T004 記錄選定方向 `direction-approved.md`（2026-11-25，「這三個設計我最喜歡dir-3」）
- [ ] T005 jacky0407 確認採用 dir-3（Issue #28 驗收條件「兩位組員選定」）

## Phase 2: Foundational

- [x] T010 `js/glyph.js`：`glyphKind`、`glyph`、`renderStageTrack`
- [x] T011 `css/app.css`：`:root` 色票、記號形狀（`data-shape`／`data-tone`）、頁首與階段軌
- [x] T012 三頁外殼改寫，保留所有 id、`data-feature`、script（`index.html`、`teacher.html`、`student.html`）
- [x] T013 `tests/architecture/test_feature_scripts_loaded.py` 加入 006 對照（`overview.js`、`student-face.js`）

## Phase 3: User Story 1 - 老師一眼掌握本輪狀態 (P1)

- [x] T020 [US1] 測試：`tests/browser/test_pages.py::test_teacher_overview_shows_stage_winners_and_solved_count`（US1-AS1～AS5）
- [x] T021 [US1] 測試：`tests/unit/frontend/test_glyph.py::test_stage_track_marks_done_and_current_step`（US1-AS5）
- [x] T022 [US1] `js/overview.js`：`questionStates`、題目方塊、成功題數、各組長條、倒數、換活動清除
- [x] T023 [US1] 總覽套用 004 的結果版本守衛 `acceptRankingRounds`（FR-006；補寫 spec 時發現，已同步三張圖）

## Phase 4: User Story 2 - 用幾何記號辨識組別 (P1)

- [x] T030 [US2] 測試：`tests/unit/frontend/test_glyph.py`（形狀與色調循環、裝飾屬性）
- [x] T031 [US2] 測試：`tests/browser/test_pages.py::test_group_glyphs_accompany_group_numbers_on_both_pages`
- [x] T032 [US2] 既有模組加記號：`teacher.js`、`submission.js`、`ranking-review-teacher.js`、`ranking-review.js`
- [x] T033 [US2] `tests/unit/frontend/test_student_ranking_render.py` 假 DOM 補 `dataset`、`setAttribute` 並複製 `glyph.js`（真實模組現在載入它）

## Phase 5: User Story 3 - 學生看得懂剩餘時間 (P2)

- [x] T040 [US3] 測試：`tests/browser/test_pages.py::test_student_countdown_ring_follows_deadline_only_while_round_is_open`
- [x] T041 [US3] `js/student-face.js`：本組記號、圓環倒數、階段軌、換活動清除

## Phase 6: User Story 4 - 一致的視覺基準與可讀性 (P2)

- [x] T050 [US4] 測試：`tests/architecture/test_ui_tokens.py`（色碼只在 `:root`、頁面無 inline 色彩、11 組對比 ≥ 4.5:1、負對照）
- [x] T051 [US4] 測試：`tests/browser/test_pages.py::test_pages_fit_phone_width_without_horizontal_scroll`
- [x] T052 [US4] `app.css` 把 `:root` 外的色碼改為變數（`--on-color`、`--danger-bg`）

## Phase 7: Polish & 驗證

- [x] T060 用真實流程截圖打磨三輪（1440、375；`polish-log.md`），JS 錯誤 0
- [x] T061 改版前後截圖：`screenshots/before`（005 原始版本 `f0f45da`）、`screenshots/after`
- [x] T062 三張 PlantUML 圖：`diagrams/006-ui-refresh-{component,class,sequence}.puml` 並轉 PNG
- [x] T063 程式碼 ↔ 圖一致性檢查（見 quickstart.md「圖表一致性」）
- [x] T064 `tests/SCENARIO_MAP.md` 加入 006 段
- [x] T065 自動化驗證：pytest、ruff check、ruff format --check、mypy（結果記在 quickstart.md）
- [ ] T066 非實作者人工驗證（quickstart.md「人工驗證」，1440 與手機各一次）
- [ ] T067 投影機實測後排可讀性（SC-005）
- [x] T068 005（PR #25）合併 main 後，依 Issue #28 的分支策略 rebase 到 main 並把 PR #33 的 base 改成 `main`（2026-11-25 完成，rebase 後重跑驗證見 quickstart.md）
