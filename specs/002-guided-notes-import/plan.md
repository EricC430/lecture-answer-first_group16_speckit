# Implementation Plan: Guided Notes 匯入（Google Sheets 學習單）

**Branch**: `feature/6-guided-notes-import` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-guided-notes-import/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/002-guided-notes-import-component.puml`](../../diagrams/002-guided-notes-import-component.puml)
- 類別圖：[`diagrams/002-guided-notes-import-class.puml`](../../diagrams/002-guided-notes-import-class.puml)
- 時序圖：[`diagrams/002-guided-notes-import-sequence.puml`](../../diagrams/002-guided-notes-import-sequence.puml)

本 plan 的模組、類別與流程都依這三張圖命名；plan 補充細節而需要偏離圖時，先改圖並重新轉出 PNG（本次 plan 已同步更新類別圖，見「圖表同步」）。

## Summary

老師在活動準備中（001 的準備中或開放加入，第一輪開始前），用 Google 帳號授權、以 Google Picker 選一份 Google 試算表與一張工作表，系統唯讀取回工作表，**依「題號」「作答」文字表頭與合併範圍動態定位**，辨識單題與題組（題號縱向合併或相鄰重複），算出每題的精確答案格，整份驗證通過才交給 001 取代題目，並保存來源映射與匯入時結構供 005 寫回。

技術做法：

- **核心**：`core/guided_notes_import/` 的 `parse(snapshot) -> ParseResult` 是純函式，輸入不可變的工作表快照，沒有任何時間或 I/O；錯誤全部收集後一起回報，任何錯誤就不產生題目（原子）。
- **應用層**：`ImportService` 以「每個活動一把匯入鎖」序列化，順序固定為「查階段與身分 → 讀取 → 解析 → 001 `replace_questions` → 才保存來源映射與結構」，001 拒絕時 002 完全不變。
- **外層**：後端以授權碼流程持有 token（只在記憶體）；範圍只用非敏感的 `drive.file`；Sheets 與 Drive 以官方程式庫唯讀存取；Picker 只在前端選檔，後端重新驗證類型。
- **前端**：沿用 001 的原生 JavaScript，`teacher.html` 加一個區塊，邏輯放 `adapters/static/js/import.js`。

## Technical Context

**Language/Version**：Python 3.11 以上

**Primary Dependencies**：

- 沿用 001：FastAPI、uvicorn、pydantic v2；開發用 pytest、pytest-timeout、httpx（`TestClient`）、ruff、mypy。
- 本子功能新增（追加在 `pyproject.toml` 相依列表最後）：`google-api-python-client`（Sheets v4、Drive v3，含 `HttpMockSequence` 供測試）、`google-auth`、`google-auth-oauthlib`。**皆為核心路徑會用到的套件，列在核心相依，不放選用 extra**；版本於實作加入相依時以 `pip index versions` 查證並記錄，不憑記憶。
- 前端載入 Google 官方的 `https://apis.google.com/js/api.js`（Picker），無版本號可釘，是 Picker 的官方載入方式。

**Storage**：無。授權 token、選定來源、匯入結果都只在後端記憶體，重啟即清空（原則 VII）。

**Testing**：pytest。核心單元（表格驅動、兩份版面＋九種缺陷＋近似錯誤對照）、應用層（Fake 連接埠）、轉接層（`HttpMockSequence`）、HTTP 契約（`TestClient`）、架構純度（`ast`）；真實 Google 用 `@pytest.mark.real_google` 手動執行，缺環境變數時明確失敗。詳見 [research.md](research.md) R9。

**Target Platform**：Windows 10／11 本機；後端只監聽 `127.0.0.1`（OAuth 回呼用 `localhost`）；Chrome 或 Edge。

**Project Type**：單一專案的 Web 應用，沿用 001 的三層結構。

**Performance Goals**：50 題以內的學習單，從確認工作表到預覽在 10 秒內（SC-006）。做法是兩次欄位遮罩的唯讀請求，Google 呼叫以 `asyncio.to_thread` 執行，不阻塞其他活動的同步（技術限制 4）。

**Constraints**：

