# 驗證紀錄：004-ranking-review

所有指令都在專案根目錄用 `.venv\Scripts\` 的工具執行（Python 3.14.7）。每筆紀錄只寫實際執行過的指令與結果數字。

## 基準（T002，2026-11-24，實作開始前，分支已合併 main 的 003）

| 指令 | 結果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 184 files already formatted |
| `mypy` | Success: no issues found in 36 source files |
| `pytest -q` | 547 passed, 2 deselected |

## 先寫測試的失敗紀錄

| 階段 | 日期 | 指令 | 實作前的結果 |
|---|---|---|---|
| Phase 2（T005～T008） | 2026-11-24 | `pytest tests/unit/core/ranking_review tests/unit/app/ranking_review tests/contract/test_http_ranking_review_wiring.py -q` | 收集階段 ImportError：`No module named 'lecture_quiz.app.ranking_review.service'`（conftest 無法載入），0 個測試能執行 |

## 自動化結果

| 階段 | 日期 | 指令 | 結果 |
|---|---|---|---|
| Phase 2 完成（T018） | 2026-11-24 | `pytest -q` | 563 passed, 2 deselected（基準 547 + 新增 16）；`pytest tests/architecture -q` 47 passed；`ruff check .` All checks passed；`ruff format --check .` 201 files already formatted；`mypy` Success: no issues found in 45 source files |
| Phase 3～4 完成（T019～T036，US1／US2） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy`；`pytest tests/architecture -q` | 598 passed, 2 deselected（Phase 2 後 563 + 新增 35）；ruff All checks passed；format 214 files already formatted；mypy Success: no issues found in 48 source files；architecture 50 passed。測試先行：US1 核心測試先因匯入失敗（collection error）、app 4 項失敗，實作後通過；US2 3 個核心測試檔先 collection error、view／app／integration 先失敗，實作後通過。前端（T035／T036）無自動化測試，僅通過靜態文字安全檢查，畫面行為待 T094 人工驗證 |
| Phase 5 完成（T037～T042，US3） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 611 passed, 2 deselected（+13）；ruff All checks passed；format 217 files already formatted；mypy Success: no issues found in 48 source files。**未做到先紅後綠**：`rank_fair` 在 US2 實作 `recompute` 時一併完成，所以 US3 測試一寫完就通過；改以突變檢查補強：暫時把公平排序鍵的成功次數改成常數 0，`test_rank_fair.py`＋`test_fair_layouts.py` 11 項中 5 failed、6 passed，還原後 41 passed（`tests/unit/core/ranking_review`）。前端（T042）無自動化測試，待 T094 |
| Phase 6 完成（T043～T052、T055，US4） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 693 passed, 2 deselected（+82）；ruff All checks passed；format 224 files already formatted；mypy Success: no issues found in 48 source files。測試先行：`test_review_rules_mark.py` 先 ImportError（`RoundReviewRules` 不存在）、服務層 3 個測試檔先 `NotImplementedError`、HTTP 契約與端對端 19 項先全數失敗（`19 failed`），實作後 `19 passed`。`test_diff.py` 的 3 項在 `diff` 於 US2 已實作時就通過（同 P-06）。前端判錯／撤銷按鈕（T052）無自動化測試，待 T094 人工驗證 |
| Phase 7 完成（T053～T054、T056～T059，US5） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 703 passed, 2 deselected（+10）；ruff All checks passed；format 227 files already formatted；mypy Success: no issues found in 48 source files。依 T058 說明，重算在 US2～US4 已實作，所以這組測試一寫完就通過（不要求先失敗）；鑑別力由 T054 負對照證明：累加式錯誤實作 `accumulating_recompute` 跑完判錯、撤銷後與初始結果不同（`!=` 斷言通過），正確實作相同。前端「結果已更新」與版本守衛（T059）無自動化測試，待 T094 |
| Phase 8 完成（T060～T070，US6） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 733 passed, 2 deselected（+30）；ruff All checks passed；format 235 files already formatted；mypy Success: no issues found in 48 source files。測試先行：`test_finalize_plan.py` 先 `AttributeError`（無 `finalize_plan`），其餘 US6 測試在實作前因 `finalize` 為 `NotImplementedError` 失敗。實作後 001 的空定案路由已移除，既有 2 個測試因行為變化調整（見 P-09、P-10）。老師頁「確認定案」按鈕（T070）無自動化測試，待 T094 |
| PR #20 審查回應（T096） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy` | 735 passed, 2 deselected（+2，新增 `test_single_finalize_button.py`）；ruff All checks passed；format 236 files already formatted；mypy Success: no issues found in 48 source files。已移除 001 老師頁的舊「確認定案」按鈕；Q-23／24／25 於 alignment.md 標為定案 |
| Phase 9 完成（T071～T078，US7） | 2026-11-24 | `pytest -q`；`ruff check .`；`ruff format --check .`；`mypy`；`node --check`（6 個前端模組） | 746 passed, 2 deselected（+11）；ruff All checks passed；format 240 files already formatted；mypy Success: no issues found in 48 source files；node --check 6 個模組皆語法正確。**未做到先紅後綠**：US7 的資料面（學生版省略理由與次數、替換歷程、版本單調）在 US2～US6 已實作，所以 T071、T072、T074、T075 一寫完就通過；T073 擴充 `FORBIDDEN` 加入 `eval(`、`new Function`，既有與新增前端檔案都不含，直接通過。**學生畫面實際只顯示哪些組（T076）、003 學生頁移除已公開作答（T077）、老師頁不重複顯示答案（T078）沒有自動化測試，只有語法檢查，必須由 T094 人工驗證** |
| Phase 10 自動化收尾（T079～T091、T093、T095） | 2026-11-24 | 見下方各列 | 見下方各列 |
| T085 ruff／mypy | 2026-11-24 | `ruff check .`；`ruff format --check .`；`mypy` | All checks passed；309 files already formatted；Success: no issues found in 68 source files |
| T087 全部自動化測試（已合併 main 的 002 之後） | 2026-11-24 | `pytest -m "not real_google and not perf"` | 1089 passed, 5 deselected。與 T002 基準（547 passed）比較：增加包含 main 合併進來的 002 測試與 004 新增測試，沒有失敗 |
| T093 quickstart 一、自動化驗證 | 2026-11-24 | `pytest tests/architecture/test_core_is_pure.py`；`pytest tests/unit/core/ranking_review tests/unit/app/ranking_review tests/contract/test_http_ranking_review.py -k "ranking"`；`pytest -m perf tests/perf/test_ranking_latency.py` | 29 passed；161 passed；2 passed（數字見效能一節）。`tests/SCENARIO_MAP.md` 004 區塊：56 個 Acceptance Scenario 中 55 個有對應測試，未對應 US7-AS2（學生畫面實際顯示，前端行為，待 T094）；OpenSpec 13 列（12 個 ranking-review Scenario＋1 列跨能力）皆有測試 |
| T086 日誌與核心純度 | 2026-11-24 | `grep -rn "print(" src/`；`grep -rnE "datetime\.now\|import time\|import asyncio\|fastapi" src/lecture_quiz/core/ranking_review/` | 兩者都沒有任何輸出；`test_core_is_pure.py` 29 passed；`snapshot_extension` 只做純計算與 `ReviewStore.cache` 的不可變快取，沒有 I/O 或狀態寫入（程式審視） |
| T084 程式碼與圖表一致性 | 2026-11-24 | 人工逐項比對 `diagrams/004-ranking-review-{component,class,sequence}.puml` 與程式；改圖後 `java -jar plantuml.jar` 重新轉出並開啟 PNG 檢視 | 發現類別圖 4 處與程式不一致並已修正：題序在獨立的 `QuestionOrder`（由 `RoundReview.initial` 呼叫）、`as_final` 是函式不是 `ResultView` 方法、新增 `RoundView`、回傳型別為 `ReviewOutcome`；`RankingCalculator` 補 `initialCounts`、`rankSpeed`／`rankFair` 的實際參數。組件圖與時序圖與程式一致，不需修改。類別圖 PNG 已重新產生並開啟檢視，文字可讀、無重疊 |
| T089 OpenSpec 核對 | 2026-11-24 | `sha256sum docs/openspec-reference/ranking-review/spec.md` | `7a243602279aa7f22f33436903cb171df7749d2efe951783ec5c56c4615bd23f`，與 `README.md` 一致；實作沒有新增或偏離 OpenSpec 的功能行為（學生畫面範圍屬顯示時機，使用者 2026-11-24 確認不衝突） |
| T095 機敏資料 | 2026-11-24 | `git ls-files \| grep -E "\.env$\|credentials\|client_secret\|期末專題說明\|project_proposal"`；`grep -rln "client_secret\|access_token\|refresh_token"` 於 004 檔案 | 沒有任何輸出；全專案 grep 的命中只在 002 的 Google 轉接器（設定欄位名稱），不是 004 的檔案，也不是密鑰值 |
| Convergence T097（ENDED 階段鎖定測試） | 2026-11-24 | `pytest -m "not real_google and not perf"`；`ruff check .`；`ruff format --check .`；`mypy` | 1090 passed, 5 deselected（+1）；ruff All checks passed；format 309 files already formatted；mypy Success: no issues found in 68 source files。新測試 `test_after_activity_ended_everything_stays_locked` 一寫完就通過（行為已正確，converge 探測先確認過）；突變檢查：暫時讓 `_is_final` 不含 `Stage.ENDED`，該測試 1 failed、同檔其餘 3 passed，還原後 4 passed |
| Convergence T098（移除 `ReviewStore.drop`） | 2026-11-24 | `pytest -m "not real_google and not perf"`；`ruff check .`；`ruff format --check .`；`mypy`；`grep -rn "\.drop(" src tests` | 1089 passed, 5 deselected（移除 1 個只測 `drop` 的測試，-1）；ruff All checks passed；format 309 files already formatted；mypy Success: no issues found in 68 source files；grep 沒有任何輸出 |

