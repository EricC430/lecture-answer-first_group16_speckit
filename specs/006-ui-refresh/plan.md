# Implementation Plan: 介面改版——幾何記號（UI Refresh，huashu-design dir-3）

**Branch**: `feature/28-006-ui-huashu` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/006-ui-refresh-component.puml`](../../diagrams/006-ui-refresh-component.puml)
- 類別圖：[`diagrams/006-ui-refresh-class.puml`](../../diagrams/006-ui-refresh-class.puml)
- 時序圖：[`diagrams/006-ui-refresh-sequence.puml`](../../diagrams/006-ui-refresh-sequence.puml)

模組與函式名稱與圖一致。補寫 spec 時加入結果版本守衛（FR-006），三張圖已在同一個 commit 更新並重新轉出 PNG。

**前置條件**：001～005 與 #30 已在 main，本分支已 rebase 到 main。006 不修改後端。

## Summary

只改前端呈現。視覺方向由 huashu-design 的三方向流程產生（設計需求 `design-spec.md`、六張方向卡 `directions.md`、三個初稿 `design-demos/`），選定 dir-3「幾何記號」：白底、墨黑，加朱紅、黃、藍三色，每組一個幾何形狀。

技術做法：

- **新增三個前端模組**（只讀快照、不呼叫 API）：
  - `js/glyph.js`：`glyphKind`（組號 → 形狀與色調）、`glyph`（建立裝飾元素）、`renderStageTrack`（階段軌）。
  - `js/overview.js`：老師頁 `#overview-section`，以 `onTeacherSnapshot` 註冊；`questionStates(snapshot)` 依 001 的 `stage`／`openQuestions`、003 的 `submissions.current`、004 的 `ranking.rounds` 推得每題狀態；套用 004 的 `acceptRankingRounds` 守衛。
  - `js/student-face.js`：學生頁本組記號、倒數圓環、階段軌，以 `onStudentSnapshot` 註冊。
- **既有模組只加組別記號元素**：`teacher.js`（組別表第一欄）、`submission.js`（作答看板表頭）、`ranking-review-teacher.js`、`ranking-review.js`（順位列）。邏輯、文字、API 呼叫都不變。
- **HTML 外殼與 CSS**：三頁改寫外殼，保留所有 id、`data-feature`、script；老師頁分左欄（總覽、活動）與右欄（匯入、作答、順位、寫回；開放加入後匯入區塊以 CSS `order` 移到最後）。`app.css` 整份改寫，色票集中在 `:root`。

## Technical Context

**Language/Version**：原生 JavaScript（ES modules）、CSS；後端 Python 3.11 不變

**Primary Dependencies**：無新增。字型使用 Windows 內建（微軟正黑體、Bahnschrift、Consolas），不使用 CDN

**Storage**：無。題目狀態只在前端由快照推得，不保存

**Testing**：pytest；`tests/unit/frontend/`（node 執行真正的模組＋假 DOM）、`tests/architecture/`（靜態檢查）、`tests/browser/`（真實 uvicorn＋CDP 無頭瀏覽器，Google 用假替身）

**Target Platform**：Windows 本機瀏覽器（Edge／Chrome）；投影 1440 寬、手機 375 寬

**Performance Goals**：沿用 001 的 2 秒同步要求；總覽在每次快照時重畫，題數 50 題以內

**Constraints**：不改後端、不改 001～005 的行為與 DOM id；文字一律 `textContent`；色碼只在 `:root`；對比 ≥ 4.5:1

## Constitution Check

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致（NON-NEGOTIABLE） | 不實作也不改變任何 OpenSpec 行為；spec 的 Traceability 逐條列出畫面會呈現的 OpenSpec 規定並確認不變；總覽只重排老師已可見的資料，學生可見資料不變；屬「畫面排版」，依 PROJECT_WORKFLOW 第 10 節不記入 alignment.md | ✅ |
| II 圖表生成（NON-NEGOTIABLE） | 三張圖已產出並轉 PNG；實作偏離時先改圖（FR-006 守衛已同步到三張圖）；tasks 列有程式碼 ↔ 圖一致性檢查 | ✅ |
| III Guided Notes 動態定位 | 不涉及匯入與寫回；總覽的格數只讀 002 提供的 `questionShapes`，不寫死題數或位置 | ✅（不適用部分已說明） |
| IV 後端為唯一事實來源 | 階段、輪次、勝出組、定案與否全部取自快照；前端不計算順位；倒數圓環只是 `deadline` 的視覺化，截止仍由後端判定 | ✅ |
| V 資料可見性與安全 | 總覽只在老師頁；學生頁不新增他組資料；新增輸出一律 `textContent`、記號 `aria-hidden`；沒有新的輸入欄位 | ✅ |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 都有測試（tests/SCENARIO_MAP.md 006 段）；真實瀏覽器測試走正式入口（HTTP＋WebSocket＋實際頁面）；不呼叫 Google；非實作者人工驗證列於 quickstart.md | ✅（人工驗證待執行） |
| VII 簡單與本機運作 | 不新增套件、不用框架或建置步驟；不使用外部字型與 CDN | ✅ |
| 技術限制：架構（NON-NEGOTIABLE） | 只動外層（`adapters/static/`）；核心與應用層不變，`test_core_is_pure.py` 照常通過 | ✅ |
| 技術限制：日誌、風格 | 沒有新增 Python 程式；測試檔通過 ruff、ruff format；mypy 照常 | ✅ |

**Post-design 重新檢查**：補寫 spec 時比對 OpenSpec round-submission「關輪公開結果與版本一致」，發現總覽缺少 004 的結果版本守衛，已加入（FR-006）並更新三張圖；沒有其他違反項目。

## Project Structure

### Documentation (this feature)

```text
specs/006-ui-refresh/
├── spec.md · plan.md · tasks.md · quickstart.md（驗證紀錄與人工驗證步驟）
├── design-spec.md · directions.md · direction-approved.md   # huashu-design 三方向流程的 gate 文件
├── design-demos/dir-1～3.html、shot-dir-*.png、first-dir-*.png  # 三方向初稿（示範資料，手寫）
├── polish-log.md                                              # 打磨紀錄
└── screenshots/before/、screenshots/after/                    # 改版前後截圖（真實流程）
```

### Source Code (repository root)

```text
src/lecture_quiz/adapters/static/
├── index.html · teacher.html · student.html   # 外殼改寫（id、data-feature、script 保留）
├── css/app.css                                # 整份改寫，:root 色票
└── js/
    ├── glyph.js · overview.js · student-face.js            # 006 新增
    └── teacher.js · submission.js · ranking-review*.js      # 只加組別記號元素
tests/
├── unit/frontend/test_glyph.py                 # 新增
├── unit/frontend/test_student_ranking_render.py # 假 DOM 補 dataset、複製 glyph.js
├── architecture/test_ui_tokens.py              # 新增
├── architecture/test_feature_scripts_loaded.py # 加入 006 對照
└── browser/test_pages.py                       # 新增 4 個測試
```

## 對既有功能的影響

| 子功能 | 變更 | 行為影響 |
|---|---|---|
| 001 | `teacher.js` 組別表第一欄前面加記號；`teacher.html`／`student.html` 外殼改寫 | 無（文字、按鈕、id 不變） |
| 003 | `submission.js` 作答看板表頭加記號 | 無 |
| 004 | `ranking-review-teacher.js`、`ranking-review.js` 順位列加記號；006 共用 `ranking-common.js` 的版本守衛（`seenVersions` 同一份，冪等） | 無 |
| 005 | 只有 CSS | 無 |

## Complexity Tracking

無違反憲章的項目。
