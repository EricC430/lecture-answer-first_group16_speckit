# Research: 同一瀏覽器共用學生身分與跨分頁同步

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-11-26

本文件記錄 007 的技術決策。現況依據 2026-11-26 `origin/main`（`cd90d1b`）的程式碼：

- 學生裝置 token 由 `ActivityService.join` 以 `new_token()` 產生，在加入回應的 `deviceToken` 欄位交給頁面。
- 頁面把 token 存在 `sessionStorage["device:{code}"]`，所以每個分頁是一台裝置（001 research R5）。
- HTTP 請求用 `Authorization: Bearer`；WebSocket 連線後的第一則 `{"type":"auth","token":...}` 帶 token。
- 後端以 `hash_token(token)` 作為 `activity.devices` 的鍵。

## R1：瀏覽器身分的保存方式

- **Decision**：使用一個 HttpOnly cookie `lq_browser`。值為 `secrets.token_urlsafe(32)`（43 字元，256 位元亂數），稱為「瀏覽器金鑰」。屬性如下：
  - `HttpOnly`
  - `SameSite=Strict`
  - `Path=/`
  - `Max-Age=86400`（1 天，spec FR-004）
  - 不設 `Secure`：系統只在本機以 HTTP 執行，設了瀏覽器就不會保存。
  - 不設 `Domain`：只對發出 cookie 的主機有效。
- **Rationale**：
  - spec Clarifications 2026-11-26 已限定使用 HttpOnly cookie。
  - `SameSite=Strict` 讓其他網站發出的請求不會帶上這個 cookie，不需要另外做 CSRF token。後端也沒有開 CORS，帶 JSON 本文的跨站請求本來就會被預檢擋下。
  - 有效期 1 天，涵蓋一堂課，也符合「關閉瀏覽器後仍保留」（spec Clarifications 第 2 題）。
- **Alternatives considered**：
  - localStorage：頁面程式碼讀得到，clarify 時已否決。
  - 每個活動各一個 cookie（`lq_device_{code}`）：見 R2，金鑰不需要依活動區分。
  - session cookie（不設 Max-Age）：瀏覽器關閉就消失，與 clarify 第 2 題衝突。

## R2：瀏覽器金鑰與 001 裝置 token 的關係

- **Decision**：瀏覽器金鑰直接取代 001 的「裝置 token」。
  - `ActivityService.join` 不再自己產生 token，改用呼叫端傳入的瀏覽器金鑰，`hash_token(瀏覽器金鑰)` 就是 `activity.devices` 的鍵。
  - 同一個金鑰可以在不同活動各有一筆 `DeviceIdentity`，符合 spec Edge Case「同一瀏覽器加入不同活動」。
  - 金鑰不依活動區分，整個瀏覽器只有一把。
- **Rationale**：
  - 這樣 001 的資料模型、`resolve_requester`、`resolve_device`、003 的 `submit(code, device_token, …)`、離開本組與刪除組別時「依 token 雜湊關閉連線」（`WebSocketHub.disconnect_device`）都不必改，只要換掉 token 的來源。
  - 同一瀏覽器的所有分頁共用同一個雜湊。離開本組或組別被刪除時，001 原本就會把該雜湊的所有連線關掉，並送出 `unauthorized`（`LEFT_GROUP`／`GROUP_DELETED`）。因此 US2-AS2、US2-AS4 的跨分頁同步不必另外實作。
- **Alternatives considered**：
  - 金鑰只當「瀏覽器編號」，加入時另發裝置 token 存在服務端，以「金鑰 → token」對應。這會多一層對應表，沒有帶來任何好處。

## R3：先發金鑰再加入（同時加入的競爭，FR-007、SC-002）

- **問題**：如果在第一次加入時才發金鑰，同一瀏覽器的兩個分頁同時第一次加入，兩個請求都不帶 cookie，會各拿到一把新金鑰，結果建立兩個組別，違反 FR-007。
- **Decision**：新增 `POST /api/browser-session`。學生頁載入時先呼叫它：
  - 請求已帶格式正確的 `lq_browser`：不動 cookie，回 204。
  - 請求沒有帶，或格式不對：發一把新金鑰並設定 cookie，回 204。回應本文是空的，金鑰只出現在 `Set-Cookie`。
  - 加入端點**不發**金鑰。請求沒有瀏覽器金鑰（例如瀏覽器封鎖了 cookie）時回 400 `BROWSER_SESSION_REQUIRED`，訊息為「瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面」。這同時滿足 FR-013。
