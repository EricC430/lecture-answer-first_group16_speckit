# 服務介面契約：005 與 001／002／003／004

**用途**：Python 程式內的介面，不經過 HTTP。以 `typing.Protocol` 定義（005 自己的連接埠放在 `src/lecture_quiz/app/result_export/ports.py`）。005 對 001～004 **只讀**，也不修改它們的任何程式（研究 R16）。

## 005 使用 001 的介面（已存在，不新增）

| 方法 | 說明 |
|---|---|
| `ActivityService.export_view(code, requester) -> Outcome[ExportView]` | 只限老師；`CANCELLED` 一律拒絕（alignment 2026-11-23 C8）；回傳 `stage`、`question_numbers`、`solved_questions`、`unsolved_questions`、`groups`。005 用它做身分與階段閘門，並取得全部題號（算「未寫入的題」） |
| `ActivityService.get(code) -> Activity \| None` | 取得活動（推送時需要） |
| `ActivityService.resolve_requester(code, token) -> Requester` | HTTP 層把 token 轉成身分 |
| `ActivityService.add_snapshot_extension(extension)` | 註冊快照擴充 `export`（老師版）；擴充函式同步、無副作用 |
| `SyncPublisher.publish(activity)` | 寫回狀態改變後，在鎖外推送最新快照 |
| `Clock.now() -> datetime` | 取得 `started_at`／`finished_at`；核心不使用 |

## 005 使用 002 的介面（已存在，不新增）

