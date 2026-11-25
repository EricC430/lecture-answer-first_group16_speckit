# 006 驗證紀錄

每列都是實際執行過的指令或操作與其輸出數字（憲章原則 VI）。執行環境：Windows 11、`.venv` Python 3.14.7、無頭 Chrome／Edge（`tests/browser/cdp.py`）。

## 自動化

| 日期 | 任務 | 指令 | 結果 |
|---|---|---|---|
| 2026-11-25 | 基準（改版前） | `.venv\Scripts\python -m pytest -q`（`feature/28-006-ui-refresh` 建立當下，等同 f0f45da） | 1340 passed, 8 deselected, 69.63s |
| 2026-11-25 | T003 | `.venv\Scripts\python scripts/build_font_subset.py --source-dir <scratchpad>/font-src`（來源：google/fonts `ofl/notoseriftc`、`ofl/inter`、`ofl/ibmplexmono`，2026-11-25 下載） | 4 個 woff2，總量 266.5 KB（≤ 600 KB）；實作完成後會重跑以涵蓋新文字 |
| 2026-11-25 | T005～T007（實作前） | `.venv\Scripts\python -m pytest tests/unit/ui -q` | 2 failed, 16 passed, 29 errors：缺 `tokens.css`、`app.css` 有寫死色碼、缺 `projection.css`（如預期先失敗）；正負對照皆正確 |
| 2026-11-25 | T012 | `.venv\Scripts\python -m pytest tests/unit/ui -q` | 47 passed |
| 2026-11-25 | T012 | `.venv\Scripts\python -m pytest -q` | 1387 passed, 8 deselected, 74.66s（= 基準 1340 + 新增 47，無回歸） |
| 2026-11-25 | 修正 | `tests/browser/cdp.py` 寫入時磁碟已滿，檔案被截成 0 位元組；以 `git checkout` 還原 HEAD 版後，依 UI 測試的呼叫方式重寫 `set_viewport`、`emulate_media`、`track_network`、`network_urls`、`screenshot`；事件改依 `sessionId` 交給所屬分頁；截圖前先 `Page.bringToFront`（背景分頁不產生畫格，原本會卡到逾時） | 截圖測試由逾時改為 1 passed（53.6s） |
| 2026-11-25 | T003（重跑） | `.venv\Scripts\python scripts/build_font_subset.py --source-dir <scratchpad>/font-src`（實作新增 66 個字後 `test_font_subset.py` 失敗而重跑） | 4 個 woff2，總量 279.3 KB（≤ 600 KB）；`pytest tests/unit/ui -q` 48 passed |
| 2026-11-25 | 修正 | `tests/integration/test_app_smoke.py` 首頁標記由「老師頁」改為 `href="teacher.html"`（006 首頁改為角色卡片，原字樣已不存在；仍檢查首頁連得到老師頁） | 該測試通過 |
| 2026-11-25 | T091 | `.venv\Scripts\python -m ruff check .`；`ruff format --check .`；`mypy` | All checks passed；420 files already formatted；Success: no issues found in 83 source files（修正前 132 個錯誤，皆在 006 新增的測試與 `scripts/build_font_subset.py`；長字串以隱式串接拆行，拆行前後以 AST 比對確認語意不變） |
| 2026-11-25 | T089 | `.venv\Scripts\python -m pytest -q -rs`（含 001～005、`tests/browser/`、`tests/unit/ui/`） | 1445 passed, 0 failed, 0 skipped, 8 deselected（`perf`、`real_google`），153.15s；基準 1340 → +105 |
| 2026-11-25 | T093 | `pytest` 執行所有引用 `tests/fixtures/guided_notes_layouts.py` 的測試檔（002 匯入、005 寫回、003 判定等 28 個檔案）；另以 `-k "layout_a or layout_b"` 篩選 | 176 passed（2 個 perf 依預設排除）；兩版面參數化測試 7 passed |
| 2026-11-25 | T090 | `.venv\Scripts\python -m pytest -m perf -o log_cli=true -o log_cli_level=INFO`（老師 + 6 組、每組 2 條連線 = 13 條） | 6 passed，34.56s。最大延遲：開輪 6.2 ms、關輪 5.0 ms、定案 89.0 ms、結束 5.4 ms；提交→老師看板 6.3 ms；判錯 55.1 ms、撤銷判錯 48.3 ms、結果定案 35.2 ms；寫回狀態推送 10.2 ms（皆 < 2000 ms）。20 組 41 條連線（只記錄）：判錯最大 550.6 ms |
| 2026-11-25 | T090（T059） | `pytest -s tests/browser/test_ui_projection.py::test_projection_shows_replacement_within_2s` | 1 passed；10 次遞補延遲最大 0.009 s（全部 0.004～0.009 s，≤ 2 s） |
| 2026-11-25 | T092 | `scripts/build_font_subset.py` 搜尋 `print(`；`static/js/` 搜尋 `console.`；檢查 `teacher-layout.js` 開啟投影的網址；`git status --porcelain --untracked-files=all` 搜尋 TTF／OTF／`.env`／憑證；`git check-ignore -v .env` | 0 個 `print`、0 個 `console`；投影網址只有 `projection.html?code=…`，token 取自同一瀏覽器的 localStorage；沒有待追蹤的字型來源或機敏檔；`.env` 被 `.gitignore:11` 排除 |

