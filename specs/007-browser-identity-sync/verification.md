# Verification: 同一瀏覽器共用學生身分與跨分頁同步

**Feature**: [spec.md](spec.md) | **Tasks**: [tasks.md](tasks.md) | **Quickstart（驗證紀錄表）**: [quickstart.md](quickstart.md)

本檔記錄實作期間發現的問題與處理方式（比照 003～005 的「實作問題紀錄」）。測試指令與結果數字記在 quickstart.md 的驗證紀錄表。

## 實作問題紀錄

### P-01：同一瀏覽器重送加入請求時，冪等快取查不到（2026-11-26，T016）

- **現象**：`tests/integration/test_idempotency.py::test_create_join_and_open_round_replayed_20_times` 失敗。同一把瀏覽器金鑰、同一個 `Idempotency-Key` 重送加入，第 1 次回 200，第 2 次起回 409 `ALREADY_IN_GROUP`。
- **原因**：`ActivityService._execute` 以「請求者身分 + Idempotency-Key」作為冪等快取的鍵。007 之前每次加入都是新 token，重送時仍是匿名，鍵相同。007 之後，第一次加入成功後，同一把金鑰在重送時已被解析成該組的 `Device`，鍵不同，所以查不到快取，改成真的執行一次加入，就被 INV-1 或既有檢查拒絕。
- **影響**：學生頁 `api.js` 在網路錯誤時會以同一個 key 重試（001 契約）。若第一次其實已成功，重試會收到「這個瀏覽器已是第 N 組成員」，畫面卻沒有切到本組。
- **處理**：`service.py` 新增 `_idempotency_identity(command)`：`JoinGroup` 以 `command.device_token_hash`（瀏覽器雜湊）為範圍，其他指令維持請求者身分。修正後該測試通過；並在 `tests/integration/test_007_browser_identity.py` 補上不帶 Bearer 的 cookie 路徑重送測試。
- **文件同步**：research R3 補記；plan 實作順序不變。

### P-02：瀏覽器金鑰相關常數與 `browser_key_from` 放在 `common.py`（2026-11-26，T009）

- **原因**：plan 原本把 cookie 常數與 `browser_key_from` 放在 `browser_session.py`，但 `common.request_token` 需要使用它們，而 `browser_session.py` 又要 import `common.annotate_request_log`，會形成循環 import。
- **處理**：常數 `BROWSER_COOKIE_NAME`、`BROWSER_COOKIE_MAX_AGE` 與 `browser_key_from` 放在 `adapters/web/common.py`；`browser_session.py` 只放 `POST /browser-session` 路由。行為與契約不變。plan 的 Source Code 結構已同步。

### P-03：瀏覽器測試的 cookie 注入改用 `Storage.setCookies`（2026-11-26，T029）

- tasks 寫的是 CDP `Network.setCookie`。實作改用瀏覽器層級的 `Storage.setCookies`（帶 `browserContextId`），因為它可以直接指定要寫入哪個 browser context，不必先開分頁。效果相同：該 context 在之後的請求與 WebSocket 握手都帶上 HttpOnly 的 `lq_browser`。
- 既有測試中「另一組學生」的分頁原本用 `page.browser.new_page()`（同一個瀏覽器），改為 `student_tab()`，在新的 browser context 開分頁，避免不同組共用同一把金鑰。

### P-04：FR-013 的瀏覽器測試以「清除 cookie」模擬「瀏覽器沒有保存身分」（2026-11-26，T032）

- CDP 沒有穩定的封鎖 cookie 開關。`tests/browser/test_007_tabs.py::test_missing_cookie_at_join_shows_message` 在頁面取得金鑰後、按加入前以 `Storage.clearCookies` 清掉該 context 的 cookie，驗證畫面提示與「不建立組別」。
- 真的在瀏覽器設定中封鎖 cookie 的情況沒有自動化，留給 quickstart 人工步驟 13。

### P-05：負對照紀錄（2026-11-26，T017）

