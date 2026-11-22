# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案現況

軟體工程期末專題（NCU SE6005）第 16 組 SpecKit 小組的「Vibe Coding 課堂搶答系統」：老師匯入 Google Sheets 格式的 Guided Notes，各組學生搶答，最後把搶答成功的答案寫回原學習單。組員：jacky0407、EricC430。

**憲章 v1.0.1 已完成**（`.specify/memory/constitution.md`，2026-11-21，以 `/speckit-constitution` 產生；v1.0.1 補上 lint 與型別檢查工具），**技術棧已定案**（憲章「技術限制與範圍」）：

- 堆疊與環境：Python 3.11 以上 + FastAPI；Google Sheets 匯入／寫回使用 Google Sheets API（OAuth，由老師授權）；Windows 本機執行，後端只監聽 localhost；活動狀態只存在記憶體，不用資料庫。
- 程式碼風格：PEP 8；公開函式／類別／方法必須有型別提示與 docstring；lint／格式化用 Ruff（`ruff check`、`ruff format`），型別檢查用 mypy（`src/`），設定在 `pyproject.toml`，提交前三者都要通過（憲章 v1.0.1）。
- 日誌：只用 `logging`（INFO、stdout），不用 `print`；不得記錄 token、授權碼、client secret。
- 效能：狀態變更 2 秒內反映到所有畫面（WebSocket 或 SSE 由 plan 決定）；效能驗證組數 N 由 001 plan 決定；組數上限待 alignment Q-07，不得自訂。
- **架構（NON-NEGOTIABLE）**：核心邏輯（學習單解析、提交判定、順位計算）是不依賴網路、框架與系統時鐘的純函式，時間由呼叫端傳入；Google、API、畫面在外層轉接層，相依只能由外層指向核心。

**共用骨架**（Issue #5，`chore/5-project-skeleton`）：`pyproject.toml`、`src/lecture_quiz/{core,app,adapters}/`、`main.py`、共用 HTTP 錯誤／日誌（`adapters/web/common.py`）、前端共用 `static/js/{api,sync,identity}.js`、`tests/conftest.py`（`FakeClock`）、`tests/architecture/test_core_is_pure.py`。完整說明與子功能擴充約定見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。指令（Windows，先 `py -3.11 -m venv .venv`，再 `.venv\Scripts\python -m pip install -e ".[dev]"`）：

- lint／格式：`ruff check .`、`ruff format --check .`；型別：`mypy`（只檢查 `src/`）；測試：`pytest`（預設排除 `perf`；單一測試：`pytest tests/contract/test_http_common.py::test_health`）。
- 啟動：`python -m lecture_quiz`（只監聽 127.0.0.1:8000）。

子功能依序為 `001-activity-session` → `002-guided-notes-import` → `003-round-submission` → `004-ranking-review` → `005-result-export`（各自另開 Issue）。

回覆與文件一律使用台灣繁體中文。

## 兩個重要的本機檔案（不追蹤）

`.gitignore` 排除了下列檔案，但它們是需求的來源，開工前先讀：

- `期末專題說明.md`（與原始 `期末專題說明.pdf`）：課程作業說明，是需求與評分標準的依據。
- `project_proposal_draft.md`：小組提案草稿（功能清單 C1–E6、五個子功能拆分 001–005、各子功能的 `/speckit-*` prompt、待與 OpenSpec 組對齊的事項）。**這是草稿**：Python／FastAPI 與 Google Sheets API（OAuth）已由憲章定案；其餘細節（例如是否使用 Picker，見 `docs/alignment.md` Q-11）以憲章、對齊紀錄與各子功能 spec 為準。

不要把這兩類檔案 `git add` 進去，也不要在 commit、PR、Issue 中貼出其內容中的機敏資訊。

## 跨組對齊文件（追蹤）

- `docs/openspec-reference/<能力>/spec.md`：OpenSpec 組 5 份 spec 的原封副本，是**使用者可見行為的唯一基準**（憲章原則 I）。不得修改；對方更新時整份重新複製，並更新 `docs/openspec-reference/README.md` 的取得日期與 SHA-256。`.gitattributes` 已對這些檔案關閉換行轉換。
- `docs/alignment.md`：跨組決議紀錄（日期、議題、結論、影響範圍、雙方確認人）與「待與 OpenSpec 組確認」問題清單。撰寫子功能 spec 前先查這份清單；涉及仍「待確認」的項目時，在 spec 中標記 `[NEEDS CLARIFICATION]` 並引用問題編號（如 Q-11），不得自行假設答案。
- 每份子功能 spec 都要標註對應的 OpenSpec Requirement；偏離或新增行為須先記入 `docs/alignment.md` 並經雙方確認。

## 開發流程（Spec Kit + Claude）

完整規則見 [docs/PROJECT_WORKFLOW.md](docs/PROJECT_WORKFLOW.md)，動手前必讀。要點：

- Spec Kit v1.2.1 已安裝（`specify init --here --integration claude --script ps`），skill 位於 `.claude/skills/speckit-*`，命令是**連字號**格式：`/speckit-constitution`、`/speckit-specify`、`/speckit-clarify`、`/speckit-plan`、`/speckit-tasks`、`/speckit-analyze`、`/speckit-implement`、`/speckit-converge`（另有 `/speckit-checklist`、`/speckit-taskstoissues`）。
- 流程：憲章全專案一份；每個子功能各跑一次 specify → clarify → plan → tasks → analyze → implement → converge。子功能產物放在 `specs/<編號>-<名稱>/`。
- `.specify/memory/constitution.md` 是 v1.0.1 憲章（7 項核心原則，其中 I 跨組行為一致、II 圖表生成／PlantUML 設計優先為 NON-NEGOTIABLE）。`/speckit-plan` 的 Constitution Check 須逐條檢查；修改憲章須走 PR 並經兩位組員同意。
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
- 與 OpenSpec 小組的系統功能必須一致；影響行為或規則的變更先討論並記錄在 `docs/alignment.md`。
- 評分會對照 constitution、spec、plan、tasks、圖表與程式碼、Demo 影片是否一致，所以任何一方改動都要同步其餘部分。
- 繳交期限 2026-11-30 00:00，內部以 11/29 晚上為凍結點。
