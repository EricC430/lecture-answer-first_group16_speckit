# Implementation Plan: 活動建立、組別加入與階段同步

**Branch**: `feature/5-001-activity-session` | **Date**: 2026-11-21（2026-11-23 依 Clarifications 更新） | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-activity-session/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/001-activity-session-component.puml`](../../diagrams/001-activity-session-component.puml)
- 類別圖：[`diagrams/001-activity-session-class.puml`](../../diagrams/001-activity-session-class.puml)
- 時序圖：[`diagrams/001-activity-session-sequence.puml`](../../diagrams/001-activity-session-sequence.puml)

本 plan 的模組、類別與流程都依這三張圖命名；設計需要偏離時，先改圖並重新轉出 PNG。

## Summary

本子功能提供搶答系統的骨架：

- 老師指定組數上限 N（1～99）建立活動並取得獨占控制權；同一個瀏覽器同時只能有一個存續中的活動。
- 學生以「組號（1～N）+ 6 碼組別憑證」加入，多裝置同組，重新整理後恢復身分；也可以在非搶答中離開本組，老師可以刪除沒有提交的空組。
- 一套 7 階段狀態機（準備中、開放加入、搶答中、結果未定案、結果已定案、已結束、已取消），管理開放加入、開輪、關輪只一次、定案、結束與取消。老師先匯入題目並按「開放加入」，學生才能加入。
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

**Scale/Scope**：一堂課 1～數個活動，每個活動數十組、數十題；兩個頁面（老師、學生）；12 個 HTTP 端點、1 條 WebSocket。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 檢查項 | 結果 | 依據 |
|---|---|---|
| **I 跨組行為一致** | ✅ 通過 | spec 的 Traceability 涵蓋 6 條 Requirement 與 12 個 Scenario（2026-11-23 後續決議：開放加入階段、空組免憑證、刪除組別規則，兩組已同意，見 alignment）。所有偏離與新增行為（組號、組數上限、組別加入憑證、倒數、取消與結束、離開本組、刪除空組、一位老師一個活動）都已記入 `docs/alignment.md`，OpenSpec 組於 2026-11-23 全部確認 |
| **II 圖表生成** | ✅ 通過 | 以三張圖為藍圖。本 plan 為圖表補上 `code` 參數，以及給 003／004／005 的介面方法，已同步更新類別圖並重新轉出 PNG。tasks 必須有「程式碼與圖表一致性驗證」任務 |
| **III Guided Notes 動態定位** | ✅ 通過（不適用解析） | 本子功能不解析學習單。`replace_questions` 只接收 002 成功匯入的題號；被拒時，既有題目完全不變（[service-interfaces](contracts/service-interfaces.md)）。不需要「兩份版面學習單」測試 |
| **IV 後端為唯一事實來源** | ✅ 通過 | 身分由後端 token 雜湊判定（研究 R5）；階段、關輪只一次由鎖與 `round.closed` 雙重保證（研究 R6）；重送以 `Idempotency-Key` 去重；狀態機是確定性純函式 |
| **V 資料可見性與安全** | ✅ 通過 | 學生快照只含本組資料，連實際組數都不給（[data-model](data-model.md)）；所有輸入（含組數上限、組號、憑證）由 `InputRules` 在後端驗證，失敗時不改變狀態；錯誤只回 `code` 與可修正的 `message`；不可信文字以 `textContent` 輸出；token 只保存雜湊、比對用 `compare_digest`、不寫入 log |
| **VI 驗收情境驅動測試** | ✅ 通過 | 每個 Acceptance Scenario（US1～US7，共 47 個）至少對應一個測試，docstring 標明 `Scenario: USn-ASm`。本子功能不使用 Google，因此不需要 mock 或真實路徑驗證。非實作者人工驗證腳本見 [quickstart](quickstart.md)，包含 2 秒同步與重啟失效 |
| **VII 簡單與本機運作** | ✅ 通過 | 只用記憶體、單一 process、只監聽 `127.0.0.1`。前端不用框架與建置工具。開發用的 seed API 預設關閉，002 合併後移除（見 Complexity Tracking） |
| **技術限制 1 堆疊** | ✅ 通過 | Python 3.11 以上 + FastAPI；Windows 本機；只監聽 localhost |
| **技術限制 2 程式碼風格** | ✅ 通過 | PEP 8 由 Ruff 檢查；型別提示與 docstring 由 Ruff 規則 ANN、D 加上 mypy 檢查（研究 R3）。**lint 與格式化工具已定案，需以修訂程序補回憲章**（Next Actions） |
| **技術限制 3 日誌** | ✅ 通過 | `logging.basicConfig(level=INFO, stream=sys.stdout)`；請求 log 的欄位白名單見 [http-api](contracts/http-api.md) |
| **技術限制 4 效能** | ✅ 通過 | N = 6，有自動化效能測試與人工延遲顯示（研究 R2）；系統的組數上限由老師建立活動時指定（1～99，研究 R9；alignment 2026-11-23 A2） |
| **技術限制 4 架構（NON-NEGOTIABLE）** | ✅ 通過 | 核心放在 `src/lecture_quiz/core/`，只依賴標準函式庫的資料型別。`tests/architecture/test_core_is_pure.py` 以 `ast` 自動檢查（研究 R4）；相依方向為 `adapters → app → core` |

**Phase 1 設計完成後重新檢查**（2026-11-23 依 Clarifications 再檢查一次）：結果相同，沒有新增違規。唯一需要說明的例外，是開發用 seed API，列在 Complexity Tracking。

## OpenSpec 組確認後的設計調整（2026-11-23）

2026-11-21 的提案已全部獲確認（alignment 2026-11-23）。與 2026-11-21 版 plan 相比，設計調整如下：

| 決議 | 設計調整 | 依據 |
|---|---|---|
| A1 組號取代組名 | `Group.number: int` 成為識別鍵；`DeviceIdentity.group_number`、`Round.baseline`、`FinalizeOutcome.success_increments` 都以組號為 key；`InputRules.normalize_group_number` 取代 `normalize_group_name`；拒絕原因 `INVALID_GROUP_NAME` 改為 `INVALID_GROUP_NUMBER` | 研究 R9 |
| A2 組數上限 | `Activity.max_groups`；建立活動的 HTTP 本文新增 `maxGroups`；`InputRules.validate_max_groups`（1～99）；新增拒絕原因 `INVALID_MAX_GROUPS`；老師快照新增 `maxGroups` | 研究 R9 |
| B3 組別加入憑證 | 維持原設計（學生快照 `ownGroup.credential`、老師快照每組 `credential`）；新增 `ALREADY_IN_GROUP` | 研究 R9 |
| B4、B5 離開本組、刪除空組 | 維持原設計（`LeaveGroup`、`DeleteGroup`、`MarkGroupSubmitted`）；刪除路徑改為 `DELETE /activities/{code}/groups/{number}`；新增 `GROUP_NOT_FOUND`、`NOT_IN_GROUP` | contracts |
| C6、C8、C9 | 維持原設計 | — |
| C7 一位老師一個存續中活動 | `ActivityService.create` 檢查請求帶的老師 token；`ActivityRegistry.find_by_teacher`；新增 `TEACHER_HAS_ACTIVE_ACTIVITY`；前端 `localStorage["teacher:last"]` | 研究 R10 |

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
├── main.py                         # 建立 FastAPI app、logging 設定、組裝 001 服務、掛載路由與靜態檔
├── __main__.py                     # python -m lecture_quiz（只監聽 127.0.0.1，日誌輸出到 stdout）
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
│       ├── ports.py                # Clock、CountdownScheduler、SyncPublisher、ActivityGateway 等 Protocol（由 adapters 實作）
│       ├── registry.py             # ActivityRegistry（記憶體、去重表、每個活動的鎖）
│       ├── secrets_gen.py          # 代碼、憑證、token 產生與雜湊
│       └── service.py              # ActivityService
├── adapters/                       # 外層：FastAPI、WebSocket、系統時鐘、asyncio 排程
│   ├── clock.py                    # SystemClock
│   ├── countdown.py                # AsyncioCountdownScheduler
│   ├── web/
│   │   ├── common.py               # 共用骨架（Issue #5）：統一錯誤格式、例外處理、請求 log、Bearer／Idempotency-Key 解析、/api 404 fallback
│   │   ├── system.py               # 共用骨架：GET /api/health
│   │   ├── http_api.py             # 001 的 HTTP 端點、Outcome 與 RejectionReason → HTTP
│   │   ├── ws_sync.py              # WebSocket 連線管理、SyncPublisher 實作
│   │   └── dev_seed.py             # 開發用 seed API（環境變數啟用；002 合併後移除）
│   └── static/
│       ├── teacher.html
│       ├── student.html
│       ├── css/app.css
│       └── js/{api.js, sync.js, identity.js, countdown.js, teacher.js, student.js}
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
| 開發用 seed API（`LECTURE_QUIZ_DEV_SEED=1` 才啟用；**已於 2026-11-23 移除**） | 002 合併前，001 的人工驗證需要題目才能開輪 | 等 002 合併後才驗證，會讓 001 卡在相依上；直接改記憶體則無法由非實作者操作。限制條件：預設關閉、只限老師、002 合併後的第一個 PR 移除 |

## Next Actions

1. ~~補回憲章（Ruff、mypy）~~：已由 PR #13 合併為憲章 v1.0.1。
2. ~~開會確認提案~~：OpenSpec 組 2026-11-23 全部同意（alignment 2026-11-23）。
3. ~~協調 002 介面~~：EricC430 已於 Issue #6 同意 `code` 參數與只傳題號，PR #11 已更新 002 類別圖。
4. ~~更新 tasks 並分析~~：已執行 `/speckit-tasks`、`/speckit-analyze`，US1～US7 與 Polish 已實作。
5. **下一步**：處理 PR #15 的審查意見，由 EricC430 依 quickstart 執行人工驗證（T084）。