- **核心的雙重檢查**：
  - 服務層在取得活動鎖**之前**就解析了請求者，所以兩個同時送出的加入請求都會被解析成 `Anonymous`。
  - 因此 `JoinGroup` 指令新增欄位 `device_token_hash: str | None`，由服務層填入 `hash_token(瀏覽器金鑰)`。核心 `_join_group` 除了原本「請求者已是成員」的檢查，再加一條：`command.device_token_hash` 已在 `activity.devices` 時，回 `ALREADY_IN_GROUP`。
  - 這條檢查在鎖內執行，是純函式，第二個請求一定會被拒絕。
  - 拒絕訊息的函式 `_describe_group_rejection(reason, command, activity)` 拿不到 `issued`，所以改從 `command.device_token_hash`（沒有時才用 `command.actor.token_hash`）找出所屬組別，訊息為「這個瀏覽器已是第 N 組成員，請先離開本組。」（spec US1-AS3）。同時加入的落敗者也能看到組號。
  - `issued.device_token_hash` 仍保留，與 `command.device_token_hash` 相同；`_join_group` 在兩者不一致時拋 `ValueError`（服務層的程式錯誤，不是使用者輸入）。
- **冪等範圍**（2026-11-26 實作時發現，verification P-01）：加入的 Idempotency-Key 以瀏覽器雜湊為範圍，而不是請求者身分；否則第一次加入成功後的重送，會因為請求者已變成組員而查不到快取。
- **仍存在的競爭**：同一瀏覽器第一次載入時，若兩個分頁在同一個往返時間內同時呼叫 `browser-session`，可能各拿一把金鑰，後到的覆蓋先到的。學生頁要等這個呼叫完成才啟用加入按鈕，而人輸入組號需要好幾秒，所以實際上不會在加入前互相覆蓋。這列為已知限制，不影響 SC-002：SC-002 量的是頁面載入完成後的同時加入。
- **Alternatives considered**：
  - 由頁面產生金鑰：頁面讀得到金鑰，違反 FR-008。
  - 在靜態頁回應中設定 cookie：要把學生頁從 StaticFiles 改成自訂路由，改動更大，競爭問題也一樣存在。

## R4：請求者身分的來源與優先順序

- **Decision**：新增 FastAPI dependency `request_token`，取代 `http_api.Token` 原本使用的 `bearer_token`。所有 import `Token` 的子功能（002～005）都自動套用。規則如下：
  1. 有 `Authorization: Bearer` 時用它。老師頁一律帶老師 token；測試也用這個方式（見 R8）。
  2. 沒有時讀 `lq_browser` cookie，格式不符就當成沒有。
  3. 兩者都沒有時為 `None`，即匿名。
- **Rationale**：
  - 老師頁在同一個瀏覽器時，請求也會自動帶著學生的 cookie。Bearer 優先，老師操作就不會被解析成學生（US3、FR-009）。
  - 學生頁不再附上任何 token（FR-008），只靠 cookie。
- **活動不存在時回 404 還是 410**（`unwrap` 依「是否帶 token」決定）：
  - 現在學生的每個請求都會帶 cookie，若照原規則，輸入打錯的代碼也會變成 410「活動已失效」。
  - 因此**加入端點**判斷 404／410 時只看 Bearer，打錯代碼仍回 404「找不到這個活動代碼」。
  - 其他端點與 WebSocket 維持原規則：帶 cookie 而活動不存在時回 410／`gone`。
  - 但網址帶錯誤的 `?code=`（例如貼錯連結）時，學生頁也會收到 `gone`。為了不把「打錯代碼」顯示成「活動已失效」，學生頁依「這個分頁是否曾經同步成功」區分：沒有同步成功過 → 顯示加入畫面與「找不到這個活動代碼，請確認後再輸入。」；同步成功過 → 顯示「活動已失效」（spec Edge Case、FR-011）。判斷只在前端畫面，後端回應不變。
- **Alternatives considered**：cookie 優先於 Bearer。老師與學生在同一瀏覽器時，老師操作會被當成學生操作，違反 US3。

