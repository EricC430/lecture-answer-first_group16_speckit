# PR 說明草稿（004-ranking-review，不自動發布）

標題建議：`feat: 004 順位計算、判錯重算與定案（US1～US7）(#8)`

## 內容

順位計算（速度／公平模式）、固定題序、整輪重算、判錯與撤銷（退回上一步）、確認定案與歷史鎖定，以及依角色裁切的結果檢視。核心是純函式（`core/ranking_review/`），不依賴網路、框架與系統時鐘。

## 對既有程式的影響

- **001**：`POST /activities/{code}/rounds/current/finalize` 改由 004 提供，本文必須帶 `{"resultVersion": n}`；001 的空定案路由與老師頁舊「確認定案」按鈕已移除（避免重複且舊按鈕會得 400）。`specs/001-activity-session/contracts/http-api.md` 第 8 項與 `service-interfaces.md` 已同步。既有定案測試改用 `finalize_current` helper，斷言未放寬（唯一例外：`test_finalize_contract` 的回應多了 `resultVersion`、`alreadyFinalized`，斷言改為只比對 `version`）。
- **003**：學生頁「已公開的作答」區塊移除（FR-037，改由 004 學生區塊只顯示本組、目前搶答成功者與剛被判錯的前一組）；老師頁同一輪不再重複列出答案。003 的資料與後端沒有改。`test_second_round_keeps_history_and_hides_new_answers` 改提交題二（第 1 輪題一現在真的會被定案為成功）。需 003 負責人確認（T092 尚未完成）。
- **main.py**：新增 `_wire_ranking`（在 003 之後組裝）與 004 router。

## OpenSpec 一致性

沒有新增或偏離 OpenSpec 的功能行為；`docs/openspec-reference/ranking-review/spec.md` 未改（SHA-256 與 README 一致）。Q-23／24／25 已於 `docs/alignment.md` 定案（2026-11-24）。

## 驗證（2026-11-24，皆實際執行）

- `ruff check .` All checks passed；`ruff format --check .` 309 files already formatted；`mypy` Success: no issues found in 68 source files
- `pytest -m "not real_google and not perf"`：1089 passed, 5 deselected
- `pytest -m perf tests/perf/test_ranking_latency.py`：2 passed；6 組最大 112.9 ms（必過 < 2000 ms），20 組最大 702.2 ms（只記錄）
- Scenario 對照：56 個 Acceptance Scenario 中 55 個有自動化測試，US7-AS2（學生畫面實際顯示）為前端畫面行為，無自動化測試，待 T094 人工驗證
- 詳見 `specs/004-ranking-review/verification.md`（含 P-01～ 的實作問題紀錄）

## 尚未完成

- **T094 人工驗證**：需非實作者（jacky0407）依 quickstart 手動步驟在多個瀏覽器分頁走一遍；前端（老師頁按鈕、學生區塊、版本守衛）沒有自動化測試。
- **T092**：與 003 負責人確認學生頁調整。
- 作者不得核准自己的 PR：請先決定由誰核准。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
