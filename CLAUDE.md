# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案現況

軟體工程期末專題（NCU SE6005）第 16 組 SpecKit 小組的「Vibe Coding 課堂搶答系統」：老師匯入 Google Sheets 格式的 Guided Notes，各組學生搶答，最後把搶答成功的答案寫回原學習單。組員：jacky0407、EricC430。

**憲章 v1.1.0 已完成**（`.specify/memory/constitution.md`，2026-11-21 以 `/speckit-constitution` 產生；v1.0.1 補上 lint 與型別檢查工具，v1.1.0 於 2026-11-22 修訂原則 I 的討論範圍），**技術棧已定案**（憲章「技術限制與範圍」）：

- 堆疊與環境：Python 3.11 以上 + FastAPI；Google Sheets 匯入／寫回使用 Google Sheets API（OAuth，由老師授權）；Windows 本機執行，後端只監聽 localhost；活動狀態只存在記憶體，不用資料庫。
- 程式碼風格：PEP 8；公開函式／類別／方法必須有型別提示與 docstring；lint／格式化用 Ruff（`ruff check`、`ruff format`），型別檢查用 mypy（`src/`），設定在 `pyproject.toml`，提交前三者都要通過（憲章 v1.0.1）。
- 日誌：只用 `logging`（INFO、stdout），不用 `print`；不得記錄 token、授權碼、client secret。
- 效能：狀態變更 2 秒內反映到所有畫面（001 採 WebSocket 只推送、HTTP 負責操作）；效能驗證為老師 + 6 組、每組 2 條連線（001 研究 R2）；組數上限由老師建立活動時指定（1～99，alignment 2026-11-23 A2）。
- **架構（NON-NEGOTIABLE）**：核心邏輯（學習單解析、提交判定、順位計算）是不依賴網路、框架與系統時鐘的純函式，時間由呼叫端傳入；Google、API、畫面在外層轉接層，相依只能由外層指向核心。

**共用骨架**（Issue #5，`chore/5-project-skeleton`）：`pyproject.toml`、`src/lecture_quiz/{core,app,adapters}/`、`main.py`、共用 HTTP 錯誤／日誌（`adapters/web/common.py`）、前端共用 `static/js/{api,sync,identity}.js`、`tests/conftest.py`（`FakeClock`）、`tests/architecture/test_core_is_pure.py`。完整說明與子功能擴充約定見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。指令（Windows，先 `py -3.11 -m venv .venv`，再 `.venv\Scripts\python -m pip install -e ".[dev]"`；專案路徑含中文時要改 `.pth`、只跑不改時可用一般安裝 `pip install ".[dev]"`，三種做法見 DEVELOPMENT.md「專案路徑含中文時」，不要用 `PYTHONUTF8`）：

- lint／格式：`ruff check .`、`ruff format --check .`；型別：`mypy`（只檢查 `src/`）；測試：`pytest`（預設排除 `perf`；單一測試：`pytest tests/contract/test_http_common.py::test_health`）。
- 啟動：`python -m lecture_quiz`（只監聽 127.0.0.1:8000）。

**001-activity-session 已實作**（`feature/5-001-activity-session`，PR #15）：`src/lecture_quiz/core/activity/`（純函式狀態機、輸入規則、快照裁切）、`app/activity/`（`ActivityService`、registry、ports）、`adapters/web/{http_api,ws_sync}.py`、`adapters/static/{teacher,student}.html`。組別以組號識別（`Group.number: int`），`Activity.max_groups` 為組數上限；給 002～005 的服務介面見 `specs/001-activity-session/contracts/service-interfaces.md`。

**002-guided-notes-import 已實作**（PR #11、#17；#17 誤合併到 `feature/6-guided-notes-import` 而非 main，2026-11-24 另開 PR 補進 main；T028、T071 的真實 Google 驗證已由 EricC430 回報通過（2026-11-23，細節依其決定未記錄）、T072 不做、T076 待 jacky0407，見 `specs/002-guided-notes-import/quickstart.md` 紀錄表；001 的開發用 seed API 已移除，003 的格數來源改為 `ImportService.blanks_per_question`）：三層路徑 `src/lecture_quiz/core/guided_notes_import/`（`parse(snapshot)` 純函式）、`app/guided_notes_import/`（`ImportService`、連接埠、記憶體存放）、`adapters/google/`（授權、Sheets 唯讀、錯誤對應）與 `adapters/web/guided_notes_import.py`、`adapters/static/js/import.js`。Google 設定放 `.env`（只放 `.env.example`；`python -m lecture_quiz` 會載入它，**不要**直接用 `uvicorn` 啟動，access log 會記下授權碼）。測試：預設 `pytest -m "not real_google and not perf"`（`addopts` 已排除兩者；命令列的 `-m` 會覆蓋它）；真實路徑手動執行 `pytest -m real_google`（需 `REAL_GOOGLE_*` 環境變數，缺少會明確失敗）。

