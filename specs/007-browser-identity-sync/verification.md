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