- 核心不得依賴網路、框架與系統時鐘。
- 日誌只用 `logging`（INFO、stdout），不記錄 token、授權碼、`state`、client secret、試算表標題與儲存格內容。
- 匯入只讀取，不修改老師試算表（FR-023）。
- 不提供本地 XLSX 上傳（FR-005）。

**Scale/Scope**：題數約 50 題以內、單張工作表數百列；一個老師頁面區塊、8 個 HTTP 端點、0 條新的 WebSocket（匯入後題目變動由 001 的快照同步）。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 檢查項 | 結果 | 依據 |
|---|---|---|
| **I 跨組行為一致** | ✅ 通過 | spec 的 Traceability 涵蓋 guided-notes-import 全部 5 條 Requirement；沒有超出 OpenSpec 原文的新增行為（2026-11-21 起「結構輔助定位」已取消，alignment.md 的取代列確認人已補）。本 plan 沒有新增或改變使用者可見行為；選檔元件、授權範圍、單一工作表自動選用等屬實作決定，不列入 alignment.md |
| **II 圖表生成** | ✅ 通過 | 以三張圖為藍圖；本 plan 補的 `requester`、`inspect`、`SourceSelection`、授權相關方法已同步更新類別圖並重新轉出 PNG。tasks 必須有「程式碼與圖表一致性驗證」任務 |
| **III Guided Notes 動態定位** | ✅ 通過 | 解析只依文字表頭、合併範圍與相對位置，不含固定座標或工作表名稱（[research R4](research.md)）；匯入原子（解析全過才呼叫 001，001 拒絕時 002 不保存）；SC-003 與 research R9 要求至少兩份版面不同的學習單；來源映射與匯入時結構保存供 005 寫回前重驗 |
| **IV 後端為唯一事實來源** | ✅ 通過 | 身分與階段由 001 判定；Picker 的類型過濾不採信，後端以 Drive `mimeType` 重新驗證；工作表識別由後端驗證屬於所選試算表；解析是確定性純函式 |
| **V 資料可見性與安全** | ✅ 通過 | 學生沒有任何匯入端點；token 只在後端記憶體、`picker-config` 只回短效 `drive.file` token 並 `no-store`；`state` 一次性且有期限；錯誤訊息固定對照表且不含內部細節；試算表文字以 `textContent` 輸出並截斷；`.env` 不入版控；空字串金鑰視為未設定並明確失敗 |
| **VI 驗收情境驅動測試** | ✅ 通過（待實作後以 tasks 驗證） | 每個 Acceptance Scenario（US1～US6，共 28 個）與 Edge Case 至少一個測試，docstring 標明 Scenario；Google 一律 mock；真實路徑驗證列入 [quickstart](quickstart.md) B 區（兩份真實版面）；非實作者（jacky0407）人工驗證並記錄。**尚未執行任何驗證，不宣稱完成** |
| **VII 簡單與本機運作** | ✅ 通過 | 只用記憶體、沿用單一 process、只監聽本機；沒有資料庫。唯一新增的複雜度是 Google 官方程式庫與 Picker 的外部腳本，屬需求（使用者指定 Picker 選檔、憲章指定 Google Sheets API）而非額外設計 |
| **技術限制 1 堆疊** | ✅ 通過 | Python 3.11 以上 + FastAPI；Google Sheets API 與 OAuth 由老師授權；Windows 本機、只監聽 localhost |
| **技術限制 2 程式碼風格** | ✅ 通過 | Ruff（含 D、ANN）與 mypy 沿用 001 定案的設定；公開函式與類別都要有型別提示與 docstring |
| **技術限制 3 日誌** | ✅ 通過 | `logging`、INFO、stdout；欄位白名單見 [http-api](contracts/http-api.md) 的「日誌」 |
| **技術限制 4 效能** | ✅ 通過 | SC-006 的 10 秒；Google 呼叫放執行緒，不拖慢 2 秒同步；N 由 001 plan 決定（N = 6），匯入不增加推送連線 |
| **技術限制 4 架構（NON-NEGOTIABLE）** | ✅ 通過 | 核心 `core/guided_notes_import/` 只依賴標準函式庫；Google 程式庫只在 `adapters/google/`；相依 `adapters → app → core`；架構測試（沿用 001 的 `ast` 掃描）納入本核心套件 |

