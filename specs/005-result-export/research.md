# Phase 0 研究：005-result-export

**日期**：2026-11-24 | **對應**：[plan.md](plan.md)、[spec.md](spec.md)

每一項寫「決定、理由、考慮過的替代方案」。涉及 Google 行為的項目，來源是**已安裝版本**的程式庫內附文件（憲章與全域規則：版本相關的行為以已安裝版本為準，不憑記憶）：`.venv/Lib/site-packages/googleapiclient/discovery_cache/documents/sheets.v4.json`，`google-api-python-client 2.202.0`，文件 `revision` 為 `20261019`。

**待真實驗證**的假設另列於 R17，對應 spec SC-009；自動化測試以 mock 驗證的行為不等於 Google 真實行為。

## R1　每活動一把鎖與「寫入進行中」旗標（FR-020）

**決定**：`ExportStore` 為每個活動保存一把 `asyncio.Lock` 與一個 `in_progress` 的寫回嘗試。`confirm_write`／`retry` 的順序：

1. 先做階段、身分與快照檢查（同步，不 `await`）。
2. 取得該活動的鎖 → 若已有進行中的嘗試，直接回傳該嘗試（不開始第二次寫入）；否則建立狀態為 `IN_PROGRESS` 的新嘗試 → 釋放鎖。
3. **鎖外**做 Google I/O（重新讀取、結構比對、寫入）。
4. 再取鎖寫回最終狀態 → 釋放鎖 → 推送。

**理由**：Google I/O 可能長達數十秒，不能在鎖內做（會擋住同活動的預覽、CSV 與其他請求）；asyncio 單執行緒下，「檢查有無進行中、建立進行中」之間沒有 `await`，所以不會有兩個請求同時通過檢查。這與 004 的做法（自己的每活動鎖、推送在鎖外）一致。

**替代方案**：整個 I/O 都在鎖內——預覽與 CSV 會被卡住，且違反 FR-022「CSV 不依賴寫回」；用 001 的活動鎖——001 的鎖不可重入，且 005 唯讀，不需要動 001 的狀態。

## R2　成果快照識別（FR-005）

**決定**：`snapshot_id` ＝ 預覽當下「已定案輪次編號」遞增排序後以點連接（例如 `1.2.3`；沒有已定案輪次為空字串，此時預覽直接回「沒有可寫回的結果」，不發識別）。確認請求帶預覽時拿到的 `snapshot_id`；後端以「目前已定案輪次」重新計算識別，不相等就 `409 STALE_SNAPSHOT` 並要求重新預覽。

**理由**：spec FR-005 的條件是「成果集合在預覽之後改變（有新輪次定案）」。已定案輪次不可改判（004 FR-023）、提交不可修改（003 FR-036），所以「輪次編號集合相同」就保證寫入內容相同；用輪次集合最簡單、確定、可測。

**替代方案**：用內容雜湊——新輪次若沒有任何搶答成功者（全被判錯）就不會讓預覽失效，對老師較方便，但與 spec 字面（有新輪次定案就須重新預覽）不一致；為避免兩組行為分歧，採字面解讀。

## R3　寫入 Google 的方式（FR-011～FR-014、FR-019）

**決定**：使用 `spreadsheets.batchUpdate`，每個目標格一個 `updateCells` 請求：

```text
range:  { sheetId, startRowIndex=r, endRowIndex=r+1, startColumnIndex=c, endColumnIndex=c+1 }
rows:   [ { values: [ { userEnteredValue: { stringValue: <答案原文> } } ] } ]
fields: "userEnteredValue"
```

整次寫入的所有目標格放在**同一個** `batchUpdate` 請求。

**依據（來自 `sheets.v4.json`，revision 20261019）**：

- `spreadsheets.batchUpdate`：「Each request is validated before being applied. If any request is not valid then the entire request will fail and nothing will be applied. … it is guaranteed that the updates in the request will be applied together atomically.」——一次請求內全部成功或全部不套用，符合 FR-014（不會「先寫一部分」）與「明確失敗＝確認沒有任何格被改」。
- `ExtendedValue.stringValue`：「Represents a string value. Leading single quotes are not included.」——以 `stringValue` 寫入是字串型別，不會被解析成公式或數字（FR-013）。
- `UpdateCellsRequest.fields`：只列 `userEnteredValue` 時，只更新值，不動格式、合併設定與其他屬性（FR-012）。
- 授權範圍：`spreadsheets.batchUpdate` 的 `scopes` 包含 `https://www.googleapis.com/auth/drive.file`（與 `drive`、`spreadsheets`）。