## R5：WebSocket 驗證

- **Decision**：
  - 第一則 auth 訊息的 `token` 改為可省略或 `null`。省略時改讀握手請求的 `lq_browser` cookie（`websocket.cookies`）。
  - 同源的 WebSocket 握手會自動帶上 cookie，前端學生頁送出 `{"type":"auth"}` 就可以。
  - 老師頁仍送 `{"type":"auth","token":"<老師 token>"}`。
  - 兩者都沒有，或解析成匿名時，與現行相同：送 `unauthorized`（`INVALID_TOKEN`）並關閉連線。
  - `type` 不是 `auth`，或 `token` 不是字串也不是 null 時，仍以 `CLOSE_BAD_FIRST_MESSAGE` 關閉。
- **Rationale**：保留「連線後第一則訊息驗證」的流程，只放寬 token 的來源，老師端完全不受影響。

## R6：跨分頁通知（加入，FR-010、US2-AS1）

- **問題**：離開與刪除已經由 R2 的「同雜湊的所有連線」處理。但加入之前，其他分頁還在加入畫面，沒有任何連線，cookie 改變也不會通知它們。
- **Decision**：
  - 使用 `BroadcastChannel("lq-identity")`。學生頁加入成功後送出 `{"type":"joined","code":"<活動代碼>"}`，不含任何身分內容。
  - 其他分頁收到時，如果目前沒有連線（停在加入畫面），就以該活動代碼開始同步，並把網址改成 `?code=`。
  - 已經連著某個活動的分頁不受影響。例如還在看另一個已結束活動的結果，就不會被切走。
  - 瀏覽器不支援 `BroadcastChannel` 時不啟用這個通知，該分頁重新整理後一樣能恢復身分（FR-004）。Chrome、Edge、Firefox、Safari 15.4 以上都支援。
- **Rationale**：
  - 同一瀏覽器的分頁之間通知，只發生在瀏覽器內，不經過後端。
  - 訊息只帶活動代碼，不洩漏身分（FR-008）。
  - 收到通知的分頁仍然透過 cookie 向後端驗證，後端還是唯一的事實來源（憲章原則 IV）。
- **Alternatives considered**：
  - `storage` 事件：需要在 localStorage 寫一個標記，效果相同但比較迂迴。
  - 加入畫面每秒輪詢：浪費資源，而且延遲取決於輪詢間隔。

## R7：學生頁載入流程與「本來就沒有身分」的情況

- **Decision**：
  1. 學生頁載入時先 `POST /api/browser-session`，完成前停用加入按鈕。
  2. 網址帶 `?code=` 時直接以 cookie 開始同步，前端不再判斷自己有沒有 token，因為 cookie 讀不到。
  3. 第一次連線就收到 `unauthorized`（`INVALID_TOKEN`）時，表示這個瀏覽器在該活動沒有身分：安靜地顯示加入畫面，不顯示錯誤。
  4. 之後才收到的 `unauthorized`（例如 `LEFT_GROUP`、`GROUP_DELETED`），維持現在的提示。
  5. 加入時收到 `409 ALREADY_IN_GROUP`，而且送出的活動代碼就是這個活動：顯示該訊息，並以該代碼開始同步，切換到本組畫面（spec US1-AS3、US1-AS5）。代碼不同時（例如另一個活動）不會發生，因為身分以活動為單位。
  6. 第一次連線就收到 `gone`：見 R4，顯示「找不到這個活動代碼」而不是「活動已失效」。
  7. 「加入其他活動」按鈕（活動已結束或取消時）只重設畫面。後端的組別身分保留，因為已結束的活動不需要也不能離開本組，不必清 cookie。
  8. `identity.js` 移除 `getDeviceToken`、`setDeviceToken`、`clearDeviceToken`。`currentIdentity()` 改成只回傳活動代碼與「是否已連線」。003 的 `round-submission.js` 送出答案時不再附 token。
- **Rationale**：頁面讀不到 cookie，只能把「有沒有身分」交給後端判斷。後端本來就是唯一的事實來源（憲章原則 IV），所以這樣做沒有問題。

## R8：既有自動化測試的相容做法