- 核心 INV-1 的單元測試（`tests/unit/core/test_state_machine_join.py` 的 3 項 007 測試）在實作 INV-1 之前執行，結果 3 failed、16 passed；實作後全數通過。
- 第一次嘗試第二次負對照時，做法需要還原未 commit 的檔案，被工具權限擋下而沒有執行。
- INV-1 commit 之後（2026-11-26，T050 審查後），以 Edit 暫時刪除 `state_machine.py` 的 INV-1 兩行，執行 `pytest tests/integration/test_007_browser_identity.py::test_concurrent_joins_one_wins`：1 failed（兩個加入都成功，`len(winners) == 2`）；再以 Edit 加回，`git diff` 確認檔案與 commit 相同，該測試 1 passed。

### 措辭統一（PR #37 審查建議 3，2026-11-26）

- `NOT_IN_GROUP` 的訊息原本仍是「這台裝置…」（001、003 各一處），已改為「這個瀏覽器目前沒有加入任何組別。」與「這個瀏覽器還沒有加入組別，請先加入組別。」，001、003 的 data-model、001 契約與 research 同步加註。沒有測試斷言這兩則訊息的原文。

### P-06：T041 另外修改了 005 的 quickstart（2026-11-26）

- tasks 只列出 001、003、004、006，實際以 `grep "分頁"` 檢查時發現 `specs/005-result-export/quickstart.md` 的人工驗證也寫「學生至少兩組各一個分頁」，一併改為「各用一個獨立的瀏覽器」。
- 001 的 quickstart 只改前置條件的定義（分頁 A1、A2、B、C 各自是獨立瀏覽器），各步驟沿用原本的代號，不逐列改寫。

### P-07：001 時序圖 PNG 被 PlantUML 預設尺寸上限截斷（2026-11-26，T040）

- 以預設設定重新轉出時，圖高被截在 4096 px，結尾的「結束活動」「重連與重啟」段落消失（檔案從 486 KB 變成 224 KB 才發現）。
- 改以 `java -DPLANTUML_LIMIT_SIZE=8192 -jar plantuml.jar` 重新轉出，高度 4783 px，開啟確認內容完整。之後轉出長的時序圖都要加這個參數。
- 同時檢查所有 PNG：另有 `diagrams/005-result-export-class.png` 寬度剛好 4096 px，可能也被截斷；它不是 007 改的，留給 005 負責人確認。

## 獨立審查（T050，2026-11-26）

由另一個 agent 以唯讀方式審查 `git diff origin/main...HEAD`（審查時 1428 passed）。結論：INV-1 正確、冪等快取不會被其他瀏覽器誤用、金鑰不外洩、既有測試改寫沒有放寬斷言。發現的問題與處理如下。

### P-08：瀏覽器金鑰的 1 天期限從第一次發出起算、不延長（審查第 1 點，已確認）

- **情境**：前一天 10:00 開過學生頁，今天 9:30 上課加入，10:00 cookie 過期；WebSocket 仍連著，但 HTTP 提交改為匿名被拒，重新加入又因頁面沒再呼叫 browser-session 而得到誤導的 `BROWSER_SESSION_REQUIRED`。
- **處理**：`browser-session` 一律重新設定 cookie，已有合法金鑰時沿用同一把、延長 1 天（滑動期限）。學生頁每次載入都會呼叫，所以期限從「最後一次開頁」起算。spec FR-004、契約 §1、research R1、data-model 同步修改。
- **測試**：`tests/contract/test_http_browser_session.py::test_existing_valid_cookie_is_kept_and_refreshed`（修改前 failed，修改後 passed）。

### P-09：加入端點不檢查 Bearer 格式，老師 token 也能當金鑰（審查第 3 點，已確認）

- **情境**：`Bearer x` 可以加入並取得學生身分，違反 FR-008「格式錯誤視為沒有身分」；用老師 token 加入會留下雜湊等於老師的裝置，因為 `resolve_requester` 先比對老師，該裝置永遠無法離開，組號也無法釋放。只有手動偽造請求才會發生，沒有權限提升。
- **處理**：`http_api.join_group` 的 Bearer 必須通過 `is_browser_key`，否則改用 cookie；解析出的請求者是老師時回 `403 TEACHER_CANNOT_JOIN`。契約 §3、§6 同步。
- **測試**：`test_http_join.py::test_malformed_bearer_is_not_a_browser_key`、`test_teacher_token_cannot_join`（修改前 failed，修改後 passed）。

### P-10：還在連線、尚未收到第一份快照的分頁會忽略其他分頁的加入通知（審查第 2 點，可能，時間窗很窄）

