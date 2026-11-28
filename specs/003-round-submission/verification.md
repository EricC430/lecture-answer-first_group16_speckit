# 驗證紀錄：003-round-submission

依憲章原則 VI：記錄日期、實際執行的指令與結果數字。人工驗證與真實路徑驗證在本檔後段（尚未進行）。實作中發現的問題集中在文末「實作問題紀錄」。

## 基準（T002，實作前）

- 日期：2026-11-23；環境：Windows 11、Python 3.11.5；分支 `feature/7-003-round-submission`（已合併 main `a22f047`，含 001）。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 125 files already formatted |
| `mypy` | Success: no issues found in 26 source files |
| `pytest` | 389 passed, 1 deselected |

## Foundational（T005～T019）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T005～T009 共 5 個測試檔先寫，執行 `pytest`（只跑這 5 個檔）結果為 5 errors during collection（`RecordSubmission`、`HandlerStep`、`round_submission` 模組尚不存在）。
- **例外**：T018 的 dev seed `blanks` 測試是在實作之後補寫（順序與 TDD 不符），補寫後執行通過；已在此記錄。
- 實作中發現一個**測試本身的錯誤**：`test_accept_marks_then_commits_inside_lock_and_publishes_once` 的 setup 只清了 `published`、沒清 `locked_during_publish`，導致比對到建立活動時的推送紀錄；修正測試的 setup，程式碼未改。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `ruff format --check .` | 141 files already formatted |
| `mypy` | Success: no issues found in 34 source files |
| `pytest` | **421 passed**, 1 deselected（001 既有 389 個 + 新增 32 個） |
| `pytest tests/architecture` | 28 passed（`core/round_submission/` 已納入純函式檢查） |

- **001 既有測試**：全部通過，沒有修改任何既有斷言（T014）。既有測試檔中只有 `tests/conftest.py`（新增 003 共用工具，`make_app` 預設注入 `FakeQuestionShapeSource`）與 `tests/integration/test_dev_seed.py`（在檔尾新增 2 個測試）有變更。

## US1（T020～T028）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T020～T023 先寫；執行 `pytest tests/unit/core/round_submission/test_decide_us1.py tests/unit/app/round_submission tests/contract/test_http_submissions.py` 結果 24 failed、3 passed（通過的 3 個是 Foundational 已完成的 `test_store.py`）；`test_answer_rules.py` 收集失敗（模組不存在）。`questionShapes` 的整合測試也先寫並確認失敗（1 failed）。
- **設計調整**：`SubmissionRejection`、`DecisionKind`、`SubmissionDecision` 定義在 `core/round_submission/models.py`（`rules.py` 重新匯出），避免 `rules.py` 與 `answer_rules.py` 循環匯入；plan 的結構說明已同步。
- **前端**：`js/submission.js`、`js/round-submission.js` 以 `node --check` 通過；尚未在瀏覽器手動操作（留待 quickstart 人工驗證）。

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed! |
| `mypy` | Success: no issues found in 35 source files |
| `pytest` | **465 passed**, 1 deselected（新增 44 個；001 既有測試未修改） |

## US2（T029～T034）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T029～T031 先寫；執行這 3 個檔結果 10 failed、5 passed。通過的 5 個不依賴 US2 程式：題號檢查優先、先無效再有效、下一輪重新作答、他組不受影響、刪組規則（001 既有行為）。
- **範圍調整**：T031 的「同組另一台 WebSocket 收到答案」（US2-AS1 推送部分）與「離組後提交仍屬原組」（US2-AS6）需要快照中的提交資料，分別移到 US4 的 T043 與 US5 的 T048；tasks.md 已註記。
- **競爭測試**：同組兩台裝置以 `asyncio.gather` 同時送同題，重複 50 次，每次都只保存 1 筆、只推送 1 次，另一方回本組已送出且附同一筆提交。
- **前端**：`js/round-submission.js` 依快照 `submissions.current.own` 把本組已送出的題目改為唯讀（US4 提供資料後生效）；`node --check` 通過，尚未在瀏覽器手動操作。

| 指令 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | All checks passed!；152 files already formatted |
| `mypy` | Success: no issues found in 35 source files |
| `pytest` | **480 passed**, 1 deselected（新增 15 個；001 既有測試未修改） |