**理由**：以 `sheetId` 與列欄索引定位，不需要工作表名稱或 A1 字串，所以不受改名影響、也不寫死位置（憲章原則 III）；原子性由 Google 保證，不必自己補償。

**替代方案**：`spreadsheets.values.batchUpdate` 搭配 `valueInputOption=RAW`——需要工作表名稱組 A1 範圍（改名或名稱含特殊字元時易錯）；文件對整批原子性的描述不如 `batchUpdate` 明確。不採用。

## R4　讀取目標格的目前內容（FR-002 覆寫影響）

**決定**：005 自己的轉接層用 `spreadsheets.get`（`ranges=[該工作表]`，`fields` 只要 `sheets(properties(sheetId),data(startRow,startColumn,rowData(values(userEnteredValue))))`）讀取，取出各目標格的 `userEnteredValue`。判定覆寫影響（純函式，見 data-model）：

| 目標格目前內容 | 影響 |
|---|---|
| 沒有 `userEnteredValue` | `EMPTY` |
| `stringValue` 與答案**逐字相同** | `SAME` |
| 其他（不同字串、數字、布林、公式） | `REPLACE`（附原內容的純文字顯示） |

**理由**：002 的 `SheetsReader.read` 只讀 `effectiveValue` 與 `formattedValue`，無法分辨「公式算出 `2`」與「文字 `2`」，也無法分辨數字 `123` 與文字 `123`（寫入字串會改變型別，不能算「內容相同」）。`userEnteredValue` 可以。005 不修改 002 的讀取欄位（避免影響 002 已通過的測試與真實驗證）。

**代價**：預覽與寫入前多一次讀取（一次給 002 的 `read`＋`parse` 做結構比對，一次給 005 的目前內容）。50 題規模的整張工作表讀取各約數百毫秒，可接受；spec SC-008 的 3 秒不含 Google 往返。

## R5　來源結構比對（FR-007～FR-009）

**決定**：服務層以 002 的 `SheetsReader.read(code, source)` 取得目前的 `SheetSnapshot`，用 002 的 `GuidedNotesParser.parse` 重新辨識，再交給 005 核心的 `compare_structure(imported: StructureSnapshot, reparsed: ParseResult)` 逐項比對並分類差異：

| 差異類別 | 比對的項目 |
|---|---|
| `IDENTITY` | `SheetsReader.read` 回 `SHEET_NOT_FOUND`（工作表已不存在）；試算表／工作表識別以 `SourceRef` 為準，不看名稱 |
| `UNRECOGNIZED` | 重新辨識失敗（表頭被刪、題號不連續等；`ParseResult.ok` 為假） |
| `HEADER_POSITION` | `header_number`、`header_answer`、`answer_cols`、`data_start_row` |
| `QUESTION_NUMBER` | `row_numbers`（各資料列對應的題號） |
| `SUB_BLANK` | `answer_cells` 的鍵（題號, 子編號）多了或少了 |
| `ANSWER_CELL` | 同一個（題號, 子編號）的答案格位置不同 |
| `MERGE_RANGE` | `merges`（與表頭列及資料區相交者） |

**理由**：這七類正好涵蓋 OpenSpec「來源結構一致性檢查」列的六項，加上「無法辨識」。002 的 `StructureSnapshot` 本來就是為這個比對設計的（002 `contracts/service-interfaces.md`「給 005」），所以 005 不重寫解析規則。作答格的文字內容不在 `StructureSnapshot` 內，所以「只改作答文字」自然不算差異（FR-009）；工作表只改名也不算（以 `sheetId` 識別）。

**替代方案**：直接用 `==` 比較兩個 `StructureSnapshot`——只能得到「不相等」，無法指出差異類別與位置（FR-008 要求指出）。

