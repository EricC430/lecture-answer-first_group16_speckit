# Quickstart: 同一瀏覽器共用學生身分與跨分頁同步

**Feature**: [spec.md](spec.md) | **Contract**: [contracts/http-and-sync-changes.md](contracts/http-and-sync-changes.md)

這份是驗證指南，用來證明 007 從頭到尾可用。實作完成後，把下方「驗證紀錄」填上實際執行的日期、指令與結果數字；沒有實際跑過的項目不得勾選。

## 前置條件

- 已依 `docs/DEVELOPMENT.md` 安裝：`py -3.11 -m venv .venv`，再 `.venv\Scripts\python -m pip install -e ".[dev]"`。專案路徑含中文時，依該文件的三種做法處理。
- 啟動系統：`.venv\Scripts\python -m lecture_quiz`。**一律開 `http://127.0.0.1:8000`**，不要用 `localhost`，兩者的 cookie 不共用（research R9）。
- 人工驗證需要兩個獨立的瀏覽器身分，例如 Chrome 一般視窗加上另一個 Chrome 設定檔，或 Chrome 加 Edge。同一個瀏覽器的分頁共用學生身分，不能拿來模擬不同組。
- 匯入題目沿用 002 的流程。只想驗證 007 時，可以用 002 測試夾具裡的學習單。

## 自動化驗證

```powershell
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\mypy
.venv\Scripts\pytest                                   # 預設排除 perf、real_google
.venv\Scripts\pytest -m perf tests/perf/test_sync_latency.py   # SC-006，每組 2 個瀏覽器
```

各 Scenario 對應的測試列在 `tests/SCENARIO_MAP.md` 的 007 區段（由 `/speckit-tasks` 產生）。下列測試**必須走 cookie 路徑**，不帶 Bearer，以證明學生實際使用的路徑可用（research R8）：

- 契約測試：`browser-session` 發 cookie、加入回應不含 `deviceToken`、沒有金鑰時回 `BROWSER_SESSION_REQUIRED`。
- 整合測試：同一個 `TestClient`（同一個 cookie jar）連續 10 次加入不同組號，只建立 1 組（SC-001）；兩個請求同時加入，重複 20 次（SC-002）。
- 瀏覽器端對端：同一個瀏覽器 context 開兩個分頁，從加入畫面實際加入、離開；不同 context 加入不同組。
- 日誌：完整流程的 `caplog` 中金鑰字串出現 0 次（SC-007）。

## 人工驗證步驟（非實作者執行）

以 6 組、1 位老師為例。瀏覽器甲、乙代表兩個獨立的瀏覽器身分。

1. **老師建立活動**：在瀏覽器甲開老師頁，建立組數上限 6 的活動，匯入題目後開放加入，記下活動代碼 K。
2. **US1-AS1**：在瀏覽器甲開學生頁分頁 A，加入第 3 組；再開分頁 B，網址為 `/student.html?code=K`。
   **預期**：分頁 B 直接顯示第 3 組與憑證，沒有加入表單。
3. **US1-AS3**：在瀏覽器甲另開一個不帶代碼的學生頁（`/student.html`），輸入 K 與第 5 組送出。
   **預期**：出現「這個瀏覽器已是第 3 組成員，請先離開本組。」老師看板沒有第 5 組。
4. **US2-AS1**：在瀏覽器乙開兩個不帶代碼的學生頁分頁 C、D，在 C 加入第 5 組。
   **預期**：D 在 2 秒內自動切到第 5 組畫面。
5. **US1-AS2**：用第三個瀏覽器身分（例如 Edge），附上瀏覽器甲畫面上的第 3 組憑證，加入第 3 組。
   **預期**：成功，與甲共用第 3 組身分。
6. **US2-AS2**：在瀏覽器甲的分頁 B 按「離開本組」。
   **預期**：A、B 兩個分頁都在 2 秒內回到加入畫面，並提示「已離開本組」；Edge 仍是第 3 組。
7. **US2-AS3**：老師開輪後，在瀏覽器乙的分頁 D 按「離開本組」。
   **預期**：按鈕停用或請求被拒絕，C、D 都仍是第 5 組。
8. **US2-AS5**：搶答中在 C 送出一題答案。
   **預期**：D 在 2 秒內顯示該題已送出。
9. **US1-AS5**：關閉瀏覽器乙的所有視窗，重新打開並進入 `/student.html?code=K`。
   **預期**：直接恢復第 5 組。
10. **US2-AS4**：關輪、定案後，瀏覽器甲重新加入第 1 組（從未提交）。老師刪除第 1 組。
    **預期**：甲的所有學生分頁在 2 秒內回到加入畫面，並提示「此組已被老師刪除」。
11. **US3**：在瀏覽器甲（老師的瀏覽器）完成步驟 2、6、10 後，於老師頁執行開輪、關輪。
    **預期**：老師操作都成功，老師身分沒有消失。
12. **US2-AS6**：停止後端再重新啟動。
    **預期**：所有學生分頁顯示「活動已失效，請重新建立或加入活動」。
13. **FR-013**：在瀏覽器設定中封鎖 `127.0.0.1` 的 cookie，開學生頁嘗試加入。
    **預期**：出現「瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面」，老師看板沒有新組別。
14. **FR-008**：在開發者工具的 Console 執行 `document.cookie`。
    **預期**：結果不含 `lq_browser`。另外在網址列、畫面與後端終端機輸出中，都找不到金鑰字串。

## 驗證紀錄

| 項目 | 日期 | 執行者 | 指令／操作 | 結果 |
|---|---|---|---|---|
| ruff／format／mypy | | | | |
| pytest（預設） | | | | |
| perf（SC-006） | | | | |
| 人工驗證 1～14 | | | | |