## 效能（T082～T083）

日期：2026-11-24。指令：`pytest -m perf tests/perf/test_ranking_latency.py`（本機真實 uvicorn、`websockets` 客戶端，50 題；第 1～9 輪各 1 題、第 10 輪 41 題且每組都提交；判錯、撤銷判錯各 10 次、定案 10 次）。量測「送出請求 → 所有連線都收到含新結果的快照」的最大值。結果：`2 passed in 44.91s`。

| 操作 | 6 組（13 條連線，**必過 < 2000 ms**）最大／平均 | 20 組（41 條連線，**只記錄**）最大／平均 |
|---|---|---|
| 判錯 | 68.0 ms／61.9 ms | 702.2 ms／553.7 ms |
| 撤銷判錯 | 112.9 ms／65.4 ms | 638.3 ms／556.8 ms |
| 定案 | 56.1 ms／11.6 ms | 623.9 ms／82.8 ms |

- 6 組：三種操作最大值都小於 2000 ms，達標（SC-004）。
- 20 組：這次量到的最大值都小於 2000 ms，但沒有當成通過條件，也**不宣稱** 20 組達標；它比 6 組慢約 6～10 倍（判錯平均 553.7 ms 對 61.9 ms），主要是 41 條連線各收到一份含 41 題 × 20 組候選的快照。研究 R14 的「只送目前輪並提供 GET 查詢舊輪」暫不實作，僅記錄為建議。
- 單次、本機、同一台機器同時跑客戶端與伺服器，未取多次分布；只能說明本機這次的量測，不代表他組電腦。

