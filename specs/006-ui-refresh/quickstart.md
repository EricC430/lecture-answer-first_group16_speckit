# Quickstart 與驗證紀錄：006 介面改版（huashu-design dir-3）

## 啟動

```powershell
.venv\Scripts\python -m lecture_quiz   # 只監聽 127.0.0.1:8000
```

開啟 `http://127.0.0.1:8000/`（首頁）、`/teacher.html`、`/student.html`。不要直接用 `uvicorn` 啟動（見 CLAUDE.md）。

## 自動化驗證（2026-11-25，實作者執行）

| 指令 | 結果 |
|---|---|
| `.venv\Scripts\python -m pytest -q` | 1371 passed, 8 deselected（`real_google`、`perf` 預設排除） |
| `.venv\Scripts\ruff check .` | All checks passed |
| `.venv\Scripts\ruff format --check .` | 404 files already formatted |
| `.venv\Scripts\mypy` | Success: no issues found in 83 source files |

以上是 rebase 到 main（含 #25、#30）之後重跑的結果；rebase 前在 005 分支上是 1366 passed。

改版前基準（同日、改動前在 `f0f45da` 上執行）：`pytest -q` 1340 passed。

006 新增或修改的測試（對應見 `tests/SCENARIO_MAP.md` 的 006 段）：

- `tests/browser/test_pages.py`：`test_teacher_overview_shows_stage_winners_and_solved_count`、`test_group_glyphs_accompany_group_numbers_on_both_pages`、`test_student_countdown_ring_follows_deadline_only_while_round_is_open`、`test_pages_fit_phone_width_without_horizontal_scroll`（真實 uvicorn＋無頭 Edge／Chrome，Google 用假替身）
- `tests/unit/frontend/test_glyph.py`（node 執行真正的 `glyph.js`）
- `tests/architecture/test_ui_tokens.py`（色碼只在 `:root`、頁面無 inline 色彩、對比度，含負對照）
- 修改：`tests/architecture/test_feature_scripts_loaded.py`（加入 006 對照）、`tests/unit/frontend/test_student_ranking_render.py`（假 DOM 補 `dataset`，複製 `glyph.js`）

## 對比度（WCAG AA，由 `test_ui_tokens.py` 從 `app.css` 的 `:root` 計算）

| 文字 on 背景 | 對比 | 使用位置 |
|---|---|---|
| `--ink` on `--bg` | 18.42:1 | 內文 |
| `--grey` on `--bg` | 6.48:1 | 次要文字、標籤、階段軌 |
| `--grey` on `--wash` | 5.73:1 | 未出題方塊 |
| `--red-ink` on `--bg` | 6.04:1 | 搶答成功、判錯按鈕、未成功方塊 |
| `--red-ink` on `--danger-bg` | 5.14:1 | 錯誤訊息 |
| `--on-color` on `--red` | 4.58:1 | 主要按鈕、結果未定案色塊 |
| `--on-color` on `--red-ink` | 6.04:1 | 主要按鈕 hover |
| `--on-color` on `--blue` | 6.75:1 | 成功題數色塊 |
| `--on-color` on `--ink` | 18.42:1 | 輪次色塊、作答中方塊、狀態列 |
| `--ink` on `--yellow` | 9.81:1 | 搶答中色塊、待定案方塊、同步中斷橫幅 |
| `--ink` on `--wash` | 16.29:1 | 總覽方塊、圓環倒數 |

最低是白字在朱紅上 4.58:1，剛好過 4.5。之後調整 `--red` 時要重跑測試。

## 截圖（真實流程，2026-11-25）

用 `tests/browser` 的 LiveServer 與 CDP 無頭瀏覽器跑同一段流程：建立活動、匯入版面 A、6 組加入；第 1 輪題 1、題 3 作答→關輪→定案；第 2 輪題 2、題 4（300 秒倒數）作答→關輪→判錯。改版前在 `f0f45da`（005）執行，改版後在本分支執行，每張圖的頁面 JS 錯誤皆為 0。