## US3（T035～T041）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T035～T038 先寫；執行這 4 個檔結果 13 failed、16 passed。通過的 16 個包含 US1 的契約測試，以及截止邊界兩個測試：截止當下、截止後 1 毫秒拒絕；截止前 1 毫秒接受。截止邊界早就通過，因為 001 的 `RecordSubmission` 已在鎖內檢查 `now < deadline`，加上步驟 2 後改由 003 判定先擋下。
- **讀取介面**：`round_submissions`、`all_submissions`（給 004、005）在 T040 完成，補測試時先確認失敗（1 failed）。
- **關輪與提交競爭**：隨機先後重複 50 次，兩種結果都有出現；接受時關輪推送當下已包含該提交，被拒時未保存。
- **訊息**：沒有任何輪次時與已截止共用「本輪已結束（或尚未開始），不能再送出。」（tasks.md T035 已註記）。
- **前端**：`STALE_ROUND` 顯示訊息與「重新整理」按鈕；`ROUND_CLOSED` 停用其餘未送出的表單。`node --check` 通過，尚未在瀏覽器手動操作。

| 指令 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | All checks passed!；155 files already formatted |
| `mypy` | Success: no issues found in 35 source files |
| `pytest` | **498 passed**, 1 deselected（新增 18 個；001 既有測試未修改） |

## US4（T042～T046）

- 日期：2026-11-23；環境同上。
- **先寫測試並確認失敗**：T042、T043 先寫。`test_view_open_round.py` 收集失敗（`view.py` 不存在）；`test_submission_visibility.py` 1 failed、3 passed。通過的 3 個：學生收不到他組任何資料、沒有查詢提交的端點（兩個）。它們在加入 003 欄位前就成立，代表 001 本來就沒外流。實作後再跑一次，確認加入提交資料後仍然成立。
- 實作後 `test_view_open_round.py` 有 1 個失敗：測試自己的預期時區寫錯（`+00:00`，FakeClock 是 `+08:00`）。修的是測試，程式碼未改（問題紀錄 P-17）。
- **前端**：老師頁新增「作答看板」區塊，程式在 `js/round-submission-teacher.js`（`renderBoard` 在 `submission.js`）；`node --check` 通過，尚未在瀏覽器手動操作。

| 指令 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | All checks passed!；158 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest` | **507 passed**, 1 deselected（新增 9 個；001 既有測試未修改） |

## US5（T047～T051）

- 日期：2026-11-24；環境同上。
- **先寫測試並確認失敗**：T047、T048 先寫；執行這 2 個檔結果 7 failed、1 passed。失敗原因都是 `published` 為空（或 `for_group` 沒有 `student_sees_judged_wrong` 參數）。通過的 1 個是讀取介面已排序且不可修改，T040 已完成。
- **公開規則**（研究 R11）：輪次編號小於目前輪次，或等於目前輪次且不在搶答中，就列入 `published`；所有角色都看得到全部組、送出先後與 `noSubmission`。`judgedWrong` 一律為 `false`，等 004 提供真值。
- **US2-AS6**（由 T031 移入）：第 1 組送出後關輪、定案，該裝置離組並加入第 2 組；公開資料與 `round_submissions` 中該提交仍屬第 1 組。
- **前端**：`submission.js` 新增 `renderPublished`；老師頁與學生頁各新增「已公開的作答」區塊。`node --check` 通過，尚未在瀏覽器手動操作。

| 指令 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | All checks passed!；160 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest` | **515 passed**, 1 deselected（新增 8 個；001 既有測試未修改） |

## US6（T052～T055）

- 日期：2026-11-24；環境同上。
- **先寫測試並確認失敗**：T052 的 4 個整合測試在實作前就全部通過。後端早已原文保存答案、無倒數時不截止、重新連線送完整快照，US6 的工作在前端，這 4 個保留作回歸測試。T053 的 8 個靜態檢查實作前 1 failed、7 passed，失敗的是「倒數歸零停用表單」。
- **靜態檢查調整**（P-07、P-18）：
  - 檢查範圍改成 003 實際的模組檔。
  - 「已送出」允許出現在成功回應分支，以及依後端快照顯示同組已送出的 `markOwnSubmissions`。
  - 第一版把函式範圍從 `{` 算起，漏掉參數預設值 `message = "已送出"`，已改為從函式名稱算起。
- **前端**：學生頁作答區新增截止提示。沒有截止時間顯示「本輪沒有倒數，由老師結束。」；有截止時間時歸零後停用未送出的表單，並顯示「已到截止時間，不能再送出。」。`node --check` 通過（5 個檔案），尚未在瀏覽器手動操作。
- 執行 `ruff check` 時發現 3 個 003 測試檔的匯入分組與其他測試不一致（P-25），已用 `ruff check --fix` 修正。