**風險與緩解**：寫入答案之後，再次辨識是否仍得到相同結構？002 spec 規定「不論作答格裡是否已有文字，都視為作答格」，但這是 002 的行為，005 以測試保證：兩份版面各做一次「預覽 → 寫入 → 再預覽」，結構必須仍為相符（quickstart 步驟 4、tasks 另列）。

## R6　寫入結果的分類（FR-015、FR-016）

**決定**：轉接層把 Google 的回應與例外分成三類，只回傳類別與原因代碼，不回傳訊息本文：

| 情況 | 類別 | 原因代碼 |
|---|---|---|
| 200 | `SUCCESS` | — |
| 憑證取得失敗（尚未授權、已過期且無法更新），**尚未送出請求** | `FAILED` | `NOT_AUTHORIZED`／`AUTH_EXPIRED` |
| 401 | `FAILED` | `AUTH_EXPIRED` |
| 403、404 | `FAILED` | `PERMISSION_DENIED`（例如沒有編輯權限、檔案被刪除、範圍受保護） |
| 400 | `FAILED` | `REJECTED`（請求被拒，例如目標範圍已不存在） |
| 429 | `FAILED` | `RATE_LIMITED` |
| 5xx、逾時、連線中斷、其他網路例外 | `PENDING` | `UNKNOWN` |

**理由**：`batchUpdate` 有整批原子性，Google 回 4xx 代表請求在驗證階段被拒、「nothing will be applied」，所以可以誠實地說「沒有任何格被改」＝明確失敗。5xx 與逾時無法證明請求有沒有被處理，必須是待確認（FR-016）。429 是流量限制，請求未被處理，歸為明確失敗並提示稍後重試。

**實作細節**：`execute()` 不使用自動重試（`num_retries=0`）——重試由老師手動、結果才可解釋；逾時沿用程式庫預設（`httplib2` 60 秒）；例外由轉接層攔下，不外洩到應用層（沿用 002 `errors.py` 的 `CAUGHT`）。

## R7　重新讀取核對（FR-016，clarify Q2）

**決定**：`recheck` 只讀取（R4 的方式），**不做結構檢查**，直接讀記錄的目標位置，純函式 `reconcile(expected, read_back)`：

- 每個目標格 `userEnteredValue.stringValue` 與預期答案逐字相同 → 該格相符。
- 全部相符 → `SUCCESS`；全部不符 → `FAILED`（原因 `NOT_WRITTEN`）；部分 → `PENDING`，列出不符的格。
- 回應一律附 `cellChecks`（逐格預期與目前內容，純文字），前端另顯示固定提醒「核對只讀取匯入時記錄的位置，不檢查學習單結構是否被改動」。

**取捨（clarify 已接受）**：結構若已位移，核對可能對錯位的格子得出「成功」或「未寫入」。緩解方式是畫面必須逐格顯示內容與提醒，且重試與寫入前的結構檢查不放寬（憲章原則 III 只要求寫回前驗證）。

## R8　重新授權入口（FR-010，clarify Q1）

**決定**：005 的 `ExportService.start_authorization(code, requester)` 先做自己的閘門（活動存在、老師身分、非「已取消」、Google 連線設定齊備），再**直接呼叫 002 的 `AuthGateway.start_authorization`**，不經過 002 的 `ImportService.start_auth`。授權回呼沿用 002 既有的 `GET /api/oauth/callback`（導回 `/teacher.html?code=…&auth=ok|denied|error`）；老師頁的匯出區塊看到 `auth=ok` 後自動重新預覽。

**理由**：002 的階段檢查（只允許準備中與開放加入）在 `ImportService._gate`，而 `AuthGateway` 是沒有階段概念的轉接層連接埠，所以 005 不需要修改 002 任何程式，就能在除「已取消」外的任何階段重新授權。這**修正了 clarify 時的假設**：clarify 記錄寫「需調整 002 授權入口的階段檢查」，研究後發現不需要；spec 的 Clarifications 與 Assumptions 已同步修正。

**授權範圍**：沿用 002 的 `drive.file`，不新增範圍（`batchUpdate` 的文件列出此範圍可用）；是否真的足以寫入老師以 Picker 選定的檔案、重新授權後是否仍能存取該檔案，列入 R17 的真實驗證。