**003-round-submission 已實作**（`feature/7-003-round-submission`，PR #16；US1～US6 完成，待非實作者人工驗證 T064 與 002 接上後的真實路徑驗證 T065）：spec、plan、research、data-model、contracts、quickstart、verification（含實作問題紀錄）在 `specs/003-round-submission/`；程式在 `core/round_submission/`、`app/round_submission/`、`adapters/web/submission_api.py`、前端 `js/{submission,round-submission,round-submission-teacher}.js`。提交資料存在 003 自己的記憶體 store；判定、標記、保存經 001 新增的 `ActivityService.record_submission` 在同一把活動鎖內完成，提交資料以 001 的快照擴充機制推送；每題子空格數由 002 實作 `QuestionShapeSource`。Q-20／21／22／26 與「答錯／搶答失敗」顯示方式已獲 OpenSpec 組同意（alignment 2026-11-23）。

**004-ranking-review 已實作**（`feature/8-004-ranking-review`，PR #20；US1～US7 與 Polish 自動化部分完成，待非實作者人工驗證 T094 與 003 負責人確認 T077）：spec、plan、research、data-model、contracts、quickstart、verification（含實作問題紀錄 P-01～）在 `specs/004-ranking-review/`；程式在 `core/ranking_review/`（題序、速度／公平排名、整輪重算、判錯規則、結果檢視，純函式）、`app/ranking_review/`（`RankingService`、`ReviewStore`，自己的每活動鎖，推送在鎖外）、`adapters/web/ranking_review.py`、前端 `js/{ranking-common,ranking-review,ranking-review-teacher}.js`；`main.py` 的 `_wire_ranking` 在 003 之後組裝。**對既有功能的影響**：`POST /activities/{code}/rounds/current/finalize` 改由 004 提供（本文必須帶 `resultVersion`），001 的空定案路由與老師頁舊「確認定案」按鈕已移除；003 學生頁不再列出各組已公開答案（改由 004 學生區塊只顯示本組、目前搶答成功者與剛被判錯的前一組，FR-037），003 的資料與後端未改。結果版本 `resultVersion` 與 001 的 `version` 獨立。Q-23／24／25 已於 alignment 定案。

子功能依序為 `001-activity-session` → `002-guided-notes-import` → `003-round-submission` → `004-ranking-review` → `005-result-export`（各自另開 Issue）。

回覆與文件一律使用台灣繁體中文。

## 兩個重要的本機檔案（不追蹤）

`.gitignore` 排除了下列檔案，但它們是需求的來源，開工前先讀：

- `期末專題說明.md`（與原始 `期末專題說明.pdf`）：課程作業說明，是需求與評分標準的依據。
- `project_proposal_draft.md`：小組提案草稿（功能清單 C1–E6、五個子功能拆分 001–005、各子功能的 `/speckit-*` prompt、待與 OpenSpec 組對齊的事項）。**這是草稿**：Python／FastAPI 與 Google Sheets API（OAuth）已由憲章定案；其餘細節（例如選檔採 Google Picker，見 002 spec 的 Assumptions）以憲章、對齊紀錄與各子功能 spec 為準。

不要把這兩類檔案 `git add` 進去，也不要在 commit、PR、Issue 中貼出其內容中的機敏資訊。

## 跨組對齊文件（追蹤）

- `docs/openspec-reference/<能力>/spec.md`：OpenSpec 組 5 份 spec 的原封副本，是**使用者可見行為的唯一基準**（憲章原則 I）。不得修改；對方更新時整份重新複製，並更新 `docs/openspec-reference/README.md` 的取得日期與 SHA-256。`.gitattributes` 已對這些檔案關閉換行轉換。
- `docs/alignment.md`：跨組決議紀錄（日期、議題、結論、影響範圍、雙方確認人）與「待與 OpenSpec 組確認」問題清單。這份文件只收與對方組在重大功能性需求上的差異；實作細節與設計方式（選檔元件、OAuth scope 等）不放這裡，由 spec／plan 決定。撰寫子功能 spec 前先查這份清單；涉及仍「待確認」的項目時，在 spec 中標記 `[NEEDS CLARIFICATION]` 並引用問題編號（如 Q-07），不得自行假設答案。
- 每份子功能 spec 都要標註對應的 OpenSpec Requirement；偏離或新增行為須先記入 `docs/alignment.md` 並經雙方確認。