| 指令 | 結果 |
|---|---|
| `ruff check --no-cache .`、`ruff format --check --no-cache .` | All checks passed!；162 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest` | **527 passed**, 1 deselected（新增 12 個；001 既有測試未修改） |

## Polish（T056～T063）

- 日期：2026-11-24；Windows 11、Python 3.11.5。
- **先寫測試**：
  - T057 日誌測試實作前失敗：被拒的提交記成 `round=-`、`group=-`。
  - T058 兩份版面的 2 個測試實作前就通過，功能在 US1～US5 已完成。
  - T056 效能測試是量測，沒有「先失敗」的階段。
- **效能（T056，老師 + 6 組 × 2 連線，20 筆提交）**：
  - 提交到老師看板、到同組另一台：最大都是 39.7 ms，平均都是 5.6 ms，門檻 2000 ms。兩者在同一次推送送出，量到的時間幾乎相同。
  - 001 的狀態變更同次執行：開輪最大 19.5 ms、關輪 14.3 ms、定案 14.8 ms、結束 17.0 ms。
- **Scenario 對應（T059）**：001 有 57 個、003 有 37 個、OpenSpec round-submission 有 14 個，全部有測試，未對應：無。
  - OpenSpec 實際是 14 個 Scenario，spec、plan、tasks 原寫 13 個，已更正（P-27）。
- **圖表（T060）**：類別圖與組件圖依實作更新並重新轉出 PNG，時序圖不變（P-22）。
- **機敏資料（T063）**：`src/` 沒有 `print(`；追蹤檔案沒有 `.env`、憑證、`.venv`、課程說明、提案草稿。

| 指令 | 結果 |
|---|---|
| `ruff check --no-cache .`、`ruff format --check --no-cache .` | All checks passed!；165 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest` | **530 passed**, 2 deselected（perf 2 個） |
| `pytest -m perf` | **2 passed**（001 狀態同步、003 提交同步） |

與 T002 基準比較：001 原有測試全部保留且通過；003 新增的測試讓總數從 389 增加到 530。

**合併最新 main（含 001 組號釋放修正 #19）後重跑**：`ruff`、`mypy` 通過；`pytest` **535 passed**, 2 deselected（多出的 5 個是 #19 的測試）；Scenario 掃描 001 57 個、003 37 個，未對應：無。

**尚未完成**：
- T064：非實作者 EricC430 依 quickstart 人工驗證。
- T065：002 合併後的真實路徑驗證（P-19）。

## PR #16 審查修正（2026-11-24，EricC430 審查）

- **先寫測試並確認失敗**：新增的 6 個測試在修正前 5 個失敗。
  - `round-submission.js` 語法檢查
  - 送出中不重新啟用已鎖定的按鈕
  - 缺格數提示不重複
  - 核心判定 `SHAPES_UNAVAILABLE`
  - HTTP 503
- **修正**：
  - `round-submission.js` 的重複宣告改名為 `errorCode`（P-30）。
  - 缺格數提示改為每題一則，格數載入後移除（P-31）。
  - 新增 `SHAPES_UNAVAILABLE`，回 503 並記 WARNING（P-32）。
  - 表單送出中結束時，若已截止或已送出就不重新啟用（P-33）。
  - `judgedWrong` 佔位值寫進同步契約（P-34）。
  - 格數來源必須非阻塞，`None` 與缺題的處理寫進研究 R6 與契約（P-35）。
- **新增自動檢查**：`tests/architecture/test_static_text_safety.py::test_javascript_parses` 以 `.mjs` 副本對每支前端模組執行 `node --check`。

| 指令 | 結果 |
|---|---|
| `ruff check --no-cache .`、`ruff format --check --no-cache .` | All checks passed! |
| `mypy` | Success: no issues found in 36 source files |
| `pytest` | **547 passed**, 2 deselected |

## 實作問題紀錄

實作 003 過程中發現的問題、偏離與待辦，依發現順序編號。狀態：**已處理**（已改程式或文件）、**已記錄**（行為不變，只需知道）、**待辦**（之後的任務要處理）、**待決定**（需要組員或 OpenSpec 組決定）。

| # | 階段 | 問題 | 處理 | 狀態 |
|---|---|---|---|---|
| P-01 | Foundational | T018 dev seed 的 `blanks` 測試在實作之後才補寫，不符「先寫測試」 | 補寫後通過；在此記錄 | 已記錄 |
| P-02 | Foundational | `test_record_submission` 的 setup 沒清 `locked_during_publish`，比對到建立活動時的推送 | 修測試，程式碼未改 | 已處理 |
| P-03 | Foundational | 在快照加 `questionShapes` 會打壞 001 檢查快照欄位的測試 | 活動沒有格數資料時不帶任何 003 欄位；`seed_questions` 只在給 `blanks` 時設格數；已寫進同步契約。001 斷言未放寬 | 已處理 |
| P-04 | Foundational | 若放寬 001 的 `Outcome.rejection` 讓它容納 003 的拒絕原因，`http_api.unwrap` 讀 `reason.http_status` 會出錯（analyze I2） | 003 的拒絕改為放在 `value` 的判定結果，`Outcome` 不改 | 已處理 |
| P-05 | US1 | `rules.py` 與 `answer_rules.py` 互相匯入 | 型別移到 `models.py`，`rules.py` 重新匯出；plan 已同步 | 已處理 |
| P-06 | US1 | 日誌直接記學生送來的題號，可能寫進任意內容或超長整數 | 只記 0～9999 的整數題號，其餘記 `-` | 已處理 |
| P-07 | US1 | 學生頁的程式依 DEVELOPMENT.md「一個子功能一個 module」放在 `js/round-submission.js`；tasks 原寫 `student.js` | T053 檢查 `submission.js`、`round-submission.js`、`round-submission-teacher.js`、`student.js`、`teacher.js`；倒數停用寫在 `round-submission.js` | 已處理 |
| P-08 | US1 | 作答表單需要每題格數，原排在 US4 的 `questionShapes` 提前在 US1 做 | T028 已註記 | 已記錄 |
| P-09 | US1～US6 | 前端只做過 `node --check`，沒有在瀏覽器實際操作 | 留到 quickstart 人工驗證（T064，非實作者 EricC430） | 待辦 |
| P-10 | US2 | T031 的「同組另一台收到答案」（US2-AS1 推送）與「離組後提交仍屬原組」（US2-AS6）需要快照提交資料 | 前者已在 US4 的 `test_submission_visibility.py` 完成；後者在 US5 的 `test_us5_published.py` 完成 | 已處理 |
| P-11 | US2 | 快照帶本組提交時把表單改唯讀的前端程式，在 US4 提供資料前沒有作用 | US4 已提供 `submissions.current.own`；瀏覽器操作仍待 P-09 | 已處理 |
| P-12 | US3 | 截止邊界測試在實作前就通過 | 原因是 001 的 `RecordSubmission` 已在鎖內檢查截止時間；現在由 003 判定先擋下，兩層一致 | 已記錄 |
| P-13 | US3 | 「還沒有任何輪次」與「已截止／已關輪」共用一句訊息「本輪已結束（或尚未開始），不能再送出。」；research R10 原寫兩種語意 | 判定結果沒有欄位可區分，要分成兩句需在 `SubmissionDecision` 加欄位 | 待決定 |
| P-14 | US3 | `round_submissions`、`all_submissions`（給 004、005）原排在 T050 | 提前在 T040 完成並測試；T050 只剩 `published` | 已記錄 |
| P-15 | US4 | **關輪後老師看板與學生頁暫時是空的**：`current` 只在搶答中有內容，關輪後的 `published` 要到 US5 才實作 | US5 已實作 `published`，關輪後老師頁與學生頁的「已公開的作答」顯示本輪全部組的提交 | 已處理 |
| P-16 | US4 | T046 原要求學生頁另有 `renderOwnSubmissions` 清單；學生頁的作答表單已在送出後顯示本組答案與時間（P-11），另列一份會重複 | 不另做清單，由表單顯示；`renderBoard` 照做 | 已記錄 |
| P-17 | US4 | 新測試的預期時區寫成 `+00:00`，FakeClock 是 `+08:00` | 修測試，程式碼未改 | 已處理 |
| P-18 | US4 | T053 規定「`已送出` 只出現在成功處理函式內」；`round-submission.js` 依快照顯示「本組已送出」時也用到這個字，且不在 HTTP 成功分支 | T053 允許「已送出」出現在成功分支與依快照顯示的 `markOwnSubmissions`，其餘位置都會讓測試失敗 | 已處理 |
| P-19 | 跨子功能 | 每題格數由 002 實作 `QuestionShapeSource`（與 EricC430 口頭約定）；002 合併前只能用 dev seed | T065 真實路徑驗證要等 002 合併 | 待辦（002） |
| P-20 | 跨子功能 | 「搶答失敗」要等 004 提供勝者；全部判錯顯示「未成功」也由 004 決定 | 已寫在 tasks Notes 的 004 交接 | 待辦（004） |
| P-21 | 環境 | 在本機執行 `pytest -p no:logging` 會讓用到 `caplog` 的 12 個測試報錯（不是程式問題） | 驗證一律用不加參數的 `pytest` | 已記錄 |
| P-22 | US1～US4 | 類別圖與程式的小差異：可見性常數在程式是 `view.py` 的模組常數，圖畫成 `SubmissionView` 的屬性；`SubmissionRules.describe` 不在圖上；`SubmissionView.for_group` 多了 `student_sees_own_success`、`student_sees_judged_wrong` 兩個參數（方便測試 Q-22、Q-26 改為假） | T060 已更新類別圖（模組常數、`describe`、`http_status`、`InvalidAnswerError`、`for_group` 參數、兩個格數來源）與組件圖，重新轉出 PNG | 已處理 |
| P-23 | US5 | 每次推送快照都帶全部已公開輪次，資料量隨輪次增加 | T056 量測單一輪 20 筆提交，最大 39.7 ms；多輪累積的資料量沒有另外量測，一堂課的輪次與組數有限，先不改 | 已記錄 |
| P-25 | US1～US3 | `test_store.py`、`round_submission/helpers.py`、`test_models.py` 的匯入分組不符 ruff 規則（`tests` 應與 `lecture_quiz` 同組）；之前的 `ruff check` 都回報通過，推測是 ruff 快取，切換分支改寫檔案後才被檢查出來 | 已用 `ruff check --fix` 修正；之後的驗證一律加 `--no-cache` | 已處理 |
| P-26 | US6 | 前端倒數停用表單依瀏覽器時鐘，與後端時鐘有誤差時可能早停或晚停 | 截止判定以後端為準（T036）：晚停時送出會被拒並顯示「本輪已結束」；早停的情況在 quickstart 人工驗證觀察 | 已記錄 |
| P-27 | Polish | spec SC-001、plan、tasks T059 寫「13 個 OpenSpec Scenario」，實際是 14 個 | T059 掃描時更正三處；SCENARIO_MAP 列出全部 14 個 | 已處理 |
| P-28 | Polish | 被拒的提交日誌記 `round=-`、`group=-`，查問題時看不出是哪一組（T057 要求要有） | 改為從 001 鎖內的 `SubmissionWindow` 取得；活動不存在或不屬於任何組時仍為 `-` | 已處理 |
| P-29 | 跨 PR | PR #19（001 修正）與本 PR 都改了 `tests/SCENARIO_MAP.md`；PR #17（002）刪除 dev seed，與本 PR 有 6 個檔案衝突 | #19 已合併，本分支已併入最新 main（無衝突，535 passed）；#17 的衝突待其修改後處理，dev seed 去留與格數來源已在 #17 審查提出 | 待辦（#17）|
| P-30 | US3～US6 | **學生頁模組載入即 SyntaxError**：`submitAnswer` 內重複宣告 `const code`（US3 加入），整支 `round-submission.js` 不執行，作答表單與已公開作答都不出現。先前各階段寫的「`node --check` 通過」**不正確**：Node 24 對含 `import` 的 `.js` 執行 `node --check` 會回傳 0（模組自動偵測），沒有真的檢查出錯誤 | 改名為 `errorCode`；新增自動測試以 `.mjs` 副本檢查每支前端模組。前端仍須以瀏覽器人工驗證（P-09） | 已處理 |
| P-31 | US1 | 缺格數時「格數尚未載入」提示在每次推送都多加一則，格數載入後也不清除 | 每題一則（`notices`），格數載入後移除 | 已處理 |
| P-32 | US1 | 沒有格數資料時所有提交回 `QUESTION_NOT_OPEN`「不在本輪開放範圍」，會誤導學生；研究 R6 寫的 WARNING 日誌沒有實作 | 新增 `SHAPES_UNAVAILABLE`（503）與 WARNING；data-model、契約、類別圖同步 | 已處理 |
| P-33 | US6 | 送出途中倒數歸零，`setBusy(false)` 會把已停用的按鈕重新啟用 | 表單記住 `locked`，已停用或已送出時不重新啟用 | 已處理 |
| P-34 | US5 | `judgedWrong` 在 004 接上前一律為 `false`，契約沒有寫明是佔位值 | 寫進 `contracts/sync-websocket.md`；004 接上後提供真值 | 已處理 |
| P-35 | Foundational | `blanks_per_question` 在 001 活動鎖內呼叫，實作若有 I/O 或其他鎖可能阻塞或死結；`None` 與空對應表沒有區分 | 研究 R6 與 service-interfaces 寫明必須非阻塞；兩者都回 `SHAPES_UNAVAILABLE` | 已處理 |

## 人工驗證與真實路徑（T064、T065）

**通過**：2026-11-27 在 `main`（02b47b4）完整測試並錄影，jacky0407 於 2026-11-28 回報全部通過；細節依使用者決定不逐步記錄，以錄影為證。T065 以兩份真實 Google 學習單匯入（不記錄試算表網址與憑證）。
