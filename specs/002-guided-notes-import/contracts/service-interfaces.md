# 服務介面契約：002 的連接埠與提供給 005 的介面

**用途**：002 在 Python 程式內的介面，不經過 HTTP。以 `typing.Protocol` 定義，放在 `src/lecture_quiz/app/guided_notes_import/ports.py`。所有跨出應用層的 I/O 都是 `async`；核心的 `parse` 是同步純函式。

## 002 使用 001 的介面（`ActivityGateway`）

契約以 001 的 [service-interfaces.md](../../001-activity-session/contracts/service-interfaces.md) 為準（2026-11-21 與 jacky0407 於 Issue #6 對齊），002 的類別圖已同步：

| 方法 | 002 的用法 |
|---|---|
| `stage(code) -> Stage \| None` | 入口處判斷是否在準備中；活動不存在時為空；用來回 `ROUND_STARTED`／`ACTIVITY_CANCELLED`／`STAGE_NOT_PREPARING` |
| `is_teacher(code, requester) -> bool` | 非老師一律拒絕 |
| `replace_questions(code, requester, question_numbers: tuple[int, ...]) -> Outcome[int]` | 解析成功後呼叫；**只傳題號清單**；成功回傳新 `version`；被拒時 001 的題目完全不變 |

## 002 定義的連接埠（由外層轉接層實作）

| 連接埠 | 方法 | 說明 |
|---|---|---|
| `AuthGateway` | `start_authorization(code, requester) -> str` | 產生 `state` 並回傳 Google 授權網址 |
| | `complete_authorization(state, auth_code) -> CallbackResult` | 驗證 `state`、交換 token 並存入記憶體；回傳活動代碼與結果（`ok`／`denied`／`error`） |
| | `is_authorized(code) -> bool` | 該活動老師是否有有效授權 |
| | `picker_credentials(code) -> PickerConfig \| None` | 回傳 Picker 用的短效 access token、API 金鑰與 App ID |
| `SheetsReader` | `inspect(code, spreadsheet_id) -> Result[SpreadsheetInfo]` | 先以 Drive 確認 `mimeType`，再取得工作表清單 |
| | `read(code, source: SourceRef) -> Result[SheetSnapshot]` | 以欄位遮罩讀取一張工作表並轉成核心的 `SheetSnapshot`（唯讀） |
| `Clock` | `now() -> datetime` | 沿用 001 的 `Clock`；只用於 `state` 有效期限，核心不使用 |

`Result[T]` 的形狀與 001 的 `Outcome[T]` 相同（`ok`、`value`、`rejection`），失敗時 `rejection` 為 `ImportRejection`。轉接層**不得**把 Google 的例外往上拋給應用層（程式錯誤除外）。

## 002 提供的服務（`ImportService`）

| 方法 | 說明 |
|---|---|
| `start_auth(code, requester) -> Result[str]` | 先查階段與身分，再委派 `AuthGateway` |
| `inspect_spreadsheet(code, requester, spreadsheet_id) -> Result[SpreadsheetInfo]` | 不改狀態；`SpreadsheetInfo.auto_select_sheet_id` 在清單恰好一張時為該張識別，否則為 `None`（單一工作表自動選用的判斷在這裡，不在前端） |
| `select_source(code, requester, source: SourceRef) -> Result[SourceSelection]` | 驗證 `sheet_id` 屬於該試算表後才保存；失敗不改舊選擇 |
| `import_sheet(code, requester) -> ImportOutcome` | 持有該活動的匯入鎖；順序見 [research.md](../research.md) R6 |
| `get_import_record(code) -> ImportRecord \| None` | **給 005 使用**：唯讀；回傳最後一次成功匯入的來源、來源映射與匯入時結構 |
| `get_import_summary(code, requester) -> ImportPreview \| None` | 老師頁面重新整理後恢復預覽 |

## 給 005（結果匯出）

| 需求 | 002 提供的方式 |
|---|---|
| 寫回哪些格子 | `ImportRecord.blanks`：每格的題號、子編號與目標（列, 欄） |
| 寫回前比對來源結構（OpenSpec result-export「來源結構一致性檢查」） | `ImportRecord.structure` 與 `source`（試算表與工作表識別）；005 用同一個 `parse` 重新解析當前工作表，與 `structure` 逐項比對 |
| 讀取與寫入 Google | 005 透過同一個 `AuthGateway`／`SheetsReader` 取得授權（授權範圍 `drive.file` 已涵蓋寫入，⚠ 待真實驗證）；寫入方法由 005 自己的連接埠定義，**002 不提供任何寫入** |

- 005 只能讀 `ImportRecord`；不得修改它。
- 重新匯入只會發生在準備中；寫回發生在搶答結束後，所以 `ImportRecord` 在寫回期間不會變動。

## 純函式邊界（給架構測試）

- `core/guided_notes_import/` 只能匯入標準函式庫與自己的模組；不得匯入 `fastapi`、`starlette`、`asyncio`、`socket`、`time`、`googleapiclient`、`google`、`httpx`，也不得呼叫 `datetime.now` 等系統時鐘。
- `parse(snapshot) -> ParseResult` 的簽章沒有任何時間參數，因為解析根本不需要時間。