- **處理**：`student.js` 收到 `joined` 時改以 `state.synced`（是否已同步成功）判斷，尚未同步成功的分頁一律以通知的代碼重新同步。契約 §7 同步。
- **測試**：時間窗太窄，沒有穩定的自動化重現方式；既有的瀏覽器測試 `test_join_in_one_tab_switches_other_tabs` 仍通過。

### 其他審查項目的處理

- 第 4 點（CSRF 只靠 SameSite=Strict，可能、低）：列入 research R4 的已知限制，不修改。
- 第 6 點（WebSocket「完全沒有 cookie」沒有測到）：`test_ws_sync.py` 拆成 `test_auth_without_token_and_without_cookie_is_unauthorized`（無 cookie）與 `test_auth_with_cookie_of_non_member_is_unauthorized`。
- 第 7 點（Bearer 負面測試缺漏）：見 P-09 的兩項測試。
- 第 8 點（併發測試缺第二次負對照）：已補做，見 P-05。
- 第 10 點（契約與 docstring 寫「依 Bearer 判斷 404／410」，實際一律 404）：契約 §3 與 `http_api.join_group` 的 docstring 改為「一律回 404」。
- 第 11 點（契約 §7 表格多出錯誤代碼列）：移到 §6。
- 第 12 點（001 契約端點表仍列 `deviceToken`）：第 3 列改為 007 之後的回應。`NOT_IN_GROUP` 的「這台裝置」措辭維持不改（見上方「未改動的措辭」）。
- 審查中提到「同一瀏覽器離開本組後重用同一個 Idempotency-Key 會拿到舊快取」：前端每次操作都產生新的 UUID，走不到這條路，不修改。

### 審查修正後的驗證（2026-11-26）

- `ruff check .`、`ruff format --check .`、`mypy`：全部通過（84 source files）。
- 第一次完整執行 `.venv\Scripts\python -m pytest -q`（11:41，耗時 129 秒）：1430 passed、1 failed。失敗的是 `tests/browser/test_pages.py::test_creating_new_activity_clears_previous_activity_screen`，只操作老師頁，不經過學生 cookie 路徑。
- 該測試單獨重跑 1 passed；`tests/browser` 整個目錄連跑 3 次皆 24 passed；第二次完整執行（11:45，耗時 85 秒）1431 passed、0 failed。判斷為機器負載較高時的偶發逾時，與本次修改無關，但沒有找出確切原因，列入觀察。

## PR #37 審查（jacky0407，2026-11-26）

審查者以 worktree 重跑 lint、mypy 與 pytest（1431 passed），沒有找到會擋合併的錯誤，提出 3 項建議：

1. **憲章修訂紀錄漏了 005**：本 PR 也改了 `specs/005-result-export/quickstart.md`（P-06）。已在憲章 v1.2.0 的修訂紀錄補上 005。
2. **正式環境的加入端點接受 Bearer 當瀏覽器金鑰**：見下方 P-11。
3. **`NOT_IN_GROUP` 用詞未同步**：已改，見上方「措辭統一」。

### P-11：加入端點接受 Bearer 當瀏覽器金鑰的取捨（PR #37 審查建議 2）

- **現況**：`http_api.join_group` 先用格式正確的 Bearer，沒有才用 cookie。這條路主要給既有測試使用（`tests/conftest.py` 的 `new_browser`／`post_join`），讓既有的多裝置測試只改輔助函式（research R8）。學生頁本身從不送 Bearer。
- **是否形成繞過**：腳本可以每次換一個 Bearer 加入不同組。但即使拿掉 Bearer 路徑，腳本一樣可以「不保留 cookie、每次重新呼叫 `POST /api/browser-session` 拿一把新金鑰」，達到相同效果。所以 Bearer 路徑沒有讓繞過變得更容易。007 的目標是擋下「同一個瀏覽器開多個分頁」的一般操作，不防寫腳本或換瀏覽器（spec Assumptions 第 1 條），兩者都在已知限制內。
- **決定**：保留。保留的理由是測試相容，而且它不擴大既有限制。若之後要求正式環境只接受 cookie，需要把既有測試全部改成每個瀏覽器一個 `TestClient`（cookie 路徑）。
- **已有的防護**：Bearer 必須通過格式檢查，老師 token 一律拒絕（P-09）；同一把金鑰在同一活動只能是一個組的成員（INV-1）。
