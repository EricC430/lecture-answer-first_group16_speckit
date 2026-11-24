# Implementation Plan: 順位計算、判錯重算與定案（Ranking Review）

**Branch**: `feature/8-004-ranking-review` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-ranking-review/spec.md`

**藍圖**（憲章原則 II）：

- 組件圖：[`diagrams/004-ranking-review-component.puml`](../../diagrams/004-ranking-review-component.puml)
- 類別圖：[`diagrams/004-ranking-review-class.puml`](../../diagrams/004-ranking-review-class.puml)
- 時序圖：[`diagrams/004-ranking-review-sequence.puml`](../../diagrams/004-ranking-review-sequence.puml)

本 plan 的模組、類別與流程依這三張圖命名。plan 階段因研究 R1、R2、R4 調整了「初始結果的產生時機」「鎖」與「推送」，三張圖已在同一個 commit 更新並重新轉出 PNG。實作偏離時先改圖。

**前置條件**：004 依賴 003 的 `SubmissionReader` 與 001 的 `add_snapshot_extension`；兩者已隨 003（PR #16）合併到 main，004 直接從 main 切出即可。`docs/DEVELOPMENT.md` 3.5 規定快照擴充函式必須是同步、無副作用的純讀取，004 遵守（研究 R2）。

## Summary

關輪後，老師對每筆已接受的提交判錯或撤銷判錯；每次判錯狀態改變，系統從開輪時保存的基準與固定題序整輪重算（速度模式或公平模式），產生新的結果版本與「受影響題目」；老師確認所見最新版本後定案，成果只交給 001 一次。結果資料對所有參與者公開查詢，畫面依角色限縮（老師看完整候選情況，學生只看本組狀態、目前的搶答成功者與老師判錯當下剛被判錯的前一組，FR-036；老師介面每題只對目前的搶答成功者提供「判錯」，FR-034）。

技術做法：

- **核心**（`core/ranking_review/`，純函式）：`RankingCalculator`（題序、速度模式排名、公平模式排名、整輪重算、受影響題目 diff）、`RoundReviewRules`（判錯／撤銷／定案的判定，輸入都是已查好的資料）、`ResultView`（依角色裁切的 JSON）。輸入只有基準、模式、題號清單、候選（組號、題號、接收時間、接收序號）與判錯集合，沒有任何時鐘或 I/O。
- **服務層**（`app/ranking_review/`）：`RankingService` 用**自己的**記憶體存放區與每活動一把 asyncio 鎖，序列化判錯、撤銷與定案（研究 R1）；初始結果在關輪後第一次被讀取或操作時產生（研究 R2）；定案呼叫 001 既有的 `ActivityService.finalize(code, requester, FinalizeOutcome)`；推送透過注入的 `SyncPublisher` 在鎖外進行（研究 R4）。
- **快照**：註冊一個快照擴充函式，在快照頂層加 `ranking` 欄位（老師完整版、學生資料公開版），不改 003 的 `submissions` 欄位（研究 R5、R6）。
- **外層**：`PUT /api/activities/{code}/rounds/{round}/questions/{q}/groups/{g}/judgement`（判錯／撤銷）與 `POST /api/activities/{code}/rounds/current/finalize`（取代 001 預留的空定案路由，研究 R7）；老師頁結果區塊與學生頁結果區塊，所有文字用 `textContent`。
- **提供給 005**：`RankingService.finalized_rounds(code)` 唯讀回傳已定案輪次的完整順位、搶答成功者與判錯標記（`contracts/service-interfaces.md`）。

## Technical Context

**Language/Version**: Python 3.11 以上（沿用 001／003）

**Primary Dependencies**: FastAPI、uvicorn、pydantic（沿用，不新增套件）；前端原生 JavaScript

**Storage**: 只存在後端記憶體（憲章原則 VII），後端重啟清空

**Testing**: pytest（`perf` marker 預設排除）、pytest-timeout、FastAPI TestClient；ruff、ruff format、mypy（`src/`）

**Target Platform**: Windows 本機，後端只監聽 127.0.0.1

**Project Type**: 單一 web 服務（後端 + 靜態前端），沿用 001 的 src layout 與三層相依方向

**Performance Goals**: 老師判錯／撤銷／定案後，老師與各組學生畫面 2 秒內顯示新結果與一致的結果版本；老師加 6 組、每組 2 條連線為必過門檻，另量一次 20 組記錄結果（SC-004，由自動化 `perf` 測試執行）

**Constraints**: 核心不依賴網路、框架、系統時鐘；整輪重算不在舊暫算次數上累加；每次重算結果完全由輸入決定（SC-002、SC-003）；搶答中不提供任何順位（FR-024）；學生可取得的資料不含勝出理由與他組成功次數（FR-036）；日誌不記答案內容與 token

**Scale/Scope**: 題數 50 題以內、每活動最多 99 組（001 A2）；每格答案 ≤ 500 字（003）；一次重算要對最多 50 題、每題最多 99 個候選排序，預期為毫秒等級，實際數值由 `perf` 測試量測（研究 R14）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原則 | 檢查 | 結果 |
|---|---|---|
| I 跨組行為一致（NON-NEGOTIABLE） | spec 的 Traceability 涵蓋 ranking-review 全部 7 個 Requirement、12 個 Scenario；判錯相關的顯示方式與免填原因已由 OpenSpec 組 2026-11-23 同意；「資料公開、畫面限縮」不改變資料公開範圍，無新的偏離（見 spec Clarifications） | ✅ |
| II 圖表生成（NON-NEGOTIABLE） | 三張圖已在 specify 產出；plan 因研究 R1、R2、R4 調整後同步更新並重新轉出 PNG；implement 後要做「程式碼 ↔ 圖」一致性檢查（tasks 列為必做） | ✅ |
| III Guided Notes 動態定位 | 004 不讀寫試算表，只處理題號與提交；題號清單來自 001 的輪次規則，核心不含任何固定題數或格位；兩份版面的驗證由 002／005 負責，004 以兩組不同題數配置（A：4 題；B：5 題含題組）的純資料測試驗證不依賴固定題數 | ✅（見 spec Assumptions：Google 項目不適用） |
| IV 後端為唯一事實來源 | 先後只依 003 保存的接收時間與序號；判錯、定案權限只依 001 的老師身分；結果版本由後端遞增；重算確定性（SC-002）；同一判錯請求重送不產生第二次變更（FR-025） | ✅ |
| V 資料可見性與安全 | 搶答中 `ranking` 欄位不存在；學生資料不含勝出理由與他組次數；答案由 003 的 `submissions` 提供、前端一律 `textContent`；所有外部輸入（活動代碼、輪次、題號、組號、結果版本、身分）後端驗證，失敗不改狀態；錯誤訊息不含堆疊、路徑、憑證；日誌只記輪次、題號、組號、版本 | ✅ |
| VI 驗收情境驅動測試 | 每個 Acceptance Scenario 與 OpenSpec Scenario 都有測試並加入 `tests/SCENARIO_MAP.md`；004 不呼叫 Google，自動化測試不呼叫任何外部服務；真實路徑驗證＝非實作者依 quickstart 在多瀏覽器分頁用真實後端人工驗證（SC-009）；效能測試標記 `perf`、本機真實伺服器 | ✅ |
| VII 簡單與本機運作 | 不新增套件、不新增資料庫；對 001 只刪除一條預留的空定案路由並改由 004 提供；對 003 只調整學生頁的前端呈現與其測試（FR-037），不改 003 的資料與後端；不改 001 核心（皆列入 Complexity Tracking） | ✅（附理由） |
| 技術限制：架構（NON-NEGOTIABLE） | `core/ranking_review/` 只匯入標準函式庫與 `lecture_quiz.core` 內模組；`tests/architecture/test_core_is_pure.py` 已涵蓋整個 `core/`；時間資料只來自候選的 `received_at` | ✅ |
| 技術限制：日誌、風格 | `logging` INFO；Google docstring、型別提示；ruff、ruff format、mypy 全過才提交 | ✅ |

**Post-design 重新檢查（Phase 1 後）**：data-model、contracts 與 quickstart 沒有引入新的違反項目。碰到既有程式的地方有三處，都已列入 Complexity Tracking：① 001 的 HTTP 定案路由（研究 R7）；② 既有測試的定案呼叫改用 helper（只改呼叫方式、不改斷言）；③ 003 已合併的學生頁「已公開的作答」呈現（spec FR-037，研究 R5）。003 的 `judgedWrong` 預留欄位維持原狀、前端不使用（研究 R5）。

## Project Structure

### Documentation (this feature)

```text
specs/004-ranking-review/
├── plan.md              # 本檔
├── research.md          # Phase 0：R1～R16 決策
├── data-model.md        # Phase 1：實體、狀態轉移、演算法、驗證規則
├── quickstart.md        # Phase 1：自動化與人工驗證步驟
├── verification.md      # 實作時建立：驗證紀錄（日期、指令、結果數字）
├── contracts/
│   ├── http-api.md          # PUT judgement、POST finalize
│   ├── sync-websocket.md    # 快照新增的 ranking 欄位
│   └── service-interfaces.md # 004 ↔ 001／003／005
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks 產生
```

### Source Code (repository root)

```text
src/lecture_quiz/
├── core/
│   └── ranking_review/             # 004 新增（純函式）
│       ├── __init__.py
│       ├── models.py               # Candidate、RankingInput、RankEntry、QuestionRanking、RoundResult、WinReason、DisplayStatus（含 CORRECT＝搶答正確，定案後）
│       ├── order.py                # QuestionOrder.compute（固定題序）
│       ├── ranking.py              # RankingCalculator：rank_speed、rank_fair、recompute、diff
│       ├── review.py               # RoundReview（版本、判錯集合、結果、受影響題目、被替換的搶答成功者 `replaced`、定案）、RoundReviewRules：mark（判錯／撤銷）、finalize_plan（新成功題號、各組增量、最終累計）
│       ├── outcome.py              # FinalizedResult（定案時保存的唯讀結果）
│       └── view.py                 # ResultView.for_teacher／for_student（依角色裁切 JSON）
├── app/
│   └── ranking_review/             # 004 新增
│       ├── __init__.py
│       ├── ports.py                # RankingReader（給 005）
│       ├── store.py                # ReviewStore（記憶體）、每活動鎖
│       └── service.py              # RankingService
└── adapters/
    ├── web/
    │   ├── http_api.py             # 小改：移除 001 預留的空 finalize 路由（改由 004 提供）
    │   └── ranking_review.py       # PUT judgement、POST finalize
    └── static/
        ├── teacher.html            # 加一個 <section id="ranking-review-section">
        ├── student.html            # 加一個 <section id="ranking-review-student-section">
        └── js/
            ├── ranking-review-teacher.js   # 老師端：候選情況、只對目前搶答成功者的「判錯」、對被替換者的「撤銷判錯」、確認定案
            ├── ranking-review.js           # 學生端：本組狀態、目前搶答成功者與剛被判錯的前一組
            └── round-submission.js         # 003 小改：學生頁關輪後不再列出全部組作答（FR-037）

