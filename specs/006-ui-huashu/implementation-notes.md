# 006 dir-3 實作說明（2026-11-25）

## 改了什麼
- `static/css/app.css`：整份改成 dir-3 的視覺（白底、墨黑，加朱紅、黃、藍；Bahnschrift 數字、微軟正黑體內文；組別幾何記號）。
- `static/{index,teacher,student}.html`：版面外殼改寫。所有既有的 id、`data-feature`、`hidden`、script 都保留；老師頁分成左欄（總覽＋活動）與右欄（匯入、作答看板、順位、寫回）。
- 新增 `js/glyph.js`：組號 → 幾何記號（6 種形狀 × 2 組顏色循環），以及頁首階段軌。
- 新增 `js/overview.js`（老師頁，`#overview-section`，`data-feature="006-ui-refresh"`）：只讀快照，畫出輪次、階段（搶答中顯示倒數）、已定案成功題數、每題狀態方塊（已成功／待定案／作答中／未成功／未出題）與各組成功次數長條。
- 新增 `js/student-face.js`（學生頁）：本組記號、圓環倒數、階段軌。圓環的分母是「第一次看到截止時間時的剩餘秒數」，確切秒數與截止判定不變（仍以 001 的倒數文字與後端為準）。
- 既有模組只加入記號元素（不改邏輯）：`teacher.js`（組別表）、`submission.js`（作答看板表頭）、`ranking-review-teacher.js`、`ranking-review.js`（順位列）。

## 測試
- `tests/architecture/test_feature_scripts_loaded.py`：加入 006 的對照（`overview.js`、`student-face.js`）。
- `tests/unit/frontend/test_student_ranking_render.py`：假 DOM 補上 `dataset`、`setAttribute`，並複製 `glyph.js`（真實的 `ranking-review.js` 現在會載入它）。
- 新增 `tests/browser/test_pages.py::test_teacher_overview_shows_stage_winners_and_solved_count`。
- 2026-11-25 執行：`.venv\Scripts\python -m pytest -q` → 1344 passed, 8 deselected；`ruff check .` 通過；`ruff format --check .` 通過；`mypy` 通過。

## 尚未做（依專案流程需要補）
- 006 的 spec／plan／tasks 與 PlantUML 圖表尚未建立；`overview.js` 是新的畫面元素，依憲章原則 II 與 PROJECT_WORKFLOW 應補文件與圖並檢查一致性。
- 與 OpenSpec 組的對齊：本次只改展示，沒有改變使用者可見的功能行為；「本輪總覽」是否算新的可見行為，需要組內判斷是否記入 `docs/alignment.md`。
- 非實作者的人工驗證（投影機實測後排可讀性）。