| 方法 | 說明 |
|---|---|
| `ImportService.get_import_record(code) -> ImportRecord \| None` | 唯讀：`source`（試算表與工作表識別）、`sheet_title`、`blanks`（每個空格的題號、子編號、目標位置）、`structure`（匯入時結構）、`question_numbers` |
| `SheetsReader.read(code, source) -> Result[SheetSnapshot]` | 以欄位遮罩讀取目前的工作表（唯讀）；失敗為 `ImportRejection`（`NOT_AUTHORIZED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`SHEET_NOT_FOUND`、`READ_FAILED`、`GOOGLE_NOT_CONFIGURED`） |
| `GuidedNotesParser.parse(snapshot) -> ParseResult` | 核心純函式；005 用它對目前的工作表重新辨識（研究 R5） |
| `AuthGateway.is_configured()`、`AuthGateway.start_authorization(code, requester) -> Result[str]` | 005 的重新授權入口直接使用，不經過 `ImportService`（研究 R8） |
| `GoogleAuthGateway.valid_credentials(code) -> Result[Credentials]` | 005 的寫入轉接層透過 `CredentialsProvider` 取得有效憑證（與 002 的 `GoogleSheetsReader` 相同做法）；憑證只在轉接層內部使用 |

- 005 不得修改 `ImportRecord`，也不呼叫 `ImportService` 的任何會改變狀態的方法。
- 002 的 `ImportService._gate` 的階段限制不變（匯入仍只在第一輪開始前）。

## 005 使用 003 的介面（已存在，不新增）

| 方法 | 說明 |
|---|---|
| `SubmissionReader.all_submissions(code) -> tuple[Submission, ...]` | 全部輪次的有效提交，依（`received_at`, `sequence`）排序、不可修改；**含未定案輪次**，005 必須只取已定案輪次的部分 |

## 005 使用 004 的介面（已存在，不新增）

| 方法 | 說明 |
|---|---|
| `RankingReader.finalized_rounds(code) -> tuple[FinalizedRound, ...]` | 已定案輪次依輪次遞增；每筆含各題全部候選的 `rank`、`judged_wrong`、`display_status`，以及 `success_group`。005 **不得重新計算**順位或勝負（spec FR-025） |

## 005 定義的連接埠（由外層轉接層實作）

| 連接埠 | 方法 | 說明 |
|---|---|---|
| `SheetsWriter` | `read_cells(code, source, targets) -> Result[Mapping[CellRef, CurrentCell]]`（`async`） | 以 `spreadsheets.get` 讀取該工作表各目標格的 `userEnteredValue`（研究 R4）；唯讀 |
| | `write_text_cells(code, source, cells: Sequence[tuple[CellRef, str]]) -> WriteResult`（`async`） | 以單一 `spreadsheets.batchUpdate`、每格一個 `updateCells`（`stringValue`、`fields="userEnteredValue"`）寫入；回傳 `SUCCESS`／`FAILED(reason)`／`PENDING`（研究 R3、R6）。**不得**拋 Google 例外給應用層 |

`WriteResult` ＝ `(outcome: OutcomeStatus, reason: AttemptReason | None)`。`Result[T]` 的形狀與 001 的 `Outcome[T]`、002 的 `Result[T]` 相同。

## 005 提供的服務（`ExportService`，給 HTTP 層）

| 方法 | 說明 |
|---|---|
| `await preview(code, requester) -> Result[PreviewView]` | 閘門 → 取已定案成果與 002 記錄 → 讀取來源（結構＋目前內容）→ 核心 `build_snapshot`＋`compare_structure`；不改變任何狀態 |
| `await confirm_write(code, requester, snapshot_id) -> Result[WriteAttempt]` | R1 的順序；結果記入 `ExportStore` 並推送 |
| `await recheck(code, requester, attempt_id) -> Result[WriteAttempt]` | 只讀取，不做結構檢查（R7） |
| `await retry(code, requester, attempt_id) -> Result[WriteAttempt]` | 同一份快照內容，重新結構檢查後寫入 |
| `latest_attempt(code, requester) -> Result[WriteAttempt \| None]` | 頁面重新整理後恢復 |
| `await start_authorization(code, requester) -> Result[str]` | 重新授權入口（R8） |
| `download_csv(code, requester) -> Result[bytes]` | 只讀；UTF-8 加 BOM |
| `snapshot_extension(activity, viewer) -> Mapping[str, object]` | 老師版回傳 `{"export": …}`；學生與沒有嘗試時回 `{}` |

- 服務**不拋業務錯誤**；失敗時 `Result.ok=False`、`rejection` 為 `ExportRejection`（HTTP 狀態與訊息見 [http-api.md](http-api.md)）。只有程式錯誤才拋例外。
- `confirm_write`、`retry` 的 Google I/O 在鎖外（研究 R1）；推送也在鎖外。
- 時間（`started_at`、`finished_at`）一律由注入的 `Clock` 取得，不在核心取得。

## 組裝（`main.py`）

```text
export_service = ExportService(
    activity_service,                 # 001：export_view、快照擴充、Clock
    app.state.import_service,         # 002：get_import_record
    auth_gateway,                     # 002：AuthGateway（重新授權）
    sheets_reader,                    # 002：SheetsReader（重新讀取）
    sheets_writer,                    # 005：SheetsWriter
    app.state.submission_service,     # 003：SubmissionReader
    app.state.ranking_service,        # 004：RankingReader
    ExportStore(),
    app.state.sync_hub,               # SyncPublisher
)
app.state.export_service = export_service
api.include_router(result_export.create_router(app))  # 005，只加這一行
```

測試時 `create_app` 與 002 相同，接受注入的假 `SheetsWriter`（`export_sheets_writer` 參數）；省略時使用真實的 `GoogleSheetsWriter`，共用 002 的 `GoogleAuthGateway`。

## 純函式邊界（給架構測試）

- `core/result_export/` 只能匯入標準函式庫與 `lecture_quiz.core` 內的模組（含 002 的 `core/guided_notes_import` 型別與 004 的 `core/ranking_review` 型別）；不得匯入 `fastapi`、`starlette`、`asyncio`、`time`、`googleapiclient`、`google`、`httpx`，也不得呼叫 `datetime.now`。
- `compare_structure`、`build_snapshot`、`reconcile`、`build_rows`、`render_csv` 的時間資料都來自已保存的 `received_at`，沒有時間參數。
