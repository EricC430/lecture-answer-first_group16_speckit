# Implementation Plan: 同一瀏覽器共用學生身分與跨分頁同步

**Branch**: `feature/007-browser-identity-sync`（Issue 建立後改名為 `feature/<issue>-007-browser-identity-sync`） | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-browser-identity-sync/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/007-browser-identity-sync-component.puml`](../../diagrams/007-browser-identity-sync-component.puml)
- 類別圖：[`diagrams/007-browser-identity-sync-class.puml`](../../diagrams/007-browser-identity-sync-class.puml)
- 時序圖：[`diagrams/007-browser-identity-sync-sequence.puml`](../../diagrams/007-browser-identity-sync-sequence.puml)

本 plan 的模組與流程都依這三張圖命名。2026-11-26 plan 階段已依設計更新三張圖（加入 `browser-session` 先發金鑰、核心的鎖內雙重檢查、Bearer 優先的身分來源）並重新轉出 PNG。實作需要偏離時，先改圖。

## Summary

把 001 的學生「裝置身分」從「每個分頁一份（sessionStorage）」改成「每個瀏覽器一份（HttpOnly cookie）」。這樣同一個瀏覽器在同一個活動只能代表一個組別，所有分頁的身分變化也會在 2 秒內同步。

技術做法：

- **cookie 就是裝置 token**（research R1、R2）：
  - HttpOnly cookie `lq_browser` 保存 256 位元的瀏覽器金鑰。
  - `hash_token(金鑰)` 直接作為 001 `activity.devices` 的鍵。
  - 001 的資料模型、`resolve_requester`、003 的 `submit`、離開與刪除時「依雜湊關閉連線」都不必改。同一瀏覽器的所有分頁共用同一個雜湊，所以離開本組或組別被刪除時，001 既有的推送本來就會通知所有分頁。
- **先發金鑰再加入**（R3）：
  - 新增 `POST /api/browser-session`，學生頁載入時呼叫，只有在沒有金鑰時才發。
  - 加入端點不發金鑰；沒有金鑰時回 `BROWSER_SESSION_REQUIRED`（FR-013）。
  - 核心 `_join_group` 加一條鎖內檢查：裝置雜湊已存在就回 `ALREADY_IN_GROUP`。同一瀏覽器同時送出的加入請求只會成功一個（FR-007）。
- **身分來源**（R4、R5）：
  - HTTP 是「Bearer 優先，否則 cookie」。老師頁帶 Bearer，所以老師與學生在同一個瀏覽器時互不干擾（US3）。
  - WebSocket 的 auth 訊息可以不帶 token，這時改讀握手請求的 cookie。
- **加入的跨分頁通知**（R6）：用 `BroadcastChannel("lq-identity")`，只傳活動代碼。停在加入畫面的分頁收到後，以 cookie 開始同步。

## Technical Context

**Language/Version**: Python 3.11+（後端）；原生 JavaScript ES modules（前端，沿用 001）

**Primary Dependencies**: FastAPI／Starlette（`Response.set_cookie`、`Request.cookies`、`WebSocket.cookies`）；瀏覽器 `BroadcastChannel`。不新增套件。

**Storage**: 後端只用記憶體（憲章原則 VII），不保存金鑰本身，只保存它在各活動的雜湊；瀏覽器端用 HttpOnly cookie。

**Testing**: pytest；契約與整合測試用 FastAPI `TestClient`（每個「瀏覽器」用獨立的 client 與 cookie jar）；瀏覽器端對端測試用既有的 CDP 測試架構（`tests/browser/`），每個瀏覽器用獨立的 browser context；perf 測試沿用 `tests/perf/test_sync_latency.py`。

**Target Platform**: Windows 本機，後端只監聽 `127.0.0.1:8000`；瀏覽器為 Chrome／Edge 最新版。

**Project Type**: Web 應用（單一 Python 套件 + 靜態前端，沿用 001 的三層結構）。

**Performance Goals**: 身分變化在同一瀏覽器其他分頁 2 秒內反映（FR-010）；老師加上 6 組、每組 2 個瀏覽器時，狀態變更 2 秒內反映（SC-006，沿用 001 R2）。

**Constraints**:

- 金鑰不得出現在網址、畫面、回應本文、錯誤訊息或日誌（FR-008、SC-007）。
- 核心維持純函式（架構限制）：核心不知道 cookie 的存在，只多一條以 `issued.device_token_hash` 判斷的規則。
- 學生端不得自行附上身分（FR-008）。

**Scale/Scope**:

- 改動集中在 001 的轉接層與前端：`common.py`、`http_api.py`、`ws_sync.py`、新增 `browser_session.py`、`student.js`、`identity.js`、`round-submission.js`。
- 核心改一個函式（`_join_group`）與一則訊息；服務層改 `join` 的參數。
- 測試輔助函式約 66 處取用 `deviceToken`，改由輔助函式統一處理（R8）。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致 | spec 已標註 activity-session 的 Requirement 與 Scenario。「裝置改以瀏覽器為單位」屬於新增行為，已記入 `docs/alignment.md` 2026-11-26，經 EricC430 回報已與 OpenSpec 組核對。cookie、BroadcastChannel 屬於實作方式，不列入 alignment | 通過 |
| II 圖表設計優先 | 三張圖在 specify 階段產出，plan 階段依設計更新並重新轉出 PNG（2026-11-26，已開啟檢視，沒有文字重疊）；本 plan 的命名都取自圖。implement 後要驗證程式碼與圖一致（tasks 列為最後的任務） | 通過 |
| III Guided Notes 動態定位 | 007 不涉及匯入與寫回，002、005 的程式不改 | 不適用 |
| IV 後端為唯一事實來源 | 組別歸屬仍由後端依雜湊判定（FR-005）。「是否已有身分」改由後端回答，前端不再自行判斷。同時加入的競爭在鎖內由核心決定。`browser-session` 與加入請求都可安全重送（冪等鍵沿用 001） | 通過 |
| V 資料可見性與安全 | 金鑰採 HttpOnly、SameSite=Strict，不進回應本文與日誌（R10，有測試）；錯誤訊息不含金鑰或憑證；竄改、過期的金鑰一律視為匿名；可見性規則（學生只看本組）不變 | 通過 |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 對應至少一個測試，tasks 會更新 `tests/SCENARIO_MAP.md`。cookie 路徑有專門的測試，不帶 Bearer（R8，避免輔助函式走 Bearer 造成假綠燈）。不涉及 Google。合併前由非實作者依 quickstart 人工驗證 14 項並記錄 | 通過（待執行） |
| VII 簡單與本機運作 | 不新增套件、資料庫或持久化；只在本機執行。新增一個端點與一個瀏覽器內的通知頻道，是滿足 FR-007、FR-010 的最小做法（R3、R6） | 通過 |
| 技術限制 1「以多個瀏覽器分頁模擬各組學生」 | 與 007 衝突：同一瀏覽器的分頁共用身分。依 R11 做 PATCH 修訂 v1.1.1，改成「以多個瀏覽器（或設定檔、無痕視窗）模擬」 | 通過（含修訂任務） |
| 技術限制 2 程式碼風格 | 公開函式要有型別提示與 docstring；ruff、format、mypy 都要通過 | 通過（待執行） |
| 技術限制 3 日誌 | 只用 `logging`；不記錄金鑰；`browser-session` 只記錄方法、路徑與狀態碼 | 通過 |
| 技術限制 4 效能與架構 | 2 秒同步沿用 001 的 WebSocket 推送；核心純函式，相依只由外層指向核心（`tests/architecture/test_core_is_pure.py` 持續檢查） | 通過 |

**Post-design re-check（Phase 1 後）**：

- data-model 的 INV-1 位於核心純函式內，不依賴 cookie 或框架。
- contracts 的新增錯誤代碼 `BROWSER_SESSION_REQUIRED` 只在轉接層判定。
- 沒有新的違反項目，Complexity Tracking 不需要填寫。

## Project Structure

### Documentation (this feature)

```text
specs/007-browser-identity-sync/
├── spec.md
├── plan.md                         # 本檔
├── research.md                     # R1～R11
├── data-model.md                   # 瀏覽器金鑰、DeviceIdentity 語意、INV-1
├── quickstart.md                   # 自動化與人工驗證步驟、驗證紀錄表
├── contracts/
│   └── http-and-sync-changes.md    # 對 001 http-api.md、sync-websocket.md 的修改
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks 產生
```

### Source Code (repository root)

```text
src/lecture_quiz/
├── core/activity/
│   ├── state_machine.py        # 修改：_join_group 加入 INV-1（issued.device_token_hash 已存在 → ALREADY_IN_GROUP）
│   └── results.py              # 修改：ALREADY_IN_GROUP 訊息改為「這個瀏覽器已是第 N 組成員…」，改用 issued 雜湊找組號
├── app/activity/
│   ├── secrets_gen.py          # 新增：new_browser_key()、is_browser_key(value)（格式檢查）
│   └── service.py              # 修改：join() 改收 browser_key，不再 new_token()；JoinedDevice 移除 token
├── adapters/web/
│   ├── browser_session.py      # 新增：POST /api/browser-session、cookie 常數與 browser_key_from(request)
│   ├── common.py               # 修改：新增 request_token dependency（Bearer 優先，否則 cookie）
│   ├── http_api.py             # 修改：Token 改用 request_token；加入時要求金鑰、回應移除 deviceToken、404/410 只看 Bearer
│   └── ws_sync.py              # 修改：auth 的 token 可省略或為 null，這時改讀 websocket.cookies
├── adapters/static/js/
│   ├── identity.js             # 修改：移除 device 相關函式（老師部分不變）
│   ├── student.js              # 修改：載入時確保金鑰、以 cookie 同步、首次 INVALID_TOKEN 安靜回到加入畫面、BroadcastChannel
│   └── round-submission.js     # 修改：不再附 token，改以「是否已連線」判斷
└── main.py                     # 修改：掛上 browser_session router

