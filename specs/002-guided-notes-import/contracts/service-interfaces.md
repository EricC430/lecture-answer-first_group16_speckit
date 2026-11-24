# 服務介面契約：002 的連接埠與提供給 003、005 的介面

**用途**：002 在 Python 程式內的介面，不經過 HTTP。以 `typing.Protocol` 定義，放在 `src/lecture_quiz/app/guided_notes_import/ports.py`。所有跨出應用層的 I/O 都是 `async`；核心的 `parse` 是同步純函式。

## 002 使用 001 的介面（`ActivityGateway`）

契約以 001 的 [service-interfaces.md](../../001-activity-session/contracts/service-interfaces.md) 為準（2026-11-21 與 jacky0407 於 Issue #6 對齊），002 的類別圖已同步：

| 方法 | 002 的用法 |
|---|---|
| `stage(code) -> Stage \| None`（**同步**，依已合併的 001 `ports.py`） | 入口處判斷是否在第一輪開始前（`PREPARING` 或 `JOINING` 才允許）；活動不存在時為空；用來回 `ROUND_STARTED`／`ACTIVITY_CANCELLED`／`STAGE_NOT_PREPARING` |
| `is_teacher(code, requester) -> bool`（**同步**） | 非老師一律拒絕 |
| `replace_questions(code, requester, question_numbers: tuple[int, ...]) -> Outcome[int]`（**async**） | 解析成功後呼叫；**只傳題號清單**；成功回傳新 `version`；被拒時 001 的題目完全不變 |

## 002 定義的連接埠（由外層轉接層實作）

| 連接埠 | 方法 | 說明 |
|---|---|---|
| `AuthGateway` | `is_configured() -> bool` | Google 連線設定是否齊備（空字串視為未設定）；否則各入口回 `GOOGLE_NOT_CONFIGURED` |
| | `start_authorization(code, requester) -> Result[str]` | 產生一次性且有期限的 `state` 並回傳 Google 授權網址（`async`） |
| | `complete_authorization(state, auth_code, error) -> CallbackResult` | 驗證 `state`、交換 token 並存入記憶體；回傳活動代碼與結果（`ok`／`denied`／`error`） |
| | `is_authorized(code) -> bool` | 該活動老師是否有有效授權 |
| | `picker_credentials(code) -> Result[PickerConfig]`（`async`） | 回傳 Picker 用的短效 access token、API 金鑰與 App ID |
| `SheetsReader` | `inspect(code, spreadsheet_id) -> Result[SpreadsheetInfo]` | 先以 Drive 確認 `mimeType`，再取得工作表清單 |
| | `read(code, source: SourceRef) -> Result[SheetSnapshot]` | 以欄位遮罩讀取一張工作表並轉成核心的 `SheetSnapshot`（唯讀） |
| `Clock` | `now() -> datetime` | 沿用 001 的 `Clock`；只用於 `state` 有效期限，核心不使用 |

`Result[T]` 的形狀與 001 的 `Outcome[T]` 相同（`ok`、`value`、`rejection`），失敗時 `rejection` 為 `ImportRejection`。轉接層**不得**把 Google 的例外往上拋給應用層（程式錯誤除外）。

## 002 提供的服務（`ImportService`）

