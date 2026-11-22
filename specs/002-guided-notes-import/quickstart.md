# 快速驗證指南：002-guided-notes-import

**用途**：實作完成後，證明 002 端到端可用的執行與人工驗證腳本。本檔只記錄「怎麼驗證、預期結果」；**實際執行的日期、指令與結果數字要在執行當下填入下方的紀錄表，沒有跑過就保持空白，不得預填**（憲章原則 VI）。

**目前狀態（2026-11-22）**：尚未實作，下列所有驗證都還沒有執行過。

## 前置條件

1. 001 的骨架 PR（jacky0407 計畫另開；截至 2026-11-22 尚未建立）已合併到 main，002 分支已從 main 接續（見 [plan.md](plan.md)「相依與時程」）。
2. Python 3.11 以上，已依 `pyproject.toml` 安裝相依（含開發相依）。
3. **Google Cloud 一次性設定**（只有真實路徑驗證需要，自動化測試不需要；約 10～15 分鐘）。

   > **固定值約定**：本專案本機一律用埠號 **8000**、主機名稱 **`localhost`**。下面所有步驟都用這組**實際數值**，**不要輸入帶 `<` `>` 的占位符**（例如 `<port>`），否則 Google 會回「重新導向無效：結尾須為公用頂層網域」。這個錯誤的原因就是 Google 把 `<port>` 當成網域名稱的一部分。
   >
   > | 用途 | 要填的完整值 |
   > |---|---|
   > | 授權的重新導向 URI | `http://localhost:8000/api/oauth/callback` |
   > | `.env` 的 `OAUTH_REDIRECT_URI` | 與上一列**完全相同**（含 `http`、埠號、路徑，結尾不加斜線） |
   > | 瀏覽器開啟系統的網址 | `http://localhost:8000/teacher.html`（**不要用 `127.0.0.1`**，否則瀏覽器儲存的老師身分與回呼網址不是同一個來源，授權回來後會找不到老師身分） |
   > | 啟動後端的指令 | `uvicorn lecture_quiz.main:app --host 127.0.0.1 --port 8000`（確切模組路徑以 001 骨架為準） |
   >
   > 依 [Google 官方文件](https://developers.google.com/identity/protocols/oauth2/web-server)：重新導向 URI 一般要用 HTTPS，但 **localhost 是例外，可以用 `http`**；URI 要與設定**完全一致**（`http`／`https`、大小寫、結尾斜線）；網域不得是原始 IP（localhost 例外）。

   1. 開啟 [Google Cloud Console](https://console.cloud.google.com/)，頂端專案選單 → **新增專案**，名稱自訂（例如 `lecture-quiz`）。建立後確認頂端已切換到這個專案，並到專案首頁記下**專案編號**（一串數字，不是專案 ID），這就是 `GOOGLE_APP_ID`。
   2. **啟用三個 API**：左側選單 → API 和服務 → 程式庫，搜尋並分別按「啟用」：**Google Sheets API**、**Google Drive API**、**Google Picker API**。
   3. **設定 OAuth 同意畫面**：API 和服務 → OAuth 同意畫面（新版介面名稱為「Google Auth Platform」，下面的分頁為品牌、目標對象、資料存取、用戶端）。
      - 應用程式名稱隨意、使用者支援電子郵件與開發人員聯絡資訊填你的 Gmail。
      - 目標對象（User type）選**外部**，發布狀態維持**測試中**。
      - 在「**測試使用者**」把**用來驗證的 Google 帳號**（你自己與 jacky0407 的帳號）加進去；不在清單內的帳號授權時會被擋。
      - 「資料存取」新增範圍 `.../auth/drive.file`（非敏感）。
   4. **建立 OAuth 用戶端**：用戶端（或 API 和服務 → 憑證）→ 建立用戶端／建立憑證 → OAuth 用戶端 ID → 應用程式類型選**網頁應用程式**。
      - 「已授權的重新導向 URI」按「新增 URI」，貼上 `http://localhost:8000/api/oauth/callback`。**這個欄位是重新導向 URI，不是「已授權的 JavaScript 來源」，兩個不要填錯。**
      - 「已授權的 JavaScript 來源」可以留空（授權碼流程在後端交換 token，不需要）。
      - 建立後會顯示**用戶端 ID**與**用戶端密鑰**：分別是 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`。密鑰只貼到本機 `.env`，**不要貼到聊天、Issue、PR 或任何追蹤的檔案**。
   5. **建立 API 金鑰**（Picker 用）：憑證 → 建立憑證 → API 金鑰，這就是 `GOOGLE_API_KEY`。建議先只把「API 限制」設為 **Google Picker API**，**先不要設網站（HTTP 參照網址）限制**：Picker 會在 Google 網域的畫面裡載入，網站限制設錯會出現「API developer key is invalid」。真實驗證通過後若要再收緊，再加限制並重新驗證（此項列入 [plan.md](plan.md)「待真實驗證的假設」）。
   6. 若授權時看到「這個應用程式未經 Google 驗證」：測試中的應用程式正常會出現，按「進階」→「前往（不安全）」即可；`drive.file` 是非敏感範圍，不需要送審。
4. 複製 `.env.example` 為 `.env`（`.env` 已被 `.gitignore` 排除），填入 `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_API_KEY`、`GOOGLE_APP_ID`、`OAUTH_REDIRECT_URI`。**任何一項是空字串都視為未設定**，匯入端點會明確回 `GOOGLE_NOT_CONFIGURED`。

## A. 自動化驗證（預設不呼叫真實 Google）

在 repo 根目錄執行（指令定案於 001 的 research R3 與憲章技術限制 2）：

```text
ruff check .
ruff format --check .
mypy src
pytest -m "not real_google"
```

預期：全部通過；`pytest` 的結果數字要記錄到下方紀錄表。測試分類與對應見 [research.md](research.md) R9；每個測試的 docstring 第一行標明 `Scenario: USn-ASm` 或 `Edge: <名稱>`，tasks 階段會產生對照表。

**檢查測試真的跑到東西**：`pytest -m "not real_google" -v` 的輸出要看到核心解析、應用層、轉接層（`HttpMockSequence`）、HTTP 契約、架構純度測試各自有項目；某一類是 0 筆就是測試壞了，不是通過。

## B. 真實路徑驗證（SC-009，合併前必做）

**準備兩份版面不同的真實 Google 試算表**（用你自己的 Google 帳號建立，不要把連結或內容貼進 repo、Issue、PR）：

| 試算表 | 內容 | 預期匯入結果 |
|---|---|---|
| 版面 1（課程範本，題組＋單題混合） | 前兩題各兩個子空格、後兩題各一格；前兩題題號縱向合併；表頭在第 4 列 | 4 題、6 格；題 1：2、題 2：2、題 3：1、題 4：1；第二個子空格有位置、沒有位置落在編號格 |
| 版面 2（整體移位＋工作表更名＋多張工作表） | 同樣內容移到別的起始列欄；工作表改名；試算表另有一張無關工作表 | 與版面 1 相同的題數與格數；每格位置對應新位置 |

另備一份**單題範本**（六題、作答格橫向合併）與一份**有缺陷**的試算表（例如題號跳號）。

**操作步驟**（老師頁面，後端以 `uvicorn` 本機啟動；活動先用 001 建好，停在準備中）：

| # | 操作 | 預期 | Spec／SC |
|---|---|---|---|
| 1 | 按「匯入學習單」，在 Google 授權畫面按**取消** | 回到頁面，說明「尚未授權、未匯入任何題目」並提供重新授權；活動題目不變 | US1-AS3 |
| 2 | 再按一次，同意授權 | 回到頁面，顯示已授權 | US1-AS1 |
| 3 | 在選檔畫面按取消 | 維持原狀，沒有留下半途來源 | US1-AS5 |
| 4 | 選一份 Google 文件或 PDF（若 Picker 允許）| 被拒並說明「請選擇 Google 試算表」 | US1-AS6、FR-005 |
| 5 | 選版面 2 的試算表 | 列出工作表，要求明確選一張 | US1-AS1 |
| 6 | 選正確的那張工作表，按匯入 | 預覽「4 題、6 格」與每題格數；記錄從按下確認到看見預覽的秒數 | US3-AS1、US5-AS1、SC-006 |
| 7 | 重新整理頁面 | 預覽恢復 | US5 |
| 8 | 改選版面 1 再匯入 | 整份取代，結果相同、無舊題目殘留 | US5-AS2、SC-003 |
| 9 | 匯入單題範本 | 6 題、6 格 | US2-AS1、SC-002 |
| 10 | 匯入有缺陷的試算表 | 整份拒絕，訊息指出列、欄、原因；先前成功的匯入結果不變 | US4、SC-004 |
| 11 | 在匯入完成後，檢查原試算表 | 內容完全沒有被修改（可看版本記錄） | FR-023、SC-007 |
| 12 | 用 001 開第一輪後，再嘗試更換試算表、重新匯入 | 兩者都被拒絕，訊息「搶答已開始」，來源映射與既有提交不變 | US6、SC-008 |
| 13 | 在老師 token 以外的情況（例如另開無痕視窗沒有老師身分）呼叫匯入 | 被拒絕 | FR-025 |

**同時檢查**：

- 後端日誌（stdout）整段搜尋 token、授權碼、client secret、試算表標題，不得出現。
- 錯誤畫面不得出現堆疊、檔案路徑或憑證。
- 若步驟 5～6 因為「`drive.file` 讀不到 Picker 選到的試算表」而失敗，這是 [plan.md](plan.md) 列出的待驗證假設不成立；依 [research.md](research.md) R1 的 fallback 改用敏感範圍，並在紀錄表註明。

**擷取真實回應 fixture**：真實驗證通過後，用擷取腳本把版面 1、版面 2 的真實 `spreadsheets.get` 回應去識別化（刪除標題、帳號、檔案 ID），存成 `tests/fixtures/real/*.json`，並補上走入口的測試（JSON → 轉接層 → 解析），確認 `GridRange` 結束索引的假設。擷取前這類測試不存在，不得宣稱入口路徑已驗證。

## 紀錄表（實際執行後填寫；未執行請保持空白）

| 日期 | 執行者 | 指令或操作 | 結果數字 | 備註 |
|---|---|---|---|---|
| | | `ruff check .` | | |
| | | `ruff format --check .` | | |
| | | `mypy src` | | |
| | | `pytest -m "not real_google"` | passed／failed／總數： | |
| | | 真實路徑 B-1～B-13（版面 1、版面 2） | | |

- **實作者**：EricC430。**非實作者人工驗證**：jacky0407（執行 B 區並簽名，記錄日期與結果）。