## 人工驗證（T094）

（尚未執行；需要 002 合併後才能真實匯入題目）

## N/A 說明（T090）

- **憲章原則 III（動態定位、兩份版面學習單驗證）與 Google 真實路徑驗證不適用於 004**：004 不讀寫試算表、不呼叫任何 Google 服務（spec Assumptions）。題數與版面對 004 只是 001 提供的題號清單與 003 的提交資料，所以 004 以 `LAYOUT_A`（4 題）、`LAYOUT_B`（5 題，含無提交題與題組）兩組不同題數配置的純資料測試取代（T024、T039：`tests/unit/core/ranking_review/test_fair_layouts.py` 等），並以真實後端多分頁人工驗證（T094，尚未執行）取代。
- **自動化測試完全不呼叫外部服務**：沒有 Google、LLM 或付費服務；全部測試離線執行。
- **沒有 LLM 評分**：004 的測試是規則與資料比對，不使用 LLM judge；本檔不報告任何模型分數。

## 問題紀錄

| 編號 | 階段 | 問題 | 處理 |
|---|---|---|---|
| P-01 | Phase 2 | `core/ranking_review/models.py` 的資料型別在寫 T005 測試之前已先草擬，不是先有失敗的測試 | 型別本身沒有行為邏輯；T005 測試補齊後通過。之後每個 Story 先寫測試並確認失敗再實作 |
| P-02 | Phase 2 | 專案沒有 `pytest-asyncio`，既有測試以 `asyncio.run(scenario())` 寫非同步測試 | 004 的測試沿用同一做法 |
| P-03 | Phase 2 | tasks 寫「`Outcome` 沿用 001 的型別」，但 001 的 `Outcome.rejection` 型別是 001 的 `RejectionReason` | 004 另定 `ReviewOutcome[T]`（`rejection` 為 `ReviewRejection`），與 contracts 的錯誤表一致；不放寬 001 的型別 |
| P-04 | Phase 2 | `T005` 的「RankingInput 不變式以 recompute 拒絕」依賴 recompute | 該不變式測試放在 US2 的 `test_recompute_speed.py`（recompute 實作時一併驗證） |
| P-05 | Phase 2 | T017 遷移既有測試：`test_finalize_contract` 原斷言回應 `== {"version": ...}`，004 取代 001 空定案路由後回應多了 `resultVersion`、`alreadyFinalized` | 斷言改為只比對 `["version"]`（活動狀態版本語意不變）；這是契約本身的變更，已記錄；其他測試只改呼叫方式（補 `{"resultVersion": 1}`），斷言未改 |
| P-06 | Phase 5 | tasks 要求 US3 測試先失敗再實作，但 `rank_fair` 已在 US2 完成 | 如實記錄於上表，並以突變檢查證明測試能分辨對錯 |
| P-07 | Phase 6 | 測試寫「已取消且有輪次」的活動判錯，但 001 只允許第一輪之前取消，該情境不可能發生 | 改為對「取消後（沒有輪次）的活動」判錯，回 `ACTIVITY_CANCELLED`；判定順序仍是取消先於 `NO_ROUND` |
| P-08 | Phase 6 | 佈線測試原本用 `app.routes` 的 `path` 找路由，但巢狀 router 的 path 是空字串，斷言恆為 0（上一版的 `<= 1` 是假綠燈） | 改用 `app.openapi()["paths"]`，斷言恰有一條 `PUT .../judgement` |
| P-09 | Phase 8 | `test_finalize_during_round_is_409` 斷言搶答中定案的訊息為「請先關輪，再確認定案。」；004 接手後預設訊息變成「本輪尚未關閉，無法判錯。」 | 定案時的 `ROUND_STILL_OPEN` 沿用原訊息，測試斷言未改 |
| P-10 | Phase 8 | `test_second_round_keeps_history_and_hides_new_answers` 在第 2 輪提交題一，但 001 空定案換成 004 真定案後題一已成功、提交被拒（400） | 該測試改提交題二；這是定案行為從「不記成果」變成「記成功題」的預期後果，未放寬任何斷言 |
| P-11 | Phase 8 | 我寫的 US6 測試有三處預期算錯（沒判錯時乙只成功題二，次數應為 1 而不是 2）；第 2 輪「全題成功後開輪」001 回 400 而非 409 | 修正測試預期，實作未改 |
| P-12 | Phase 9 | T077 要求調整 003 學生頁；`grep -rn "renderPublished\|published-section\|published-list" tests` 沒有任何測試斷言學生頁文字，所以沒有測試需要調整；`submissions.published` 的資料層斷言完全未動 | 刪除學生頁「已公開的作答」區塊（`student.html`）與 `round-submission.js` 的 `renderHistory`；003 負責人需知會 |
| P-13 | Phase 9 | T078：老師頁同一輪的答案會在 003 已公開列表與 004 區塊各出現一次 | `round-submission-teacher.js` 只列出 004 尚未涵蓋的輪次；判錯標記以 004 為準 |