| 方法 | 說明 |
|---|---|
| `start_auth(code, requester) -> Result[str]` | 先查階段與身分，再委派 `AuthGateway` |
| `inspect_spreadsheet(code, requester, spreadsheet_id) -> Result[SpreadsheetInfo]` | 不改狀態；`SpreadsheetInfo.sheets` 只含可見工作表（隱藏者由轉接層或服務濾除，不計張數）；`SpreadsheetInfo.auto_select_sheet_id` 在清單恰好一張時為該張識別，否則為 `None`（單一工作表自動選用的判斷在這裡，不在前端） |
| `select_source(code, requester, source: SourceRef) -> Result[SourceSelection]` | 驗證 `sheet_id` 屬於該試算表後才保存；失敗不改舊選擇 |
| `import_sheet(code, requester) -> ImportOutcome` | 持有該活動的匯入鎖；順序見 [research.md](../research.md) R6 |
| `get_import_record(code) -> ImportRecord \| None` | **給 005 使用**：唯讀；回傳最後一次成功匯入的來源、來源映射與匯入時結構 |
| `get_import_summary(code, requester) -> Result[ImportPreview \| None]` | 老師頁面重新整理後恢復預覽（第一輪開始後仍可查看，只檢查存在與老師身分） |
| `get_import_result(code, requester) -> Result[ImportOutcome \| None]` | 恢復完整結果（含工作表標題與 001 版本），給端點 #8 |
| `auth_status(code, requester) -> Result[bool]`、`picker_config(code, requester) -> Result[PickerConfig]` | 端點 #3、#4 |

## 給 003（回合提交）

003 需要每題的子空格數（003 定義的 `QuestionShapeSource.blanks_per_question(code) -> Mapping[int, int] | None`，見 PR #16 `specs/003-round-submission/contracts/service-interfaces.md`）。**由 002 的 `ImportService` 實作**（2026-11-23 與 003 負責人協調的結論；tasks T083），003 不需要自己寫轉接：

| 方法 | 說明 |
|---|---|
| `blanks_per_question(code) -> Mapping[int, int] \| None` | 題號 → 該題子空格數（單題為 1；題組為子空格數）。由最後一次成功匯入的 `ImportRecord.blanks` 依題號計數換算；**該活動沒有成功匯入過時回 `None`**（活動不存在亦同） |

- **重新匯入後跟著更新**：第一輪開始前重新匯入成功，下一次呼叫就回新的格數；重新匯入失敗（含整份被拒）時 `ImportRecord` 不變，回傳的仍是舊格數。第一輪開始後 `ImportRecord` 鎖定，格數不再變動。
- 回傳不可變的新字典，003 無法改到 002 保存的資料；方法唯讀、不需要請求者身分，也不呼叫 Google。
- 002 的程式不匯入 003 的任何型別：`blanks_per_question` 只要方法簽章相符，003 即可把 `ImportService` 當作 `QuestionShapeSource`（結構性相符）。
- 002 合併前 003 的 `DevQuestionShapeSource` 仍依賴 001 的開發用 seed API；該 API 依 001 plan 在 002 合併後移除（本 PR 的實作 PR 已移除），003 在 002 合併後須改接 `ImportService`。

## 給 005（結果匯出）

| 需求 | 002 提供的方式 |
|---|---|
| 寫回哪些格子 | `ImportRecord.blanks`：每格的題號、子編號與目標（列, 欄） |
| 寫回前比對來源結構（OpenSpec result-export「來源結構一致性檢查」） | `ImportRecord.structure` 與 `source`（試算表與工作表識別）；005 用同一個 `parse` 重新解析當前工作表，與 `structure` 逐項比對 |
| 讀取與寫入 Google | 005 透過同一個 `AuthGateway`／`SheetsReader` 取得授權（授權範圍 `drive.file` 已涵蓋寫入，⚠ 待真實驗證）；寫入方法由 005 自己的連接埠定義，**002 不提供任何寫入** |

- 005 只能讀 `ImportRecord`；不得修改它。
- 重新匯入只會發生在第一輪開始前（001 的準備中與開放加入）；寫回發生在搶答結束後，所以 `ImportRecord` 在寫回期間不會變動。

## 純函式邊界（給架構測試）

- `core/guided_notes_import/` 只能匯入標準函式庫與自己的模組；不得匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`googleapiclient`、`google`、`httpx`，也不得呼叫 `datetime.now` 等系統時鐘。
- `parse(snapshot) -> ParseResult` 的簽章沒有任何時間參數，因為解析根本不需要時間。
