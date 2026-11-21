# Implementation Plan: 活動建立、組別加入與階段同步

**Branch**: `feature/5-001-activity-session` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-activity-session/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/001-activity-session-component.puml`](../../diagrams/001-activity-session-component.puml)
- 類別圖：[`diagrams/001-activity-session-class.puml`](../../diagrams/001-activity-session-class.puml)
- 時序圖：[`diagrams/001-activity-session-sequence.puml`](../../diagrams/001-activity-session-sequence.puml)

本 plan 的模組、類別與流程都依這三張圖命名；設計需要偏離時，先改圖並重新轉出 PNG。

## Summary

本子功能提供搶答系統的骨架：

- 老師建立活動並取得獨占控制權。
- 學生以「組名 + 6 碼組別憑證」加入，多裝置同組，重新整理後恢復身分；也可以在非搶答中離開本組，老師可以刪除沒有提交的空組。
- 一套 6 階段狀態機，管理開輪、關輪只一次、定案、結束與取消。
- 所有畫面在 2 秒內同步。

技術做法：

- **核心**：`ActivityStateMachine`、`InputRules`、`SnapshotView` 是純函式，輸入不可變的 `Activity`、操作與呼叫端傳入的 `now`，輸出新狀態或拒絕原因。
- **服務層**：`ActivityService` 以「每個活動一把 `asyncio.Lock`」序列化操作，並以 `Idempotency-Key` 去重。
- **外層**：FastAPI 提供 HTTP 操作；WebSocket 只負責推送依角色裁切的完整快照。
- **前端**：原生 JavaScript 靜態頁。

## Technical Context

**Language/Version**：Python 3.11 以上

**Primary Dependencies**：

- 執行：FastAPI、uvicorn[standard]（含 WebSocket 支援）、pydantic v2（隨 FastAPI 安裝）。
- 開發：pytest、pytest-timeout、httpx（`TestClient`）、websockets（效能測試客戶端）、ruff、mypy。

**Storage**：無。活動只存在後端記憶體，重啟即清空（原則 VII）。

**Testing**：pytest，分成 unit、architecture、contract、integration、perf（`-m perf`）五類。時間以 `FakeClock`／`ManualScheduler` 控制（研究 R4）。

**Target Platform**：Windows 10／11 本機；後端只監聽 `127.0.0.1`；以 Chrome 或 Edge 的多個分頁模擬老師與各組。

**Project Type**：單一專案的 Web 應用。FastAPI 後端同時提供靜態前端，不需要前端建置。

**Performance Goals**：老師加上 N = 6 組（每組 2 條連線）時，狀態變更推送到所有連線的最大延遲小於 2 秒（研究 R2）。

**Constraints**：

- 單一 uvicorn worker。
- 核心不得依賴網路、框架與系統時鐘。
- 日誌只用 `logging`（`INFO`、stdout），不記錄 token 或憑證。
- 不使用資料庫。

**Scale/Scope**：一堂課 1～數個活動，每個活動數十組、數十題；兩個頁面（老師、學生）；11 個 HTTP 端點、1 條 WebSocket。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 檢查項 | 結果 | 依據 |
|---|---|---|
| **I 跨組行為一致** | ✅ 通過（附條件） | spec 的 Traceability 涵蓋 6 條 Requirement 與 10 個 Scenario。Q-04、Q-06、Q-08、Q-09／Q-33 的提案，以及「離開本組」「刪除空組」兩項新增行為，已記入 `docs/alignment.md`，但 OpenSpec 組尚未確認。**plan 依提案設計；合併實作前必須取得確認**，受影響的設計點集中列在下方，方便修改 |
| **II 圖表生成** | ✅ 通過 | 以三張圖為藍圖。本 plan 為圖表補上 `code` 參數，以及給 003／004／005 的介面方法，已同步更新類別圖並重新轉出 PNG。tasks 必須有「程式碼與圖表一致性驗證」任務 |
| **III Guided Notes 動態定位** | ✅ 通過（不適用解析） | 本子功能不解析學習單。`replace_questions` 只接收 002 成功匯入的題號；被拒時，既有題目完全不變（[service-interfaces](contracts/service-interfaces.md)）。不需要「兩份版面學習單」測試 |
| **IV 後端為唯一事實來源** | ✅ 通過 | 身分由後端 token 雜湊判定（研究 R5）；階段、關輪只一次由鎖與 `round.closed` 雙重保證（研究 R6）；重送以 `Idempotency-Key` 去重；狀態機是確定性純函式 |
| **V 資料可見性與安全** | ✅ 通過 | 學生快照只含本組資料，連組數都不給（[data-model](data-model.md)）；所有輸入由 `InputRules` 在後端驗證，失敗時不改變狀態；錯誤只回 `code` 與可修正的 `message`；組名以 `textContent` 輸出；token 只保存雜湊、比對用 `compare_digest`、不寫入 log |
| **VI 驗收情境驅動測試** | ✅ 通過 | 每個 Acceptance Scenario（US1～US7，共 44 個）至少對應一個測試，docstring 標明 `Scenario: USn-ASm`。本子功能不使用 Google，因此不需要 mock 或真實路徑驗證。非實作者人工驗證腳本見 [quickstart](quickstart.md)，包含 2 秒同步與重啟失效 |
| **VII 簡單與本機運作** | ✅ 通過 | 只用記憶體、單一 process、只監聽 `127.0.0.1`。前端不用框架與建置工具。開發用的 seed API 預設關閉，002 合併後移除（見 Complexity Tracking） |
| **技術限制 1 堆疊** | ✅ 通過 | Python 3.11 以上 + FastAPI；Windows 本機；只監聽 localhost |
| **技術限制 2 程式碼風格** | ✅ 通過 | PEP 8 由 Ruff 檢查；型別提示與 docstring 由 Ruff 規則 ANN、D 加上 mypy 檢查（研究 R3）。**lint 與格式化工具已定案，需以修訂程序補回憲章**（Next Actions） |
| **技術限制 3 日誌** | ✅ 通過 | `logging.basicConfig(level=INFO, stream=sys.stdout)`；請求 log 的欄位白名單見 [http-api](contracts/http-api.md) |
| **技術限制 4 效能** | ✅ 通過 | N = 6，有自動化效能測試與人工延遲顯示（研究 R2）；不自訂組數上限 |
| **技術限制 4 架構（NON-NEGOTIABLE）** | ✅ 通過 | 核心放在 `src/lecture_quiz/core/`，只依賴標準函式庫的資料型別。`tests/architecture/test_core_is_pure.py` 以 `ast` 自動檢查（研究 R4）；相依方向為 `adapters → app → core` |

**Phase 1 設計完成後重新檢查**：結果相同，沒有新增違規。唯一需要說明的例外，是開發用 seed API，列在 Complexity Tracking。

## 受待確認提案影響的設計點

組內開會或 OpenSpec 組回覆後，若結論與提案不同，只需修改下列位置；其餘設計不受影響。

| 提案 | 受影響的設計點 | 修改範圍 |
|---|---|---|
| Q-04 老師身分同瀏覽器分頁共用 | 研究 R5：老師 token 存在 `localStorage`；`TeacherIdentity` | 前端儲存位置、`static/js/identity.js`；若改為跨裝置，需新增「老師身分轉移」流程 |
| Q-06 憑證由本組裝置與老師可見 | 學生與老師快照中的 `credential` 欄位；[sync-websocket](contracts/sync-websocket.md) | `SnapshotView`；若改成只有老師可見，只要從學生快照移除這個欄位 |
| Q-08 倒數與模式獨立、1～3600 秒 | `InputRules.validate_countdown`；`RoundRules.countdown_seconds` | 單一函式與其測試 |
| Q-09／Q-33 取消與結束分開、取消後不能匯出 | `Stage.CANCELLED`；`export_view` 拒絕 `CANCELLED` | 狀態機的一列轉移；若改成取消後可以匯出，只要修改 `export_view` |
| 離開本組（搶答中禁止） | `LeaveGroup` 操作；HTTP #4；`NO_GROUP_SWITCH_DURING_ROUND` | 若對方不同意，刪除該操作、端點與前端按鈕 |
| 刪除空組 | `DeleteGroup` 操作；HTTP #5；`Group.has_submissions`；003 的 `mark_group_submitted` | 若對方不同意，刪除該操作與端點；`has_submissions` 可以保留給 005 使用 |

## Project Structure

### Documentation (this feature)

```text
specs/001-activity-session/
├── spec.md
├── plan.md              # 本檔
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1（也是人工驗證腳本）
├── contracts/
│   ├── http-api.md
│   ├── sync-websocket.md
│   └── service-interfaces.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2（/speckit-tasks 產生）
```

### Source Code (repository root)

```text
pyproject.toml                      # 相依、ruff、mypy、pytest 設定
src/lecture_quiz/
├── main.py                         # 建立 FastAPI app、logging 設定、掛載路由與靜態檔
├── core/                           # 純函式層：不得匯入 app、adapters、fastapi、asyncio、time
│   └── activity/
│       ├── models.py               # Stage、Activity、Group、Round、RoundRules、TeacherIdentity、DeviceIdentity
│       ├── commands.py             # Command 各型別、Actor、FinalizeOutcome
│       ├── results.py              # Transition、RejectionReason、IssuedSecrets
│       ├── state_machine.py        # ActivityStateMachine.apply / is_deadline_passed
│       ├── input_rules.py          # InputRules
│       └── snapshot_view.py        # SnapshotView、ActivitySnapshot
├── app/                            # 應用層：只依賴 core 與自己的 ports
│   └── activity/
│       ├── ports.py                # Clock、CountdownScheduler、SyncPublisher、ActivityGateway 等 Protocol
│       ├── registry.py             # ActivityRegistry（記憶體、去重表、每個活動的鎖）
│       ├── secrets_gen.py          # 代碼、憑證、token 產生與雜湊
│       └── service.py              # ActivityService
├── adapters/                       # 外層：FastAPI、WebSocket、系統時鐘、asyncio 排程
│   ├── clock.py                    # SystemClock
│   ├── countdown.py                # AsyncioCountdownScheduler
│   ├── web/
│   │   ├── http_api.py             # 11 個 HTTP 端點、錯誤轉換、請求 log
│   │   ├── ws_sync.py              # WebSocket 連線管理、SyncPublisher 實作
│   │   └── dev_seed.py             # 開發用 seed API（環境變數啟用；002 合併後移除）
│   └── static/
│       ├── teacher.html
│       ├── student.html
│       ├── css/app.css
│       └── js/{api.js, sync.js, identity.js, teacher.js, student.js}
tests/
├── conftest.py                     # FakeClock、ManualScheduler、app 工廠
├── unit/core/                      # 狀態機、輸入規則、快照裁切
├── unit/app/                       # 服務層：鎖、去重、並行關輪
├── architecture/test_core_is_pure.py
├── contract/                       # 依 contracts/*.md 檢查 HTTP 與 WebSocket 格式
├── integration/                    # 以 TestClient 跑完整情境（US1～US7）
└── perf/                           # @pytest.mark.perf，真實 uvicorn + 13 條 WebSocket
```

**Structure Decision**：

- **單一專案、三層結構**：`core`／`app`／`adapters` 分別對應組件圖的「核心」「應用層」「外層」，相依方向為 `adapters → app → core`。
- **其他子功能**：002～005 之後分別新增 `core/<能力>/`、`app/<能力>/`、`adapters/web/<能力>.py`，共用 `main.py` 與 `static/`。

## Complexity Tracking

| 例外 | 為什麼需要 | 為什麼不用更簡單的做法 |
|---|---|---|
| 開發用 seed API（`LECTURE_QUIZ_DEV_SEED=1` 才啟用） | 002 合併前，001 的人工驗證需要題目才能開輪 | 等 002 合併後才驗證，會讓 001 卡在相依上；直接改記憶體則無法由非實作者操作。限制條件：預設關閉、只限老師、002 合併後的第一個 PR 移除 |

## Next Actions

1. **補回憲章**：依憲章技術限制 2，以修訂程序把「Ruff（lint + format）、mypy」補進憲章「程式碼風格」（PATCH 版本 1.0.1）。要另開 Issue 與 PR，經兩位組員同意。
2. **開會確認提案**：組內開會檢視 alignment 的 6 筆 2026-11-21 提案，再請 OpenSpec 組確認。結論不同時，依「受待確認提案影響的設計點」修改。
3. **協調 002 介面**：002 整合時，在 002 類別圖的 `ActivityGateway` 補上 `code` 參數，並改為只傳題號（[service-interfaces](contracts/service-interfaces.md)）。
4. **下一步**：執行 `/speckit-tasks`，產生 tasks.md。