## 圖表與程式碼一致性（T088，2026-11-25）

逐一比對 `diagrams/006-ui-refresh-{component,class,sequence}.puml` 與實作：

- 一致：首頁、老師頁兩欄與四個分頁（`TABS`、`TAB_FOR_STAGE`）、「有更新」標記（文字 + 圖示）、方向鍵切換、階段進度六階段、題號導覽列（`scrollIntoView` + 移動焦點）、送出狀態（`data-submit-state` idle／busy／done／error，送出中停用按鈕）、倒數剩 10 秒內 `data-urgent`、新資料提示 1500 ms（≤ 2 秒）、`prefers-reduced-motion` 把動畫時間設為 0、空狀態插圖、按鈕四種（預設 `button` 即幽靈外框，另有 `.btn-primary`／`.btn-secondary`／`.btn-danger`；`:disabled`、`[aria-busy="true"]`）、投影結果卡片（「答錯」標示、「第 N 組遞補（第 M 組答錯）」）、投影不含理由與成功次數。
- 不一致並已修正圖表：時序圖原本寫「後端推送新結果（公開範圍）」，實作是投影畫面沿用老師的同步通道收到**完整老師快照**，再由 `projection-view.js` 的 `toProjectionView` 白名單只留公開欄位（研究 R5）。時序圖與組件圖已改為這個說法，以 `java -jar plantuml.jar -charset UTF-8 "./diagrams/006-*.puml"` 重新轉出 3 張 PNG，並打開組件圖與時序圖確認新文字有顯示、沒有破圖（組件圖部分連線標籤壓到線，但仍可辨識）。

## 截圖檢查（T086，2026-11-25，部分）

`UI_SCREENSHOTS_DIR=specs/006-ui-refresh/screenshots pytest tests/browser/test_ui_screens.py` → 1 passed，產生 44 張（測試同時斷言每張都沒有整頁水平捲動）。

Claude 實際打開的 12 張：`index-375`、`index-1440`、`teacher-joining-375`、`teacher-round-1440`、`teacher-results-1024`、`teacher-ended-768`、`student-round-375`、`student-results-375`、`student-joining-768`、`projection-results-1280x720`、`projection-round-1920x1080`、`projection-ended-1280x720`。觀察：