| 畫面 | 改版前 | 改版後 |
|---|---|---|
| 首頁 1440／375 | `screenshots/before/home-1440.png`、`home-375.png` | `screenshots/after/home-1440.png`、`home-375.png` |
| 老師：建立活動 | `before/teacher-create.png` | `after/teacher-create.png` |
| 老師：搶答中 1440 | `before/teacher-open-1440.png` | `after/teacher-open-1440.png` |
| 老師：結果未定案 1440／375 | `before/teacher-pending-1440.png`、`teacher-pending-375-top.png` | `after/` 同名 |
| 學生：加入／搶答中／結果 375 | `before/student-join-375.png`、`student-open-375.png`、`student-pending-375.png` | `after/` 同名 |

打磨過程（三輪，每輪最傷的三處與修正）見 `polish-log.md`。

## 圖表一致性（2026-11-25）

逐一比對 `glyph.js`、`overview.js`、`student-face.js` 的 import／export 與三張圖：

- 組件圖：overview.js → teacher.js、submission.js（`el()`）、glyph.js、countdown.js、ranking-common.js；student-face.js → student.js、glyph.js；teacher.js、submission.js、ranking-review*.js → glyph.js。與程式一致。
- 類別圖：`glyph.js` 匯出 `glyphKind`、`glyph`、`STAGE_ORDER`、`renderStageTrack`（`SHAPES`、`TONES` 未匯出，圖上為私有）；`overview.js` 匯出 `questionStates`。與程式一致。
- 時序圖：總覽先畫階段軌、輪次、階段、長條，再經結果版本守衛才更新題目方塊；學生頁圓環只在搶答中且有 deadline 時計時。與程式一致。
- 比對時修正了兩處圖上的不一致（`SHAPES`／`TONES` 可見性、組件圖缺 `el()` 相依），已重新轉出 PNG。

## 人工驗證（非實作者執行，jacky0407）

依 PROJECT_WORKFLOW 第 9 節，合併前由非實作者操作一次。請在 1440 寬瀏覽器與手機（或瀏覽器手機模式 375 寬）各做一次，並填下表。

1. 開首頁，確認兩個入口可進入老師頁與學生頁。
2. 老師頁建立活動、匯入學習單、開放加入；頁首階段軌標在對應階段（US1-AS5）。
3. 兩台裝置（或同一台電腦上兩個不同的瀏覽器；**由 007 修訂（2026-11-26）**：同一瀏覽器的分頁共用學生身分）以不同組號加入；老師頁組別表、學生頁本組都有形狀記號，旁邊寫「第 N 組」（US2）。
4. 開一輪（設倒數），學生頁出現圓環與秒數；兩組各送出一題；老師總覽題目方塊顯示「作答中・N 組送出」（US1-AS1、US3-AS1）。
5. 關輪：總覽顯示「結果未定案」、勝出組「待定案」，成功題數不變；判錯一組，順位與總覽一起更新（US1-AS2）。
6. 確認定案：方塊變成「第 N 組・第 1 輪」，成功題數加一（US1-AS3）。
7. 開一輪不設倒數：學生頁沒有圓環，顯示「本輪沒有倒數，由老師結束」（US3-AS2）。
8. 結束活動、寫回預覽與 CSV 下載照常（001～005 行為不變，US4-AS4）。
9. 投影到教室螢幕，從後排確認讀得出輪次、階段、各題勝出組別（SC-005）。

| 日期 | 驗證者 | 環境（瀏覽器、寬度、投影） | 步驟 | 結果 | 備註 |
|---|---|---|---|---|---|
| 2026-11-27 | jacky0407 | `main` 02b47b4；1440 寬、手機寬度與投影 | 1～9 | 通過（使用者回報） | 同時確認採用 dir-3（T005）；細節不逐步記錄，以錄影為證 |
