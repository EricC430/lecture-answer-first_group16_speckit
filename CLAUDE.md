# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案現況

軟體工程期末專題（NCU SE6005）第 16 組 SpecKit 小組的「Vibe Coding 課堂搶答系統」：老師匯入 Google Sheets 格式的 Guided Notes，各組學生搶答，最後把搶答成功的答案寫回原學習單。組員：jacky0407、EricC430。

**目前還沒有任何應用程式碼，也沒有 build／lint／test 指令。** repo 只有協作規章、README 與 Spec Kit 腳手架；技術棧尚未由憲章或 plan 定案。不要憑空假設指令或目錄結構，程式碼出現後再補上本節。

回覆與文件一律使用台灣繁體中文。

## 兩個重要的本機檔案（不追蹤）

`.gitignore` 排除了下列檔案，但它們是需求的來源，開工前先讀：

- `期末專題說明.md`（與原始 `期末專題說明.pdf`）：課程作業說明，是需求與評分標準的依據。
- `project_proposal_draft.md`：小組提案草稿（功能清單 C1–E6、五個子功能拆分 001–005、各子功能的 `/speckit-*` prompt、待與 OpenSpec 組對齊的事項）。**這是草稿，其中的技術選擇（Python／FastAPI、Picker 授權等）尚未與 OpenSpec 組對齊定案**，以憲章與各子功能 spec 為準。

不要把這兩類檔案 `git add` 進去，也不要在 commit、PR、Issue 中貼出其內容中的機敏資訊。

## 開發流程（Spec Kit + Claude）

完整規則見 [docs/PROJECT_WORKFLOW.md](docs/PROJECT_WORKFLOW.md)，動手前必讀。要點：

- Spec Kit v1.2.1 已安裝（`specify init --here --integration claude --script ps`），skill 位於 `.claude/skills/speckit-*`，命令是**連字號**格式：`/speckit-constitution`、`/speckit-specify`、`/speckit-clarify`、`/speckit-plan`、`/speckit-tasks`、`/speckit-analyze`、`/speckit-implement`、`/speckit-converge`（另有 `/speckit-checklist`、`/speckit-taskstoissues`）。
- 流程：憲章全專案一份；每個子功能各跑一次 specify → clarify → plan → tasks → analyze → implement → converge。子功能產物放在 `specs/<編號>-<名稱>/`。
- `.specify/memory/constitution.md` 目前仍是**未填寫的範本**（`[PROJECT_NAME]` 等佔位符），必須先跑 `/speckit-constitution` 才能進入子功能。
- `.specify/feature.json` 是本機狀態（已被 `.specify/.gitignore` 排除），記錄目前子功能目錄；切換子功能前先確認它指向正確位置。
- `.specify/scripts/powershell/` 是 `ps` 版腳本（本機是 Windows）；若組員用其他系統，需確認所用腳本類型一致。
- Git：不直接在 `main` 開發；分支 `feature/<issue>-<name>` 等，commit 格式 `<type>: <summary>`，PR 用 Squash and merge，作者不得核准自己的 PR。先建 Issue 再動工。

## 課程硬性限制（影響所有設計與實作）

- **Diagram First（SpecKit 組必做）**：憲章必須加入 PlantUML 設計優先原則——specify 階段產出組件圖、類別圖、時序圖到 `./diagrams/*.puml`，用 `java -jar plantuml.jar "./diagrams/*.puml"` 轉 PNG 放同目錄；plan 以圖為藍圖；implement 後要驗證程式碼與圖一致。本機已有 Java（jdk-19），`plantuml.jar` 需自行下載且已被 `.gitignore` 排除。原文範本在 `期末專題說明.md` 附錄。
- **Guided Notes 匯入／匯出不得寫死儲存格位置**：助教會拿另一份學習單測試，必須依表頭與內容動態定位。
- 不得在文件、程式碼或 repo 中放密碼、金鑰、機敏資料（`.env`、憑證 JSON 已在 `.gitignore`，repo 只放 `.env.example`）。
- 只需在本機跑，不必架設可供外部連線的伺服器。
- 與 OpenSpec 小組的系統功能必須一致；影響行為或規則的變更先討論並記錄在 `docs/alignment.md`（尚未建立）。
- 評分會對照 constitution、spec、plan、tasks、圖表與程式碼、Demo 影片是否一致，所以任何一方改動都要同步其餘部分。
- 繳交期限 2026-11-30 00:00，內部以 11/29 晚上為凍結點。
