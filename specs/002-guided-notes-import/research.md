# Phase 0 研究：002-guided-notes-import

**日期**：2026-11-22 | **對應**：[plan.md](plan.md)、[spec.md](spec.md)

每一項依「決定／理由／考慮過的替代方案」記錄。凡未經真實 Google 驗證的假設，標示「⚠ 待真實驗證」，並彙整在 [plan.md](plan.md) 的「待真實驗證的假設」；真實驗證在 SC-009 完成（見 [quickstart.md](quickstart.md)）。

**官方文件來源（2026-11-22 查證）**：

- [Drive API 的授權範圍](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)：`drive.file` 屬於非敏感範圍，涵蓋使用者「透過 Google Picker 開啟或分享給應用程式」的檔案。
- [Sheets API 的授權範圍](https://developers.google.com/workspace/sheets/api/scopes)：`spreadsheets`、`spreadsheets.readonly` 是敏感範圍；`drive.file` 列為建議的非敏感範圍。
- [`spreadsheets.get`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/get)：接受 `drive.file`；`ranges`、`fields` 參數；設定 `fields` 時 `includeGridData` 會被忽略。
- [`spreadsheets#Sheet`](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/sheets)：`properties`（`sheetId`、`title`）、`data[]`（`startRow`、`startColumn`、`rowData[].values[]`）、`merges[]`（`GridRange`）。
- [Google Picker 總覽](https://developers.google.com/workspace/drive/picker/guides/overview)、[Picker 網頁範例](https://developers.google.com/workspace/drive/picker/guides/web-picker-sample)：網頁以 `PickerBuilder` 搭配 `setOAuthToken`、`setDeveloperKey`、`setAppId`，並可用 `setMimeTypes` 限制檔案類型。

---

## R1. 授權範圍與授權流程

**決定**：

- **授權範圍只要 `https://www.googleapis.com/auth/drive.file`**，不要 `spreadsheets`（敏感）或 `drive`（受限）。
  - Picker 選到的檔案，應用程式才取得該檔案的存取權；匯入（本子功能，唯讀）與寫回（005，寫入）用同一個範圍。
  - 這符合 spec 的「系統只讀取老師選定的那一份」（FR-001）與「不修改試算表」（FR-023，由程式只呼叫讀取方法保證）。
- **授權流程**：後端執行 OAuth 授權碼流程（authorization code flow），不把 client secret 交給瀏覽器。
  1. 老師按「匯入學習單」，前端呼叫 `POST .../import/auth/start`，後端產生一個隨機 `state`（綁定活動代碼、老師身分、過期時間），回傳 Google 授權網址。
  2. 瀏覽器導向 Google；老師同意或拒絕後，Google 導回 `http://localhost:8000/api/oauth/callback?code=…&state=…`（埠號 8000 為專案固定約定，見 quickstart）（Google 允許 localhost 的 http 重新導向）。
  3. 後端驗證 `state`，用授權碼交換 token，**只存在後端記憶體**（依活動代碼），然後導回老師頁面並帶 `?auth=ok|denied|error`。
- **token 不落地、不進日誌**：access token 與 refresh token 只存記憶體（原則 VII、技術限制 3）；重啟後老師需重新授權（符合「活動資料重啟即清空」）。
- **Picker 需要瀏覽器端 access token**：由後端的 `GET .../import/picker-config` 回傳短效 access token 與 Picker 設定，標頭 `Cache-Control: no-store`，只限該活動的老師。這是 Picker 的設計限制，這個 token 只有 `drive.file` 範圍。

**理由**：

- 非敏感範圍不需要 Google 的敏感範圍審核，測試帳號與助教帳號都能直接授權，降低展示風險。
- 後端持有 client secret 與 refresh token，符合「機敏資料不進前端、不進 repo」（原則 V）。

**⚠ 待真實驗證**：`drive.file` 是否足以讓 Sheets API 的 `spreadsheets.get` 讀取 Picker 選到的試算表。官方文件的兩處（Drive 範圍說明、`spreadsheets.get` 的範圍清單）分別支持這一點，但沒有任何一頁同時寫出這個組合，所以要用真實檔案驗證。若失敗，fallback 是改用 `spreadsheets.readonly`（匯入）與 `spreadsheets`（005 寫回）的敏感範圍，並在 OAuth 同意畫面把老師帳號加為測試使用者；改動只在授權範圍常數與 `.env.example`，不影響其他設計。

**考慮過的替代方案**：

- **Google Identity Services 在瀏覽器取得 token 再傳給後端**：後端要信任前端送來的 token，也沒有 refresh token，因此不採用。
- **服務帳戶（service account）**：老師要把檔案分享給服務帳戶，違反「由老師授權」（憲章技術限制 1），因此不採用。
- **`spreadsheets.readonly` 作為預設**：匯入夠用，但 005 寫回還要再升級範圍、讓老師再授權一次，因此不採用。

## R2. 選檔：Google Picker，只允許 Google 試算表

**決定**：

- 前端載入 Google 官方的 `api.js`，呼叫 `gapi.load('picker')`，以 `PickerBuilder` 建立選檔介面：
  - `setOAuthToken(accessToken)`、`setDeveloperKey(apiKey)`、`setAppId(專案編號)` 的值來自 `picker-config`。
  - 檢視用 `DocsView` 並以 `setMimeTypes('application/vnd.google-apps.spreadsheet')` 限制只顯示 Google 試算表。
- **後端不採信 Picker 的過濾**：選定後，前端只把 `spreadsheetId` 傳給後端；後端再向 Drive API 的 `files.get`（`fields=id,name,mimeType`）確認 `mimeType` 是 Google 試算表，否則回 `NOT_A_SPREADSHEET`（FR-005、FR-021）。
- 不提供貼上網址或試算表 ID 的輸入欄（spec Assumptions）。

**理由**：

- Picker 的過濾只是介面提示；使用者可以改請求，所以類型檢查必須在後端（原則 IV、V）。
- 在 `drive.file` 之下，Picker 是取得檔案存取權的唯一正規途徑；這也同時滿足使用者指定的「Picker 選檔」。

**待設定（人工，一次性）**：在 Google Cloud 專案啟用 Picker API、Drive API、Sheets API；建立 OAuth 用戶端（網頁應用程式，授權的重新導向 URI 為 `http://localhost:8000/api/oauth/callback`）與 API 金鑰（先只限制為 Picker API，不設網站限制，見 quickstart）。步驟寫在 [quickstart.md](quickstart.md)。

## R3. Sheets 讀取：官方用戶端程式庫＋最小欄位遮罩

**決定**：

- 以官方的 `google-api-python-client`（Sheets v4、Drive v3）搭配 `google-auth`、`google-auth-oauthlib`。它們是同步程式庫，轉接層以 `asyncio.to_thread` 呼叫，避免阻塞事件迴圈。
- **兩次讀取**，都只用讀取方法：
  1. **檢視（inspect）**：`spreadsheets.get`，`fields=properties.title,sheets.properties(sheetId,title,hidden,gridProperties)`。取得工作表清單（`hidden` 為真者濾除，不列入也不計張數，spec 2026-11-23 澄清），用於「多張要明確選、一張自動選」（FR-002）。
  2. **讀取工作表快照**：先以工作表標題組出 `ranges=['<標題>']`（標題以單引號包住並跳脫），再用 `spreadsheets.get`，欄位遮罩為
     `sheets(properties(sheetId,title,gridProperties),merges,data(startRow,startColumn,rowData(values(effectiveValue,formattedValue))))`。
     因為設定 `fields` 時 `includeGridData` 會被忽略，所以不需要再傳該參數。
- **為什麼要 `effectiveValue`**：它區分 `numberValue` 與 `stringValue`，才能正確判斷「數值 1.0」與「文字『1』」（FR-013）；`formattedValue` 只用於錯誤訊息中引用儲存格內容（當純文字顯示）。
- **轉成純資料**：轉接層把回應轉成核心的 `SheetSnapshot`（見 [data-model.md](data-model.md)）；`rowData` 會省略結尾的空儲存格，並以 `startRow`、`startColumn` 位移，轉換時要還原成絕對的（列, 欄）座標，並保存工作表的列欄總數。
- **合併範圍**：`GridRange` 的列欄索引都是從 0 起算；結束索引是否為「不含」，官方 `Sheet` 頁面只連結到 `GridRange` 而沒有寫明。

**⚠ 待真實驗證**：

1. `GridRange` 的結束索引（`endRowIndex`、`endColumnIndex`）為「不含」。轉接層採此假設，並由一份真實回應 fixture 的合併範圍驗證（見 R9）。
2. 讀取非 Google 試算表（例如被選成 Excel 檔）時，錯誤型態。以 R2 的 Drive `mimeType` 檢查先擋掉，這條路徑只是保險。

**理由**：

- 官方程式庫處理授權 token 更新與重試；`HttpMockSequence` 可在不連網的情況下測試轉接層（原則 VI「Google 一律 mock」）。
- 欄位遮罩讓回應只含需要的欄位，50 題以內的學習單可在 SC-006 的 10 秒內完成。

**考慮過的替代方案**：

- **直接用 `httpx` 呼叫 REST**：依賴少，但 token 更新與錯誤處理要自己寫；規則要求先找現成工具，因此不採用。
- **同步呼叫、不用 `to_thread`**：會在讀取期間阻塞所有活動的同步推送，違反 2 秒同步（技術限制 4），因此不採用。
- **匯出 XLSX／CSV 再解析**：CSV 不含合併範圍、XLSX 等於本地檔案匯入，違反 FR-005，因此不採用。

## R4. 解析演算法（核心純函式）

核心 `parse(snapshot) -> ParseResult` 完全不依賴網路、框架與系統時鐘（技術限制 4）。所有座標以 0 起算的（列, 欄）內部表示，顯示給老師時才轉成「第 N 列、第 X 欄」。

**步驟**：

1. **文字正規化**：儲存格文字以 `str.strip()` 去除首尾空白（涵蓋全形空白 U+3000 與不換行空白）。
2. **找表頭（FR-006、FR-007）**：
   1. 收集所有正規化後文字**完全等於**「題號」的儲存格，與完全等於「作答」的儲存格。不接受同義詞，也不以文字以外的結構猜測。
   2. 其中一種數量為 0 → 缺少該表頭，整份拒絕（指出缺哪一個）。
   3. 同一列同時含「題號」與「作答」稱為一個表頭區塊。恰好一個區塊，且該列只有各一個表頭 → 成功；多於一個區塊、同一列有重複表頭，或「題號」「作答」不在同一列 → 歧義，整份拒絕（FR-007、Q-14）。
   4. 取得：題號欄 = 「題號」儲存格（含合併範圍）的起始欄；作答欄範圍 = 「作答」儲存格的合併範圍所涵蓋的欄（未合併則該欄單一欄）；資料起始列 = 表頭儲存格合併範圍的結束列的下一列。
3. **逐列分類**（資料起始列到工作表最後一列）：
   1. **題號值**：該列題號欄的儲存格；若它落在某個**縱向合併範圍**內而且不是範圍的第一列，繼承範圍左上角的值（FR-011）。範圍外的空白不繼承。
   2. **子編號**：在作答欄範圍內找文字符合 `^[（(][0-9]+[）)]$` 的儲存格（半形或全形括號，半形數字；FR-010、Q-15）。全形數字、括號內夾空白等一律不認，視為無法辨識。
   3. **作答格位置**：
      - 有子編號 → 編號儲存格（含其合併範圍）**右側緊鄰**的儲存格；若它屬於合併範圍，取左上角。右側超出工作表列欄範圍 → 缺少答案格。
      - 無子編號但有題號值 → 單題：取「作答」欄範圍第一欄在該列的儲存格；若屬於合併範圍，取左上角。
   4. **忽略空白列（FR-026）**：沒有題號值也沒有子編號的列一律略過，不影響相鄰與連續性判斷。
   5. 沒有題號值但有子編號 → 孤立子空格錯誤。
4. **分組（FR-009）**：忽略空白列後，**相鄰**且題號值相同的列歸為同一題（涵蓋縱向合併與逐列重複兩種表示）。同一題號再次出現在不相鄰的位置 → 非相鄰重複題號錯誤。
5. **每題內部檢查**：
   - 題組：所有列都要有子編號，且子編號從 1 起連續不重複（FR-014）。
   - 同一題同時有「有子編號的列」和「沒有子編號的列」→ 子編號缺漏錯誤。
   - 單題恰好一個空格。
6. **整體檢查（FR-014、FR-015）**：
   - 題號依出現順序必須是 1, 2, 3 …；偏離處報跳號錯誤。
   - 所有目標儲存格（合併範圍的左上角）不可重複；重複者報目標格重疊並指出兩處。
7. **錯誤收集**：不在第一個錯誤就停，而是收集所有問題一起回報（FR-015：「指出每個問題」）；每個問題含種類、（列, 欄）與老師可照做的修正建議。只要有任何問題，`ok = False`，不產生任何題目（原子，FR-016）。
8. **輸出**：成功時回傳題目清單（題號、空格數、是否題組）、每格的來源映射（題號、子編號、目標（列, 欄））與匯入時結構（表頭位置、涵蓋範圍內的合併範圍、各列的題號值與答案格映射），供 005 比對（FR-024）。題目敘述欄完全不讀取、不保存（FR-008）。

**決定：作答格位置的細節**（spec 沒有逐字規定、屬實作決定，不列入 alignment.md）：

- 單題的答案位置取「作答欄範圍第一欄」那一格（含合併則取左上角）。
- 作答格是否已有文字不影響判定（Q-16）。

**理由**：

- 全部以「表頭＋合併範圍＋文字比對」推導，不含任何固定座標或工作表名稱（原則 III）。
- 錯誤全部收集，老師一次修完，而不是修一個、匯一次。

**考慮過的替代方案**：

- **第一個錯誤就停止**：實作較簡單，但老師要反覆匯入才能修完，因此不採用。
- **結構輔助定位（猜表頭）**：已於 2026-11-21 取消，見 [alignment.md](../../docs/alignment.md)。

## R5. 題號正規化

**決定**：

| 輸入（來自 `effectiveValue`） | 結果 |
|---|---|
| `numberValue` 為正整數值（如 1、1.0） | 該整數 |
| `stringValue` 去除首尾空白後完全符合 `^[0-9]+$` 且值大於 0（如「1」、「01」） | 該整數 |
| 其餘：0、負數、小數（1.5）、「1.」「第1題」「Q1」、全形數字、布林、公式錯誤值 | 非數字題號錯誤 |

- 一律用明確的 ASCII 規則運算式，**不使用 `str.isdigit()` 或 `int()` 的寬鬆行為**，因為 Python 會把全形數字、上標數字當成數字。
- 題號格式錯誤只在**題號欄且位於資料列**才檢查；題號欄空白不算錯誤。

**理由**：FR-013 明確要求數值 1.0 與文字「1」皆為題號 1；規則運算式讓邊界一目了然、可逐條測試。

## R6. 原子匯入、並行與儲存順序

**決定**：

- **順序（FR-027）**：匯入服務依下列順序執行，且整段持有**該活動的匯入鎖**：
  1. 向 001 取得 `stage(code)` 與 `is_teacher(code, requester)`；只有 `PREPARING` 與 `JOINING`（第一輪開始前，alignment 2026-11-23「開放加入」）允許；`CANCELLED` → `ACTIVITY_CANCELLED`；`ROUND_OPEN`／`RESULT_PENDING`／`RESULT_FINAL`／`ENDED` → `ROUND_STARTED`；非老師就拒絕。
  2. 讀取 Sheets（唯讀）→ 解析。任何失敗就回傳，**什麼都不寫**。
  3. 呼叫 001 的 `replace_questions(code, requester, 題號清單)`。被拒絕就整份拒絕，002 保存的資料也不變。
  4. 001 接受後，才以新的 `ImportRecord` **整份取代**舊的（來源映射與匯入時結構）。
- **匯入鎖**：`dict[活動代碼, asyncio.Lock]`，與 001 活動鎖分開。連續快速重複匯入時依序執行，最後成功的一次整份取代前一次（spec Edge Cases）。
- **為什麼不跟 001 的活動鎖合併**：001 的鎖在 `ActivityService` 內，002 不應取用它的內部；匯入含網路讀取，持有 001 鎖會阻擋該活動的其他操作與同步。
- **第 3、4 步之間的窗口**：001 接受後、002 保存前，若程序中斷，記憶體本來就整個消失，不會造成不一致；同一程序內由匯入鎖保證不會交錯。
- **「第一輪開始後鎖定」（FR-020）**：不需要 002 自己維護狀態，直接由 001 的 `stage()` 與 `replace_questions` 的拒絕決定；002 在入口處先查 `stage()` 是為了回傳「搶答已開始」或「活動已取消」等明確訊息。選定來源（PUT source）也受同一檢查。

**理由**：001 契約明定「001 只收題號清單、002 自己保存來源映射」，這個順序同時滿足「001 拒絕時 002 完全不變」與「原則 III 原子匯入」。

**考慮過的替代方案**：

- **先存 002 再通知 001**：001 拒絕時要回復 002 的狀態，容易出錯，因此不採用。
- **在 `replace_questions` 內帶入來源映射**：違反與 jacky0407 在 Issue #6 的約定（001 只收題號清單）。

## R7. 002 保存的資料與生命週期

**決定**：

- **`ImportStore`（記憶體）**依活動代碼保存三類資料，彼此獨立：
  1. `GoogleSession`：該活動老師的 token（R1），重啟即失。
  2. `SourceSelection`：選定的試算表識別、工作表識別、當時的標題（FR-002）。取消選檔不寫入。
  3. `ImportRecord`：最後一次成功匯入的來源、來源映射、匯入時結構（FR-024）。
- **活動刪除或不存在**：002 不主動管理活動生命週期；每次操作先問 001 `stage(code)`，活動不存在就拒絕。記憶體中殘留的資料隨重啟清除，沒有持久化。
- **給 005**：提供 `get_import_record(code) -> ImportRecord | None`（唯讀）與取得有效 Sheets 存取的方式（見 [contracts/service-interfaces.md](contracts/service-interfaces.md)）。

## R8. 錯誤分類與老師可見訊息

**決定**：所有業務失敗用 `ImportRejection` 列舉（代碼）加固定的繁體中文訊息，不拋例外給 HTTP 層；程式錯誤才拋例外，由 HTTP 層轉成不含細節的 500 訊息。

| 代碼 | 對應 spec | 老師看到的重點 |
|---|---|---|
| `NOT_AUTHORIZED` | FR-003 | 尚未授權、未匯入任何題目，提供重新授權 |
| `AUTH_DENIED` | FR-003 | 授權被取消或拒絕 |
| `AUTH_EXPIRED` | FR-003 | 授權已失效，請重新授權（不匯入半份資料） |
| `PERMISSION_DENIED` | FR-003 | 沒有該檔案的讀取權限，請調整權限或重新選檔 |
| `NOT_A_SPREADSHEET` | FR-005 | 請選擇 Google 試算表 |
| `SHEET_NOT_FOUND` | FR-002 | 所選工作表不存在，請重新選擇 |
| `SOURCE_NOT_SELECTED` | FR-002 | 尚未選好試算表與工作表 |
| `READ_FAILED` | FR-004 | 暫時無法讀取，請稍後重試（含逾時、配額） |
| `VALIDATION_FAILED` | FR-015 | 附錯誤清單（列、欄、原因、修正建議） |
| `ACTIVITY_NOT_FOUND`／`NOT_TEACHER` | FR-025 | 找不到活動／沒有權限 |
| `ROUND_STARTED`／`ACTIVITY_CANCELLED`／`STAGE_NOT_PREPARING` | FR-020、FR-025 | 搶答已開始題目不可更動／活動已取消／目前階段不可匯入 |
| `GATEWAY_REJECTED` | FR-027 | 階段或身分剛好改變，請重新整理 |

- 訊息文字集中在一個對照表（`messages.py`），測試逐項檢查「不含 token、授權碼、路徑、堆疊」（FR-022、SC-005）。
- 儲存格引用（表頭文字、題號文字）在訊息中以純文字處理：後端不做 HTML 組字，前端以 `textContent` 輸出（原則 V）。引用長度截斷在 40 字元以內，避免過長儲存格洗版。

## R9. 測試策略與固定資料（fixture）

**決定**：

- **核心單元測試**：以一個測試輔助函式，把「文字矩陣＋合併範圍清單」轉成 `SheetSnapshot`，用表格驅動方式寫案例。每個案例標明 `Scenario: USn-ASm` 或 `Edge: <名稱>`（原則 VI）。
  - 至少兩份**版面不同**的合法學習單（原則 III、SC-003）：A = 課程範本版面（表頭在第 4 列、題號在 B 欄、作答在 G 欄）；B = 整體移位且工作表更名的版本，另含單題與題組混合。
  - 負面學習單：SC-004 列出的九種缺陷各至少一份，另加近似錯誤對照（格式對但內容有缺陷，例如表頭存在但題號跳號）。**先寫負面案例、確認它們失敗，再寫實作**。
- **應用層測試**：用 `FakeSheetsReader`、`FakeAuthGateway`、`FakeActivityGateway`（行為由 001 契約定義，含階段與老師判定）驗證順序、原子性、鎖、拒絕不改狀態（US4-AS5、US6、並行重複匯入）。
- **轉接層測試**：以 `googleapiclient.http.HttpMockSequence` 餵入回應 JSON，驗證欄位遮罩、座標還原、`GridRange` 轉換、錯誤對應（401／403／404／429／逾時）。
- **HTTP 契約測試**：FastAPI `TestClient`，依 [contracts/http-api.md](contracts/http-api.md) 驗證狀態碼與訊息格式。
- **架構測試**：沿用 001 的 `tests/architecture/test_core_is_pure.py`，把 `core/guided_notes_import/` 納入掃描。
- **預設測試不呼叫真實 Google**；真實路徑用明確標記 `@pytest.mark.real_google` 的手動整合測試，並在測試內指定使用真實轉接器；缺少環境變數時**明確失敗**而不是跳過。
- **兩類 fixture 要分清楚**：
  1. **手寫 fixture**：核心單元測試的矩陣，檔頭標明「手寫、依 OpenSpec 與課程範本描述」。
  2. **真實回應 fixture**：真實路徑驗證時，由一支擷取腳本把真實 `spreadsheets.get` 回應去識別化後存成 JSON，再讓「走入口」的測試（JSON → 轉接層 → 解析）重播。擷取前，這類測試不存在，**不得宣稱入口路徑已驗證**。

## R10. 設定與機敏資料

**決定**：

- 以環境變數提供：`GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_API_KEY`（Picker）、`GOOGLE_APP_ID`（Cloud 專案編號）、`OAUTH_REDIRECT_URI`；repo 只提供 `.env.example`（原則 V）。
- **空字串視為未設定**：缺任何一項時，匯入相關端點明確回「尚未設定 Google 憑證」（給開發者看的訊息寫在日誌與 quickstart，給老師看的不含變數名稱），**不退回離線路徑、不假裝成功**。
- 日誌（`logging`、INFO、stdout）只記：活動代碼、操作、結果代碼、題數與格數；**不記** token、授權碼、client secret、試算表標題或儲存格內容。
- 設定值（授權範圍常數、`state` 有效期限）各只定義在一個地方。

## R11. 前端

**決定**：

- 沿用 001 的原生 JavaScript：`teacher.html` 只加一個「匯入學習單」區塊，邏輯放在 `src/lecture_quiz/adapters/static/js/import.js`（依 jacky0407 於 Issue #5 的約定）。
- 流程：按鈕 → `auth/start` → 導向 Google → 回來後 `?auth=ok` → `picker-config` → Picker → `inspect`（取得工作表清單與後端決定的 `autoSelectSheetId`，有值就自動 `PUT source`）→ 老師選工作表 → `POST import` → 顯示預覽或錯誤清單。
- 所有後端或試算表來的文字一律用 `textContent`；錯誤清單用表格呈現（列、欄、原因、修正建議）。
- 重新整理頁面時以 `GET .../import` 恢復「已匯入 N 題、M 格」的畫面。

**理由**：與 001 一致，免建置，助教 clone 即可跑。

**考慮過的替代方案**：框架式前端——不採用，原因同 001 的 R7。