## R9　CSV 格式（FR-024～FR-030）

**決定**：

| 項目 | 做法 | 理由 |
|---|---|---|
| 產生 | Python 標準函式庫 `csv`（`QUOTE_MINIMAL`），在核心以字串產生 | 正確處理逗號、雙引號、換行；核心不需新套件、不碰 I/O |
| 編碼 | UTF-8 並在最前面加 BOM（`utf-8-sig`） | 常見試算表軟體直接開啟時中文不亂碼（FR-027）；不加 BOM 時 Excel 會當成本機編碼而亂碼 |
| 換行 | `\r\n`（RFC 4180） | 常見試算表軟體相容 |
| 欄位 | 繁體中文表頭，順序依 FR-024 | spec 固定 |
| 時間 | `received_at.isoformat(timespec="milliseconds")`（003 保存的是含時區的本機時間，例如 `2026-11-24T20:15:30.123+08:00`） | 含時區、毫秒精度（FR-027）；`received_at` 本來就是 tz-aware（001 `SystemClock`） |
| 布林 | 「是」「否」 | spec 固定 |
| 組別 | 組號數字轉字串 | alignment 2026-11-22 |
| 子空格 | 題組為 `1..n`，單題為空字串 | 與 002 保存的 `sub_index`（單題為 `None`）一致 |
| 文字保護 | 「組別」與「答案」欄位若以 `=`、`+`、`-`、`@`、tab、歸位字元開頭，前面加一個單引號 `'` | OWASP 對 CSV 注入的標準做法；單引號在常見試算表軟體會被當成「文字前綴」而不顯示；系統產生的欄位不加 |
| 檔名 | `quiz-results-<活動代碼>.csv`，`Content-Disposition: attachment`、`Cache-Control: no-store` | 活動代碼不是機敏資料；不放日期（避免核心或轉接層為檔名讀時鐘） |

**替代方案**：保護前綴用 tab（不可見但會留在儲存格內，後續複製貼上污染資料）；用雙引號包住（不能阻止公式）；不加 BOM（中文亂碼）。

## R10　CSV 資料的組合（FR-023、FR-025）

**決定**：服務層取 004 的 `RankingReader.finalized_rounds(code)`（每題全部候選的名次、答錯標記）與 003 的 `SubmissionReader.all_submissions(code)`（答案與接收時間），以（輪次, 題號, 組號）對應後交給核心 `build_rows`。

- 003 的 `all_submissions` **含未定案輪次**，所以只取 `finalized_rounds` 出現的輪次；未定案輪次的提交完全不進核心。
- 子空格欄依 002 `ImportRecord.blanks` 的 `sub_index`（單題 `None` → 空字串）。
- 是否成功＝`rank == 1 and not judged_wrong`；是否被判錯＝`judged_wrong`（搶答失敗不算）；順位＝候選的 `rank`（被判錯為空）。**005 不重新計算**順位（004 FR 與 spec FR-025）。
- 找不到對應提交時（理論上不可能：004 的候選就是 003 的有效提交）**明確失敗**（內部錯誤，通用訊息），不虛構、不略過。

## R11　狀態推送（FR-021）

**決定**：註冊 001 的快照擴充 `export`：只對老師回傳最近一次寫回嘗試的摘要（狀態、格數、原因、快照識別、是否進行中），沒有嘗試時回 `{}`；學生永遠沒有此欄位（資料可見性）。每次嘗試狀態改變後，服務在鎖外呼叫 `SyncPublisher.publish(activity)`，所以其他老師分頁也在 2 秒內更新。快照擴充函式同步、無副作用（`docs/DEVELOPMENT.md` 3.5）。預覽與 CSV 不推送（它們是請求／回應）。

## R12　時間

**決定**：核心不讀時鐘。服務層從注入的 `Clock`（沿用 001）取得 `started_at`／`finished_at` 並存進嘗試；核心只收到已保存的 `received_at`。

## R13　錯誤、訊息與日誌（FR-031、FR-033）

**決定**：`ExportRejection` 列舉＋集中的訊息對照表（`messages.py`）；測試逐項檢查訊息不含 token、授權碼、檔案路徑、堆疊（沿用 002 SC-005 的做法）。Google 例外只對應成代碼，**不記錄**例外訊息本文。日誌只記：活動代碼、端點、嘗試編號、快照識別、目標格數、結果類別、原因代碼；**不記錄**答案、原儲存格內容、試算表網址與標題、token、授權碼。