tests/
├── conftest.py、integration/conftest.py、integration/ranking_world.py、browser/conftest.py、perf/*.py
│                               # 修改：「新瀏覽器」輔助函式（清 cookie jar → browser-session → 讀 Set-Cookie → Bearer）
├── unit/core/                  # 新增：INV-1 的純函式測試（同雜湊第二次加入被拒、不建組、不發憑證）
├── contract/test_http_browser_session.py   # 新增：發 cookie、屬性、冪等、本文為空
├── contract/test_http_join.py              # 修改：回應不含 deviceToken、BROWSER_SESSION_REQUIRED、404 只看 Bearer
├── contract/test_ws_sync.py                # 修改：auth 不帶 token 時讀 cookie
├── integration/test_007_browser_identity.py # 新增：只走 cookie 路徑的 US1～US3、SC-001、SC-002、SC-004、SC-005、SC-007
├── browser/test_007_tabs.py                # 新增：同一個 context 兩個分頁的加入、離開同步；不同 context 不同組
└── SCENARIO_MAP.md                          # 修改：加入 007 區段

specs/001-activity-session/{spec.md,research.md,contracts/*.md,quickstart.md}  # 加註「由 007 修訂」
specs/{003,004,006}-*/quickstart.md          # 多分頁模擬多組的步驟改成多瀏覽器
diagrams/001-activity-session-*.puml         # 學生畫面與 API 的身分來源加註 007
.specify/memory/constitution.md              # PATCH v1.1.1：技術限制 1 的措辭（R11）
CLAUDE.md                                    # 專案現況加入 007 一段
```

**Structure Decision**：沿用 001 的三層結構（core／app／adapters）。cookie 只出現在 `adapters/web`，金鑰的產生與格式檢查放在 `app/activity/secrets_gen.py`，與既有的 token 產生器放在一起。核心只多一條以雜湊判斷的規則，不知道 cookie 的存在。

## 實作順序與風險

1. **核心與服務層**（INV-1、`join` 參數）→ 單元測試先寫、先看到失敗。
2. **轉接層**（`browser-session`、`request_token`、加入、WebSocket auth）→ 契約測試。
3. **測試輔助函式**（R8）→ 跑一次既有的完整測試，確認數字與改動前相同。改動前先記下目前 `pytest` 的通過數，作為對照。
4. **前端**（`student.js`、`identity.js`、`round-submission.js`）→ 瀏覽器端對端測試。
5. **文件與圖表同步**（001 文件、quickstart、憲章 PATCH、CLAUDE.md）→ 程式碼與圖的一致性檢查。

| 風險 | 影響 | 對策 |
|---|---|---|
| 輔助函式改成 Bearer 後，既有測試沒有走到 cookie 路徑 | 學生的實際路徑壞掉卻沒人發現 | 007 的整合測試與瀏覽器測試一律不帶 Bearer（R8）；人工驗證步驟 2～14 走實際頁面 |
| 學生頁第一次載入時，兩個分頁的 `browser-session` 互相覆蓋 | 先加入的分頁身分變成孤兒 | 金鑰發出前不啟用加入按鈕；列為已知限制（R3） |
| `localhost` 與 `127.0.0.1` 的 cookie 不共用 | 人工驗證時以為同步壞了 | quickstart 與啟動訊息統一使用 `127.0.0.1`（R9） |
| 老師頁在同一個瀏覽器、但沒有老師 token 時，請求會帶著學生 cookie | 老師頁誤拿到學生快照 | 老師頁沒有老師 token 時本來就不呼叫老師 API（001 US1-AS2）；整合測試補一個「無 Bearer 的老師頁請求只得到學生權限」的案例 |

## Complexity Tracking

> Constitution Check 沒有需要說明理由的違反項目，本節不填寫。