**Phase 1 設計完成後重新檢查**：結果相同，沒有新增違規；Complexity Tracking 沒有需要說明的違規，只列兩項需要留意的相依。

## 待真實驗證的假設

這些在官方文件中沒有明確寫出，或只由不同頁面各自支持。實作時以 SC-009 的真實試算表驗證，**驗證前不得宣稱已成立**；若不成立，修改範圍如表所示。

| 假設 | 來源 | 若不成立的修改範圍 |
|---|---|---|
| `drive.file` 足以讓 `spreadsheets.get` 讀取 Picker 選到的試算表（也足以讓 005 寫入） | Drive 範圍說明與 `spreadsheets.get` 範圍清單各自支持，沒有單頁明說。**2026-11-23 讀取已由 EricC430 以真實帳號驗證成立（T028，細節未記錄）；寫入（005）尚未驗證** | 授權範圍常數與 `.env.example`；改用敏感範圍時 OAuth 同意畫面要加測試使用者；不影響核心與應用層 |
| `GridRange` 結束索引為「不含」 | **2026-11-23 已由官方 API 參考文件確認**：索引從 0 起算、半開區間，起點含、終點不含，例如 A3:B4 為 start_row_index 2、end_row_index 4（見 [.NET 版 GridRange 參考](https://googleapis.dev/dotnet/Google.Apis.Sheets.v4/latest/api/Google.Apis.Sheets.v4.Data.GridRange.html)、[Ruby 版](https://googleapis.dev/ruby/google-apis-sheets_v4/v0.38.0/Google/Apis/SheetsV4/GridRange.html)）。T071 回報通過也與此一致；不做真實回應 fixture 測試（T072，2026-11-23 EricC430 決定）；轉接層測試用手寫 JSON | 轉接層的座標轉換函式與其測試 |
| 將非 Google 試算表交給 `spreadsheets.get` 時的錯誤型態 | 未查證；已用 Drive `mimeType` 先擋，這只是保險 | 轉接層錯誤對應表 |
| Picker 在本機 `http://localhost` 來源下，可以正常運作；API 金鑰先只限制 API 種類，不設網站來源限制 | Picker 官方指南提到金鑰需允許來源。**2026-11-23 EricC430 在真實環境走過 Picker（T028、T071），回報可運作，細節未記錄** | 金鑰限制設定與 quickstart 的設定步驟 |

## 相依與時程

- **相依 001**：`ActivityGateway`（`stage`、`is_teacher`、`replace_questions`）契約已對齊（Issue #6）。001 尚在 `feature/5-001-activity-session` 分支，未合併。
- **2026-11-23 現況**：骨架 PR #14 與 001 的 PR #15 都已合併到 `main`，001 已含 `ActivityGateway`（`src/lecture_quiz/app/activity/ports.py`：`stage`、`is_teacher` 為同步，`replace_questions` 為 async）與新增的「開放加入」階段（`PREPARING`、`JOINING` 都可匯入）。002 已合併 `origin/main`。下一段是 2026-11-22 當時的歷史紀錄。
- **（歷史，2026-11-22）骨架 PR 凍結**（jacky0407 於 Issue #5 約定，2026-11-21 留言）：骨架 PR 計畫命名為 `chore/5-project-skeleton`，但**截至 2026-11-22 遠端沒有這個分支，也沒有對應 PR**（001 分支也還沒有 `pyproject.toml`、`src/`），實際分支名稱與時間以 jacky0407 為準。骨架 PR 合併前，002 **不得**建立 `pyproject.toml`、`main.py`、`src/`；合併後從 main 接續。因此本 plan 只產出文件，不產生程式碼。**2026-11-22 更新**：骨架 PR 已開為 #14（尚未合併），001 的 PR 為草稿 #15。決定**等相依完成再開始實作**：`/speckit-implement` 前要確認骨架 PR 已合併，且 001 的活動建立、老師 token、`replace_questions`、開輪與取消已完成（在 main 或 001 分支皆可）；骨架 PR 只涵蓋 001 的 T001～T022，不含這些功能（tasks T001）。
- **共用檔案約定**：`main.py` 只加一行 router；`teacher.html` 只加一個區塊；`pyproject.toml` 相依追加在最後；`docs/alignment.md` 只追加在最後。
- **001 的開發用 seed API**（`LECTURE_QUIZ_DEV_SEED=1`）：**已於 2026-11-23 在 002 的實作分支移除**（tasks T077；jacky0407 尚未確認）。
- **給 003 的介面**：003 需要每題子空格數（`QuestionShapeSource.blanks_per_question(code)`）。由 002 的 `ImportService` 以 `ImportRecord.blanks` 計數實作，契約見 [contracts/service-interfaces.md](contracts/service-interfaces.md)「給 003」，任務為 T083（PR #11 審查，jacky0407 要求寫成文件）。
- **後續**：005 依 `ImportRecord` 與同一個 `AuthGateway`／`SheetsReader` 寫回。

## Project Structure

### Documentation (this feature)

```text
specs/002-guided-notes-import/
├── spec.md
├── plan.md              # 本檔
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1（也是人工驗證腳本與紀錄表）
├── contracts/
│   ├── http-api.md
│   └── service-interfaces.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2（/speckit-tasks 產生）
```

### Source Code (repository root)

骨架由 001 的骨架 PR 建立；以下只列 002 新增的路徑（依 Issue #5 的約定放在 `core/<能力>/`、`app/<能力>/`、`adapters/web/<能力>.py`）。

```text
src/lecture_quiz/
├── core/guided_notes_import/        # 純函式層：只依賴標準函式庫
│   ├── models.py                    # CellRef、CellValue、MergeRange、SheetSnapshot、Question、Blank、StructureSnapshot、ValidationIssue、ParseResult
│   ├── numbers.py                   # 題號正規化（research R5）
│   ├── grid.py                      # 合併範圍查詢、儲存格文字
│   ├── hints.py                     # 每個 IssueKind 的修正建議、欄字母、引用截斷
│   ├── headers.py                   # 找表頭、判定歧義
│   ├── rows.py                      # 逐列分類：題號繼承、子編號、答案格、忽略空白列
│   ├── validator.py                 # 分組、連續性、重疊、孤立子空格
│   └── parser.py                    # GuidedNotesParser.parse
├── app/guided_notes_import/
│   ├── ports.py                     # AuthGateway、SheetsReader（Clock 與 ActivityGateway 沿用 001）
│   ├── models.py                    # SourceRef、SpreadsheetInfo、SourceSelection、ImportRecord、ImportPreview、ImportOutcome、ImportRejection
│   ├── store.py                     # ImportStore（依活動代碼：session、selection、record、lock）
│   ├── messages.py                  # ImportRejection 與 IssueKind 的固定中文訊息對照表
│   └── service.py                   # ImportService
└── adapters/
    ├── google/
    │   ├── config.py                # 讀環境變數；空字串視為未設定
    │   ├── auth.py                  # GoogleAuthGateway：授權碼流程、state 管理、token 記憶體保存
    │   ├── sheets_reader.py         # GoogleSheetsReader：Drive mimeType 檢查、spreadsheets.get、轉成 SheetSnapshot
    │   └── errors.py                # HttpError → ImportRejection 對應
    ├── web/
    │   └── guided_notes_import.py   # 8 個端點、錯誤轉換、請求 log、/oauth/callback
    └── static/js/import.js          # 授權、Picker、選工作表、預覽與錯誤清單（teacher.html 只加一個區塊）

tests/
├── unit/core/guided_notes_import/   # 核心：兩份版面、九種缺陷、近似錯誤對照、題號正規化
├── unit/app/guided_notes_import/    # 服務層：順序、原子性、鎖、拒絕不改狀態
├── unit/adapters/google/            # HttpMockSequence：欄位遮罩、座標還原、錯誤對應
├── contract/guided_notes_import/    # HTTP 契約
├── integration/                     # 兩份版面走入口（T067）、日誌不含機敏資料（T065）
├── architecture/                    # 沿用 test_core_is_pure.py，納入本核心套件
├── fixtures/                        # 手寫 fixture（標明手寫）；真實回應 fixture 在真實驗證後才新增
└── real_google/                     # @pytest.mark.real_google，手動執行，缺環境變數明確失敗
scripts/capture_real_fixture.py       # 擷取並去識別化真實回應（T068，只在本機執行）
.env.example                         # 新增 5 個 Google 設定的空白範本（追加）
```

**Structure Decision**：沿用 001 的單一專案三層結構。`core`／`app`／`adapters` 對應組件圖的「核心」「應用層」「外層」，相依方向 `adapters → app → core`。Google 相關程式碼集中在 `adapters/google/`，讓核心與應用層完全看不到 Google 型別。

## 圖表同步

本 plan 依細節補充，已同步更新類別圖（`.puml` 與 PNG 同一個 commit）：

| 差異 | 原因 |
|---|---|
| `ImportService.selectSource` 加上 `requester`，新增 `inspectSpreadsheet`、`startAuth` | 老師身分檢查與「先檢視工作表清單再選」的流程（research R11） |
| 新增 `SourceSelection`、`SpreadsheetInfo`、`SourceRef` | 保存選定來源（FR-002）；取消選檔不寫入 |
| `AuthGateway` 補上 `startAuthorization`、`completeAuthorization`、`isAuthorized`、`pickerCredentials` | OAuth 授權碼流程與 Picker 設定（research R1） |
| `SheetsReader` 補上 `inspect`，`read` 帶活動代碼 | 授權依活動代碼保存 |

2026-11-22 `/speckit-analyze` 後再同步（類別圖、時序圖 `.puml` 與 PNG 同一個 commit；組件圖不需變動，已列出授權、選檔、Sheets 三個轉接元件）：

| 差異 | 原因 |
|---|---|
| 類別圖 `ImportService.import(code, requester, source)` 改為 `importSheet(code, requester)`，補 `getImportSummary` | 與契約一致：匯入使用已由 `PUT source` 記住的來源 |
| 類別圖 `ParseResult`、`ImportRecord` 的 `sourceMapping` 改為 `blanks`，`ImportRecord` 補 `sheetTitle`、`questionNumbers` | 與資料模型一致 |
| 類別圖 `SpreadsheetInfo` 補 `autoSelectSheetId` | 單一工作表自動選用由後端決定（FR-002） |
| 時序圖補上「檢視試算表（inspect，後端以檔案類型重新驗證）」「`autoSelectSheetId` 分支」「保存來源（`PUT source`）」，匯入改為不帶來源識別 | 先前時序圖與契約的端點流程不符 |

實作完成後仍須做「程式碼與圖表一致性驗證」（原則 II）。

## Complexity Tracking

> Constitution Check 沒有違規。以下兩項不是違規，是需要留意的相依與例外。

| 項目 | 為什麼需要 | 為什麼不用更簡單的做法 |
|---|---|---|
| Google 官方程式庫（`google-api-python-client` 等三個）與 Picker 外部腳本 | 憲章指定 Google Sheets API 與老師 OAuth；使用者指定 Picker 選檔；官方程式庫負責 token 更新並提供不連網的測試工具 | 直接呼叫 REST 要自己寫 token 更新與錯誤處理；貼上網址或 ID 違反使用者指定的 Picker |
| 每個活動一把匯入鎖（與 001 的活動鎖分開） | 匯入含網路讀取，不能持有 001 的鎖而阻擋該活動的同步與其他操作；又要避免連續快速匯入交錯 | 共用 001 的鎖會洩漏它的內部並拉長持鎖時間；不加鎖無法保證「最後成功的一次整份取代」 |

## Next Actions

1. **確認骨架 PR 狀態**：骨架 PR（目前尚未建立）合併前，不做 `/speckit-implement`；`/speckit-tasks` 與 `/speckit-analyze` 可以先做。
2. **執行 `/speckit-tasks`**：一律產生測試任務（憲章原則 VI）；必須包含「兩份版面學習單」「架構純度」「程式碼與圖表一致性」「真實 Google 路徑」「日誌不含機敏資料」「人工驗證」「確認 001 開發用 seed API 已移除」的任務，以及負面案例先於實作的順序。
3. **準備 Google Cloud 設定**：依 [quickstart.md](quickstart.md) 前置條件第 3 項，EricC430 先建立 OAuth 用戶端、API 金鑰並加入測試使用者，真實驗證才不會卡住。
4. **真實驗證待驗證假設**：實作的第一個里程碑就用一份真實試算表確認 `drive.file` 能讀取（research R1），避免做完才發現授權範圍不對。