## R14　前端

**決定**：`teacher.html` 加一個 `<section id="export-section" data-feature="005-result-export">` 與一行 script；邏輯放 `js/result-export.js`（ES module，沿用 `api.js`、`sync.js`、`identity.js`）。所有不可信文字（答案、原儲存格內容、組號、工作表標題）一律 `textContent`。CSV 下載因為需要 `Authorization` 標頭，用 `fetch` 取得 blob 再以暫時網址觸發下載（`api.js` 目前只處理 JSON，005 不改它，另寫一個小函式）。介面固定文字說明保護前綴（FR-029）。

## R15　測試策略（憲章原則 VI）

| 層 | 內容 |
|---|---|
| 核心單元 | 快照與覆寫影響、結構比對各類差異、核對判定、CSV 資料列與跳脫、文字保護、確定性（相同輸入相同輸出）；兩份版面用 `tests/fixtures/guided_notes_layouts.py` 的 `layout_a`、`layout_b` |
| 應用單元 | `ExportService` 搭真實 001 服務、假的 002 讀取器／寫入器、`FakeClock`；併發雙擊、陳舊快照、進行中、重試冪等、核對三種實況 |
| 轉接層單元 | `GoogleSheetsWriter` 以 `HttpMockSequence` 驗證請求形狀（`updateCells`、`stringValue`、`fields`）與 4xx／5xx／逾時分類 |
| 契約／整合 | `tests/contract/result_export/`（端點、錯誤碼、身分）；`tests/integration/test_export_*.py`：兩份版面端到端、寫入後再預覽結構仍相符、CSV 嚴格解析、取消的活動拒絕、日誌不含機敏資訊 |
| 架構 | `tests/architecture/test_core_is_pure.py` 已涵蓋整個 `core/`；`test_static_text_safety.py` 擴充涵蓋 `result-export.js` |
| 真實路徑 | `tests/real_google/test_real_export.py`（`real_google` 標記；缺環境變數明確失敗）＋人工驗證（quickstart） |
| 效能 | `tests/perf/test_export_latency.py`（`perf` 標記）：50 題預覽計算與 CSV 產生 |

預設測試**不呼叫任何真實外部服務**；真實路徑測試必須明確標記並由人手動執行。

## R16　對既有程式的影響

- `main.py`：新增 `_wire_export` 與一行 router 掛載（組裝順序在 004 之後）。
- 001、002、003、004 的程式**不修改**：005 只呼叫它們已提供的唯讀介面（`ActivityService.export_view`／`add_snapshot_extension`、`ImportService.get_import_record`、`SubmissionService.all_submissions`、`RankingService.finalized_rounds`）與 002 的 `AuthGateway`、`SheetsReader`、`GuidedNotesParser`。
- `pyproject.toml`：不新增套件（`google-api-python-client`、`google-auth` 已是核心相依）。

## R17　待真實驗證的假設（對應 SC-009）

自動化測試只能用 mock 驗證請求形狀，下列行為必須以真實試算表（兩份版面）確認，結果記入 `verification.md`：

1. `drive.file` 授權是否足以對老師以 Picker 選定的檔案執行 `spreadsheets.batchUpdate` 與 `spreadsheets.get`（文件的 scopes 列表包含它，但實際行為待驗證）。不足時回報並調整授權範圍（屬 plan 層級的設計，不是 alignment 議題）。
2. 重新授權（新的 OAuth 授權）之後，是否仍能存取先前以 Picker 選定的檔案。
3. `stringValue` 以等號、加號、減號、@ 開頭，以及以單引號開頭、前導零、類日期文字的答案，寫入後讀回是否逐字相同（文件只說「Leading single quotes are not included」是讀取時的表示，寫入時以單引號開頭的字串行為待驗證）。
4. 合併作答格只寫左上角時，其他屬性（格式、合併）不變。
5. 受保護範圍或唯讀權限時，Google 回的狀態碼是否為預期的 403（決定能否歸為明確失敗）。
