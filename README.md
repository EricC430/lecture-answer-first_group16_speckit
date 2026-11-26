# lecture-answer-first_group16_speckit

## 課堂學習單搶答加分師生互動系統

軟體工程期末專題（NCU SE6005）第 16 組，開發方針：SpecKit（Spec Kit + Claude）。

組員：jacky0407、EricC430

老師匯入 Google Sheets 格式的 Guided Notes（學習單），各組學生用瀏覽器搶答，老師判錯與定案後，把搶答成功的答案寫回原學習單（也可匯出 CSV）。系統只在本機執行，活動狀態存在記憶體，不使用資料庫。

## 使用流程

1. **老師**開啟老師頁建立活動（指定組數上限 1～99），取得活動代碼。
2. **老師**授權 Google 並選取學習單，系統依表頭與內容動態定位題目與空格後匯入（不寫死儲存格位置）。
3. **學生**開啟學生頁，輸入活動代碼與組號加入。
4. **老師**開輪（可選題目與規則），各組在時限內送出答案；畫面在 2 秒內同步到所有裝置。
5. 系統依速度模式或公平模式（參考各組歷史成功次數）排出每題的順位；**老師**判錯時整輪重新計算，確認後定案本輪。
6. **老師**可在活動進行中或結束後，把已定案的搶答成功答案寫回原 Google 試算表，或下載 CSV。

## 子功能與進度

| 編號 | 子功能 | 內容 | 狀態 |
|---|---|---|---|
| 001 | [activity-session](specs/001-activity-session/) | 活動建立、組號加入、開關輪與階段同步（WebSocket 推送） | 已實作 |
| 002 | [guided-notes-import](specs/002-guided-notes-import/) | Google 授權、Picker 選檔、動態解析學習單 | 已實作 |
| 003 | [round-submission](specs/003-round-submission/) | 多題搶答、送出判定與資料可見性 | 已實作 |
| 004 | [ranking-review](specs/004-ranking-review/) | 速度／公平順位、判錯重算、定案 | 已實作 |
| 005 | [result-export](specs/005-result-export/) | 定案成果寫回 Google Sheets、CSV 匯出 | 已實作，真實 Google 寫入待驗證 |
| 006 | [ui-refresh](specs/006-ui-refresh/) | 介面改版（幾何記號、投影可讀） | 已實作，待人工驗證 |
| 007 | [browser-identity-sync](specs/007-browser-identity-sync/) | 同一瀏覽器的所有分頁共用學生身分、跨分頁同步 | 已實作，待人工驗證 |

各子功能目錄都有 spec、plan、tasks、quickstart（含驗證紀錄）；組件圖、類別圖、時序圖放在 [diagrams/](diagrams/)（`.puml` 與轉出的 `.png`）。尚待完成的人工或真實路徑驗證，以各子功能的 tasks 與 quickstart 為準。

## 快速開始（Windows，Python 3.11 以上）

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
# 只有專案路徑含中文時才需要下一行（Python 3.13 以上也不需要），原因見開發指南
Set-Content .venv\Lib\site-packages\_editable_impl_lecture_quiz.pth "../../../src" -Encoding ascii
.venv\Scripts\python -m lecture_quiz
```

啟動後開啟 <http://127.0.0.1:8000/>，首頁有老師頁與學生頁的入口。後端只監聽 `127.0.0.1`，連接埠可用環境變數 `LECTURE_QUIZ_PORT` 改變（預設 8000）。

- 只想跑起來、不改程式（例如全新 clone 驗證）時，可改用一般安裝 `.venv\Scripts\python -m pip install ".[dev]"`，不需要改 `.pth`；但之後改了 `src/` 要重新安裝才會生效。三種做法的比較見[開發指南](docs/DEVELOPMENT.md#專案路徑含中文時)。
- 請用 `python -m lecture_quiz` 啟動，不要直接用 `uvicorn`：前者會載入 `.env` 並關閉會記下授權碼的 access log。

### Google 設定

匯入與寫回需要 Google OAuth。把 [.env.example](.env.example) 複製為 `.env` 並填值，步驟見 [002 quickstart](specs/002-guided-notes-import/quickstart.md)。`.env` 已被 `.gitignore` 排除，不要提交，也不要貼到 Issue、PR 或聊天中。沒有設定時，其餘功能仍可使用，匯入會回報「未設定」。

## 檢查與測試

| 用途 | 指令 |
|---|---|
| lint | `.venv\Scripts\ruff check .` |
| 格式檢查 | `.venv\Scripts\ruff format --check .` |
| 型別檢查 | `.venv\Scripts\mypy`（只檢查 `src/`） |
| 測試 | `.venv\Scripts\pytest`（預設排除 `perf` 與 `real_google`） |
| 效能測試 | `.venv\Scripts\pytest -m perf` |
| 真實 Google 路徑 | `.venv\Scripts\pytest -m real_google`（手動執行，需 `REAL_GOOGLE_*` 環境變數，缺少會明確失敗；005 的測試會真的寫入試算表） |

提交前 `ruff check`、`ruff format --check`、`mypy` 三項都必須通過（憲章技術限制 2）。

## 架構

```text
src/lecture_quiz/
├── core/<能力>/     # 純函式：學習單解析、提交判定、順位計算；不依賴網路、框架與系統時鐘
├── app/<能力>/      # 服務層：活動鎖、狀態存放、連接埠
└── adapters/        # Google API、HTTP／WebSocket、前端靜態頁
```

相依方向只能是 `adapters → app → core`（憲章 NON-NEGOTIABLE），由 `tests/architecture/test_core_is_pure.py` 自動檢查。

## 文件導覽

| 文件 | 內容 |
|---|---|
| [憲章](.specify/memory/constitution.md) | 核心原則與技術限制（含跨組行為一致、PlantUML 設計優先） |
| [協作規章](docs/PROJECT_WORKFLOW.md) | Issue、分支、commit、PR 規則與 Spec Kit 開發流程 |
| [開發指南](docs/DEVELOPMENT.md) | 環境建立、常用指令、目錄分層與子功能擴充約定 |
| [跨組對齊紀錄](docs/alignment.md) | 與 OpenSpec 組的決議與待確認問題 |
| [OpenSpec 參考 spec](docs/openspec-reference/) | 對方組 spec 原封副本（不得修改） |
| [specs/](specs/) | 各子功能的 spec、plan、tasks、quickstart |
| [diagrams/](diagrams/) | 各子功能的 PlantUML 圖與 PNG |
