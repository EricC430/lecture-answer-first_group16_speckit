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
- 曾嘗試暫時移除 INV-1 重跑並發測試作為第二次負對照，但該做法需要還原未 commit 的檔案，被工具權限擋下，因此沒有執行。

### 未改動的措辭

- `NOT_IN_GROUP` 的訊息仍是「這台裝置目前沒有加入任何組別。」（001 與 003 各一處）。spec 沒有要求修改，且不影響行為；若要統一為「這個瀏覽器」，需另外同步相關測試。