tests/
├── unit/core/ranking_review/       # 題序、速度／公平排名、重算、受影響題目、判定、View 裁切、確定性
├── unit/app/ranking_review/        # 服務 + 真 ActivityService + FakeClock、併發、001 拒絕定案
├── conftest.py（小改：finalize_current helper）、architecture/test_static_text_safety.py（擴充）、既有定案測試改呼叫 helper（不改斷言）
├── contract/test_http_ranking_review.py
├── integration/test_us{1..7}_ranking_*.py、test_ranking_visibility.py
└── perf/test_ranking_latency.py    # 6 組（門檻）與 20 組（記錄）
```

**Structure Decision**：沿用 001 的三層 src layout；004 新增 `core/ranking_review/`、`app/ranking_review/`、`adapters/web/ranking_review.py`，在 `main.py` 的「子功能 router」區塊加一行掛載、並在組裝處建立 `RankingService`（傳入 001 服務、003 的 `SubmissionReader`、`SyncHub`）。檔案配置符合 `docs/DEVELOPMENT.md` 的子功能擴充約定。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| 修改已合併的 001：移除 `POST /activities/{code}/rounds/current/finalize` 的空定案實作，改由 004 在同一路徑提供（需 `resultVersion`） | 001 的 http-api.md 已註明「`{}`（004 會擴充）」；若兩個路由並存，任何人用空本文就能不經 004 定案，結果與成功次數會對不上（FR-020、FR-021） | 保留 001 路由並在 001 內呼叫 004：001 的 adapters 會反向依賴 004，違反「子功能只加一行 router」的擴充約定；既有 001／003 測試以 `{}` 呼叫此路由，需改用 helper 先取得結果版本（tasks 列為必做） |
| 修改 003 已合併的學生頁前端（`round-submission.js`）與其畫面相關測試：關輪後不再對學生列出全部組的作答 | spec FR-037：使用者決定學生畫面只顯示本組狀態、目前搶答成功者與剛被判錯的前一組；003 的學生頁目前列出全部組作答與送出先後，兩者並存會洩漏畫面上不該有的資訊 | 保留 003 區塊並在 004 區塊旁並列：學生會同時看到全部組作答，違反 FR-036／037；只改前端呈現、不改 003 的資料與後端，資料公開範圍（OpenSpec）不變 |
| 004 自己持有每活動一把 asyncio 鎖，而不是使用 001 的活動鎖 | 定案要呼叫 `ActivityService.finalize`，該方法本身取得 001 的活動鎖，鎖不可重入；若 004 在 001 鎖內再呼叫會死鎖 | 在 001 加 handler 式的鎖內擴充點（像 003 的 `record_submission`）：要改 001 核心與服務，而 RESULT_PENDING 階段只有 `finalize` 能改變階段，004 專屬鎖已足夠序列化所有 004 操作（研究 R1） |