- 沒有發現文字互相重疊或被截斷；狀態標籤都有圖示加文字；投影畫面搶答中只顯示代碼、輪次、模式、題號、倒數。
- `student-round-375`：右下角固定的同步狀態（001 的 `#sync-status`，`pointer-events: none`）在該捲動位置蓋住題號導覽「第 4 題・未送出」的一部分；導覽列是 sticky 置頂，捲動後就不再被遮住。未修改，待組員決定。
- `index-375`：標題斷行為「Vibe Coding 課堂搶／答」，最後一字單獨一行；兩張角色卡寬度不一致（依文字寬度）。屬外觀細節，未修改。
- 同步狀態的「延遲」常顯示數秒（例如 5614 ms）：這是 001 既有指標，截圖測試中快照產生後到截圖之間的時間差，不是 006 造成的推送延遲（T090 推送最大 89 ms）。

**仍待人實際打開其餘 32 張並完成 quickstart B 第 3 步（改版前後資訊項目差異數 = 0，SC-002）**，所以 T086 維持未完成。

## 真實 Google 路徑（T096）

006 只改 HTML、CSS 與前端呈現模組，沒有新增或修改任何 Google 匯入、授權或寫回路徑（後端未修改，`git diff` 中 `src/lecture_quiz/` 只有 `adapters/static/`）。真實 Google 路徑驗證不適用；002（T028、T071）與 005（T094）的真實路徑驗證仍以各自的紀錄為準。

## 本次 UI refresh 增量確認（2026-11-25）

| 日期 | 任務 | 指令 | 結果 |
|---|---|---|---|
| 2026-11-25 | speckit-implement 前置檢查 | `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` | FEATURE_DIR 正確指向 `specs/006-ui-refresh`；requirements checklist 19/19 checked |
| 2026-11-25 | 本次 UI 靜態檢查 | `node -e ...`（檢查首頁主圖存在、HTML 引用正確、CSS 大括號平衡）；`git diff --check` | `static-ui-check-ok`；diff check 通過 |
| 2026-11-25 | 本次截圖 | Edge headless `--window-size=1440,1000` 首頁與老師頁；`--window-size=375,900` 學生頁 | 產生並實際打開 `screenshots/home-current.png`、`teacher-current.png`、`student-current.png`；首頁主圖載入，窄版學生表單確認 |

這三張是本次修改後的增量截圖，不取代 T086 要求的完整尺寸與各活動階段矩陣。虛擬環境目前指向不存在的 Python 3.14，因此本回合未宣稱 pytest／ruff／mypy 通過。

## taste-skill redesign confirmation（2026-11-25）

- kind: software，主要產品為課堂搶答學習單；主要動作為「建立活動」。
- copy lint: `node C:\Users\chent\.codex\plugins\cache\taste-skill\taste-skill\2.5.1\skills\taste-skill\scripts\copy-lint.mjs src/lecture_quiz/adapters/static/index.html --kind software` → 0 FAIL、0 WARN。
- taste gate: 已以 `gate.mjs --start` 啟動檢查，結果為 `GATE: ERROR`。`consistency.mjs` 無法走訪 1440／390，`check.mjs` 以 exit 2 timeout。依技能規則未重跑 gate。
- Edge 實際截圖：`screenshots/home-taste-current.png`，使用 `--virtual-time-budget=3000 --window-size=1440,1000`，圖片載入、文字與兩個入口可見。
- 本次變更：補上 software metadata、改為直接描述產品的標題與說明、移除圖片 caption、移除主圖傾斜、加入一次性的 `data-enter` entrance。

## taste-skill 全頁重做（2026-11-25）

- `teacher.html`、`student.html`、`projection.html` 全部補上 `data-type="software"`、`page-type`、`site-kind` metadata。
- 老師頁改為控制台 rail + 工作區，學生頁改為加入／作答優先的單一流程，投影頁改為深色播送畫面。
- 四頁以 Edge headless 實際截圖：`index-taste-current.png`、`teacher-taste-current.png`、`student-taste-current.png`、`projection-taste-current.png`。學生窄版另加 `calc(100vw - 32px)` 容器限制並重新截圖。
- `copy-lint` 仍為 0 FAIL、0 WARN。`git diff --check` 通過。
- gate 仍維持前次 `GATE: ERROR`，未重跑，因技能規則要求 timeout 後停止重跑。