## 開發流程（Spec Kit + Claude）

完整規則見 [docs/PROJECT_WORKFLOW.md](docs/PROJECT_WORKFLOW.md)，動手前必讀。要點：

- Spec Kit v1.2.1 已安裝（`specify init --here --integration claude --script ps`），skill 位於 `.claude/skills/speckit-*`，命令是**連字號**格式：`/speckit-constitution`、`/speckit-specify`、`/speckit-clarify`、`/speckit-plan`、`/speckit-tasks`、`/speckit-analyze`、`/speckit-implement`、`/speckit-converge`（另有 `/speckit-checklist`、`/speckit-taskstoissues`）。
- 流程：憲章全專案一份；每個子功能各跑一次 specify → clarify → plan → tasks → analyze → implement → converge。子功能產物放在 `specs/<編號>-<名稱>/`。
- `.specify/memory/constitution.md` 是 v1.1.0 憲章（7 項核心原則，其中 I 跨組行為一致、II 圖表生成／PlantUML 設計優先為 NON-NEGOTIABLE）。`/speckit-plan` 的 Constitution Check 須逐條檢查；修改憲章須走 PR 並經兩位組員同意。
- **憲章不保證會被自動遵守**：每個子功能的 `/speckit-specify`、`/speckit-plan` prompt 都要再明確寫一次原則 III（動態定位、兩份版面學習單驗證）、V（資料可見性、安全輸出、輸入驗證與錯誤訊息）、VI（Scenario 對應測試、Google mock、真實路徑驗證、人工驗證）與架構限制。
- 一致性範圍包含 Demo 影片：錄影前依規章第 11 節鎖定 Git tag。
- `.specify/templates/overrides/` 放專案覆寫範本（優先於 core）：`spec-template.md` 加了「OpenSpec Traceability」與「Diagrams」必填區塊；`tasks-template.md` 把測試改為必做，並加入架構分層要求，以及圖表一致性、真實 Google 路徑、兩份版面學習單、效能、日誌與人工驗證任務。core 範本不要改。`/speckit-tasks` 的 SKILL.md 仍寫「Tests are OPTIONAL」，**以憲章原則 VI 為準，一律產生測試任務**。
- `.specify/feature.json` 是本機狀態（已被 `.specify/.gitignore` 排除），記錄目前子功能目錄；切換子功能前先確認它指向正確位置。
- `.specify/scripts/powershell/` 是 `ps` 版腳本（本機是 Windows）；若組員用其他系統，需確認所用腳本類型一致。
- Git：不直接在 `main` 開發；分支 `feature/<issue>-<name>` 等，commit 格式 `<type>: <summary>`，PR 用 Squash and merge，作者不得核准自己的 PR。先建 Issue 再動工。

## 課程硬性限制（影響所有設計與實作）

- **Diagram First（SpecKit 組必做）**：憲章必須加入 PlantUML 設計優先原則——specify 階段產出組件圖、類別圖、時序圖到 `./diagrams/*.puml`，用 `java -jar plantuml.jar "./diagrams/*.puml"` 轉 PNG 放同目錄；plan 以圖為藍圖；implement 後要驗證程式碼與圖一致。本機已有 Java（jdk-19），`plantuml.jar` 需自行下載且已被 `.gitignore` 排除。原文範本在 `期末專題說明.md` 附錄。
- **Guided Notes 匯入／匯出不得寫死儲存格位置**：助教會拿另一份學習單測試，必須依表頭與內容動態定位。
- 不得在文件、程式碼或 repo 中放密碼、金鑰、機敏資料（`.env`、憑證 JSON 已在 `.gitignore`，repo 只放 `.env.example`）。
- 只需在本機跑，不必架設可供外部連線的伺服器。
- 與 OpenSpec 小組的系統功能必須一致；重大功能性差異先討論並記錄在 `docs/alignment.md`，實作細節與設計方式不需要（範圍見 PROJECT_WORKFLOW 第 10 節）。
- 評分會對照 constitution、spec、plan、tasks、圖表與程式碼、Demo 影片是否一致，所以任何一方改動都要同步其餘部分。
- 繳交期限 2026-11-30 00:00，內部以 11/29 晚上為凍結點。