- **現況**：測試輔助函式（`tests/conftest.py` 的 `join_group`、`tests/integration/conftest.py`、`ranking_world.py`、`tests/browser/conftest.py`、各 perf 測試；以 `grep -rn --include=*.py deviceToken tests` 計，共 12 個檔案、31 處）從加入回應取出 `deviceToken`，再以 Bearer 帶入。
- **Decision**：
  - 輔助函式模擬「一個新瀏覽器」的流程：
    1. 清空 TestClient 的 cookie jar。
    2. 呼叫 `POST /api/browser-session`。
    3. 從回應的 `Set-Cookie` 讀出金鑰。
    4. 帶著它加入。
    5. 之後照舊以 Bearer 帶入。後端在 Bearer 與 cookie 都有時以 Bearer 為準（R4）。
  - 這樣既有的多裝置測試只要改輔助函式，不必逐一改寫。
- **避免假綠燈**：上面的做法走的是 Bearer，**不是**學生頁實際使用的 cookie 路徑。所以 007 另外新增測試，明確**不帶 Bearer**：
  - 契約與整合測試：每個「瀏覽器」用獨立的 `TestClient`，各有自己的 cookie jar。
  - 瀏覽器端對端測試：每組學生用獨立的瀏覽器 context（CDP `Target.createBrowserContext`），身分由頁面實際加入取得。
  - 這些測試驗證 cookie 路徑從頭到尾可用。
- **瀏覽器測試的身分注入**：`tests/browser/test_pages.py` 目前把 token 寫進 `sessionStorage`。改成在該組的瀏覽器 context 以 CDP `Network.setCookie` 寫入 `lq_browser`，模擬「這個瀏覽器先前已加入」。另外有一個測試完全不注入，從加入畫面實際加入（US1、US2）。

## R9：網址主機名稱一致

- **Decision**：
  - cookie 依主機名稱區分，`localhost` 與 `127.0.0.1` 對瀏覽器來說是兩個網站。系統啟動時印出的網址固定是 `http://127.0.0.1:8000`（`python -m lecture_quiz`）。
  - 007 的 quickstart 與各子功能人工驗證步驟統一使用這個網址。用另一個主機名稱開啟，就等於另一個瀏覽器，這記為已知限制。
- **Alternatives considered**：設定 cookie `Domain`。瀏覽器不接受對 IP 位址或 `localhost` 設定跨主機的 Domain，做不到。

## R10：日誌與錯誤訊息不得出現金鑰（FR-008、SC-007）

- **Decision**：
  - `common.py` 的請求日誌只記錄方法、路徑、狀態碼與 `annotate_request_log` 的欄位，不記錄標頭或 cookie。007 不新增任何記錄 cookie 的程式。
  - 測試以 `caplog` 擷取一輪「建立 → 開放加入 → 加入 → 提交 → 離開」的完整日誌，確認瀏覽器金鑰字串出現 0 次。
  - 也確認所有回應本文都不含金鑰：加入回應移除 `deviceToken` 欄位，`browser-session` 回應本文為空。
- **注意**：不要直接用 `uvicorn` 啟動。access log 雖然不記錄 cookie，但這是專案既有的規定（CLAUDE.md），007 沿用。

## R11：憲章「技術限制與範圍」第 1 節的措辭

- **問題**：憲章寫「以多個瀏覽器分頁模擬老師與各組學生」。007 之後，同一瀏覽器的分頁共用學生身分，不能再用多個分頁模擬多組。
- **Decision**：
  - 已於 2026-11-26 修訂為 v1.2.0（獨立 commit `ca29a0c`）：技術限制 1 改為「以多個瀏覽器（或瀏覽器設定檔、無痕視窗）模擬各組學生；同一瀏覽器的分頁共用同一個學生身分」。
  - 同一次修訂也處理 `/speckit-analyze` 的 D2：子功能拆分表原本只有 001～005，且「調整拆分必須走修訂程序」，因此把 006、007 列入表中，並說明 006 起是延伸子功能。新增章節內容屬 MINOR，所以版本為 1.2.0 而不是 1.1.1。
  - 依使用者 2026-11-26 指示直接處理，不另開 PR，在 007 的 PR 說明中交代。
- **Rationale**：避免憲章與 007 的行為互相矛盾，影響評分時的一致性檢查。
