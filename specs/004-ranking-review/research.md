# Research：004-ranking-review

**日期**：2026-11-24 ｜ 所有「未知」都已在本檔決定；沒有殘留的 NEEDS CLARIFICATION。

本檔依據的實際程式與文件（main 上的 001 與 003（PR #16 合併後，2026-11-24 重新核對））：

- 001：`app/activity/service.py`（`ActivityService`、`finalize`、`add_snapshot_extension`、`snapshot_for`）、`core/activity/state_machine.py`（`_finalize`）、`core/activity/commands.py`（`FinalizeOutcome`）、`adapters/web/http_api.py`（既有 finalize 路由）、`contracts/*`。
- 003：`app/round_submission/service.py`（`round_submissions`、快照擴充）、`core/round_submission/view.py`（`published`）、`contracts/service-interfaces.md`、`data-model.md`。
- 005 spec（讀取 004 的定案結果）。

## R1 004 自己的鎖與記憶體存放區

- **決定**：004 有自己的 `ReviewStore`（每個活動一份，記憶體）與「每活動一把 `asyncio.Lock`」。判錯、撤銷、定案、初始結果建立都在這把鎖內做；推送在鎖外。不改 001 的鎖。
- **理由**：
  1. 001 的 `ActivityService.finalize` 內部自己取得 001 的活動鎖（`async with self._registry.lock(code)`），鎖不可重入；004 若在 001 鎖內呼叫它會死鎖。
  2. 活動停在「結果未定案」時，唯一能改變階段的操作就是 `finalize`（取消只能在準備中／開放加入、結束只能在已定案後、開輪只能在開放加入或已定案後）。而定案一律經 004，所以 004 的專屬鎖已足以保證「判錯／撤銷／定案」不交錯（FR-029）。
- **考慮過的替代方案**：像 003 一樣在 001 新增鎖內 handler 擴充點。要改 001 核心與服務，影響面大於收益，所以不採用。

## R2 初始結果由純計算即時導出，第一次判錯才建立並保存

- **決定**：不要求 001 在關輪時呼叫 004。關輪後、還沒有任何判錯時，`ReviewStore` 裡沒有該輪的 `RoundReview`；快照擴充函式與 `finalize` 以純計算「導出」初始結果（版本 1、判錯集合為空）而不寫入存放區。第一次實際判錯時，才以這份初始結果為起點建立 `RoundReview` 並存入 `ReviewStore`（版本 2），之後都以存放區為準。
- **理由**：
  1. 003 保證關輪後不會再有新提交（提交與關輪在 001 同一把鎖內序列化，003 FR-019），所以關輪後任何時間算出的初始結果都相同；延後建立與關輪時建立沒有差別。
  2. 001 關輪後會推送快照，快照擴充函式在推送時導出初始結果，老師與學生看到的第一份結果就是版本 1（FR-016、spec Assumptions）。
  3. `docs/DEVELOPMENT.md` 3.5（003 合併後加入）規定快照擴充函式「同步、無副作用的純讀取」，每次產生快照都會呼叫；導出初始結果只有純計算，沒有寫入，符合這項約定。
- **考慮過的替代方案**：在 001 的關輪流程加 `on_round_closed` hook。要改 001 服務；而且 hook 若失敗要處理半途狀態。延後建立沒有這些風險。
- **風險與緩解**：每次產生快照、每條連線都可能重新導出初始結果，成本重複。緩解：初始結果的輸入（基準、模式、提交）在關輪後不變，且尚無判錯的期間很短；若量測顯示明顯變慢，可用以（輪次, 版本）為鍵的不可變記憶體快取（R14），快取不改變結果、不屬於狀態。測試確認多個連線與多次導出得到相同的 `ranking`，且不會使版本增加。

## R3 結果版本與 001 的狀態版本互相獨立

- **決定**：004 的「結果版本」（`resultVersion`，每個輪次各自從 1 開始、每次實際判錯變更加 1）與 001 的 `Activity.version`／`revision` 互相獨立，不改 001。
- **理由**：001 的 `version` 只在階段、輪次、題號或已成功題改變時才加 1（001 data-model），並規定提交標記、組別加入等不加；判錯屬於 004 自己的狀態。前端對 `snapshot.version` 較小者丟棄、老師對 `revision` 較小者丟棄，兩者在判錯時都不變，所以快照仍會被接受。
- **前端防舊版本覆蓋**（FR-016）：004 的前端模組為每個輪次記住已收過的最大 `resultVersion`；收到的快照裡該輪 `resultVersion` 較小時，不更新 004 區塊（其他區塊照常更新）。
- **考慮過的替代方案**：讓判錯也使 001 的 `revision` 加 1。要在 001 核心新增一個「系統指令」，與 003 的 `RecordSubmission` 重複類似的改動。

## R4 推送：注入 `SyncPublisher`，鎖外呼叫

- **決定**：`RankingService` 建構時收到 001 的 `SyncPublisher`（組裝處的 `WebSocketHub`），判錯或定案成功後在鎖外呼叫 `await publisher.publish(activity)`，`activity` 取自 `ActivityService.get(code)`。
- **理由**：`WebSocketHub.publish` 會對每條連線呼叫 `service.snapshot_for`（含所有擴充），「裁切後內容與上次相同時不送」，所以判錯後 `ranking` 變了就會推送，而沒有變化（重複判錯）就不會推送，符合 FR-025。001 的 `ActivityService._publish` 是私有方法，不使用。
- **失敗處理**：推送例外只記錄 `logger.exception`，不影響已完成的狀態變更（與 001 `_publish` 相同）。

## R5 快照擴充 `ranking`，不改 003 的 `submissions`

- **決定**：向 `ActivityService.add_snapshot_extension` 註冊一個函式，回傳 `{"ranking": {...}}` 併入快照頂層。`ranking` 只放順位、狀態、判錯與老師專屬的次數與理由；答案、接收時間、送出先後仍由 003 的 `submissions.published` 提供，前端以（輪次、題號、組號）合併。
- **理由**：
  1. 003 的 plan 明文寫「判錯標記屬於 004，004 另行註冊快照擴充或擴充 003 的公開版資料（004 plan 決定）」。
  2. 擴充函式的回傳是頂層 `update`，無法深層覆寫 003 的 `submissions`；另開欄位不會與 003 互相覆蓋。
  3. 同一份快照裡 `ranking` 與 `submissions` 對應同一個活動狀態；`submissions.published` 在關輪後不再改變，所以不會出現「003 新、004 舊」的混合畫面（FR-035）。
- **003 的 `judgedWrong` 預留欄位**：維持原狀（一律 `false`），004 的前端不使用它，以 `ranking` 的 `judgedWrong` 為準；是否移除留給 003 的後續整理（研究 R16）。
- **003 的學生頁需要調整**：003 已合併的學生頁（「已公開的作答」區塊，`renderPublished`）會對所有學生列出全部組的答案與送出先後，與 spec FR-036、FR-037 的學生畫面範圍不同。004 的 tasks 要涵蓋：學生頁關輪後改由 004 的結果區塊呈現（本組狀態、目前搶答成功者與剛被判錯的前一組），不再逐組列出全部作答；老師頁沿用 003 的已公開輪次列表並補上 004 資料。003 資料的公開範圍不變，只改前端呈現與其測試。

## R6 `ranking` 的角色形狀：資料公開、畫面限縮

- **決定**：
  - **老師**：每個已關輪輪次的完整資料：每題全部候選的 `rank`、`countAtProcessing`、`reason`、`judgedWrong`、`displayStatus`，另有 `questionOrder`、各組暫算次數 `groupCounts`、`affectedQuestions`、每題的 `replacedGroup`、`resultVersion`、`final`。
  - **學生（所有學生同一份）**：同樣的輪次與題目，但每個候選只有 `groupNumber`、`rank`、`judgedWrong`、`displayStatus`，不含 `countAtProcessing`、`reason`、`groupCounts`。
  - 學生畫面只顯示「本組狀態、每題目前的搶答成功者（`successGroup`）與剛被判錯的前一組（`replacedGroup`）」，由前端依 FR-036 決定；不需要「排在搶答成功者之前」的判準（2026-11-24 澄清已改為只留最近一次被替換的一組）。
  - `displayStatus` 在定案前名次 1 為 `SUCCESS`（搶答成功），定案後改為 `CORRECT`（搶答正確）；`replacedGroup` 是 `RoundReview` 保存的「被替換的搶答成功者」（題號 → 組號），判錯當下該組是搶答成功者才設定，該題下一次判錯、撤銷或定案時失效。
- **理由**：使用者 2026-11-24 的決定是「公開」＝資料開放查詢、畫面限縮，且 OpenSpec 要求公開候選順位與判錯標記；因此學生資料可含他組的順位與狀態，但不含理由與他組成功次數（spec FR-036、SC-010）。學生資料與組別無關（本組成功次數沿用 001 的 `ownGroup.successCount`），所以所有學生可共用同一份快取（研究 R14）。
- **風險（已知取捨）**：限縮只在畫面，懂得看 WebSocket 或 `GET /snapshot` 的學生仍能看到他組的順位與狀態。這是使用者明確選擇的設計，OpenSpec 規定的就是公開，因此接受。
- **考慮過的替代方案**：伺服端只給學生畫面需要的子集。這會使「資料公開」與 003 已公開所有組答案的現況不一致，且 OpenSpec 要求公開候選順位，所以不採用。

## R7 定案路由：取代 001 預留的空定案

- **決定**：在 `adapters/web/ranking_review.py` 提供 `POST /api/activities/{code}/rounds/current/finalize`，本文必須含 `resultVersion`；同時從 `adapters/web/http_api.py` 移除 001 的同路徑空實作。`ActivityService.finalize` 方法本身不改（004 與測試仍可呼叫）。
- **理由**：001 http-api.md 的第 8 項寫明「`{}`（004 會擴充）」；兩個路由並存會讓任何人以空本文不經 004 定案，造成成功次數與結果不一致（FR-020）。
- **對既有測試的影響**：使用 `POST .../finalize` 搭配 `{}` 的測試（約 4 個檔案：`test_http_close_finalize.py`、`test_us4_close_finalize.py`、`test_us5_end_cancel.py`、`test_us5_published.py` 等）要改用共用 helper：先取得該輪 `ranking.resultVersion`（或直接用 1，因為沒有判錯時初始版本為 1），再送 `{"resultVersion": n}`。tasks 列為獨立任務，測試的驗證意圖不變。
- **冪等**：004 保存 `FinalizedResult`；已定案且 `resultVersion` 相同時直接回覆既有結果，不再呼叫 001（001 對已定案輪次會以階段不符拒絕）。

## R8 判錯 API：以 PUT 設定狀態

- **決定**：`PUT /api/activities/{code}/rounds/{round}/questions/{q}/groups/{g}/judgement`，本文 `{"wrong": true|false}`；回應含 `changed`、`resultVersion`、`affectedQuestions`。
- **理由**：「設定狀態」語意天然冪等，重送、重複判錯、重複撤銷都回 `changed=false` 且版本不變（FR-025）。路徑含輪次，使過期頁面（輪次不是目前輪）可以被拒絕（spec edge：輪次已過期或不是目前輪）。
- **不需要**：原因欄位（FR-034）、請求 `Idempotency-Key`（狀態設定本身冪等）。

## R9 理由與排序規則（演算法）

- **排序鍵**：候選排序鍵一律 `(received_at, sequence)`；公平模式前面再加「處理當下的成功次數」，即 `(count, received_at, sequence)`。`sequence` 全活動唯一，所以鍵永遠分得出先後（FR-017）。
- **理由分類**（對每個候選，與「排在它前一名的候選」比較；第一名與第二名比較）：

  | 情況 | 理由 |
  |---|---|
  | 沒有比較對象（唯一候選） | `SOLE_CANDIDATE`（唯一候選） |
  | 速度模式，接收時間不同 | `EARLIER_SUBMISSION`（提交較早） |
  | 公平模式，成功次數不同 | `FEWER_SUCCESSES`（成功次數較少） |
  | 公平模式，次數相同、接收時間不同 | `EARLIER_SUBMISSION` |
  | 時間（與次數）都相同 | `BACKEND_ORDER`（以後端接收先後決定） |

  OpenSpec 兩個公平模式 Scenario 的對照：題一甲因提交較早（次數 0 比 0、甲較早）、題二乙因成功次數較少（乙 0、甲 1）、完全同次數同時間以序號決定。`SOLE_CANDIDATE` 是 spec「理由分類至少包含…」之外新增的一類，spec FR-008 已補上。
- **被判錯的候選**：沒有名次與理由，排在該題有名次者之後，依 `(received_at, sequence)`。

## R10 受影響題目的判定

- **決定**：`diff(old, new)` 逐題比較 `QuestionRanking`（成功者、所有候選的 `(group, rank, countAtProcessing, reason, wrong)`），任何一項不同就算受影響。回傳題號集合；初始結果（版本 1）沒有「上一版」，`affectedQuestions` 為空。
- **理由**：spec FR-016「順位、搶答成功者或理由有變者」；把判錯標記的改變一併納入，是因為標記改變必然使該筆提交的名次改變（有名次 ↔ 無名次）。
- **標示壽命**：只對應最近一次實際變更（Clarifications 第 2 題）：`affectedQuestions` 存在 `RoundReview` 裡，下一次實際變更時覆蓋，定案後 `ranking` 不再輸出（`final=true` 時為空）。

## R11 純函式邊界與型別

- **決定**：核心用自己的 `Candidate(group_number, question_number, received_at, sequence)`，不匯入 003 的 `Submission`；由 `RankingService` 把 003 的 `Submission` 轉成 `Candidate`。核心型別都是 `@dataclass(frozen=True)`，集合用 `tuple`／`frozenset`／`MappingProxyType`。
- **理由**：排名只需要這四個欄位；核心不依賴另一個子功能的核心，003 日後改欄位不會牽動 004 的純函式。`tests/architecture/test_core_is_pure.py` 已涵蓋整個 `core/`。
- **時間**：核心完全不取得現在時間；順位只比較已保存的 `received_at`。

## R12 驗證與錯誤碼

| 代碼 | HTTP | 條件 | 訊息（語意） |
|---|---|---|---|
| `INVALID_REQUEST` | 400 | 本文不是物件、缺欄位、`wrong` 不是布林、題號或組號不是正整數 | 請求格式不正確 |
| `NOT_TEACHER` | 403 | 不是該活動老師（含學生、其他活動老師、匿名） | 需要這個活動的老師身分才能操作 |
| `ACTIVITY_NOT_FOUND`／`ACTIVITY_GONE` | 404／410 | 活動代碼不存在；帶 token 時回 410（活動可能已因後端重啟失效），否則 404（沿用 001 `unwrap` 的規則與訊息） | 找不到這個活動代碼 |
| `ROUND_NOT_FOUND` | 404 | 輪次編號不存在 | 找不到這一輪 |
| `SUBMISSION_NOT_FOUND` | 404 | 該輪該題該組沒有已接受的提交 | 找不到這筆提交，請重新整理後再操作 |
| `ROUND_STILL_OPEN` | 409 | 目前輪仍在搶答中 | 本輪尚未關閉，無法判錯 |
| `NO_ROUND` | 409 | 活動還沒有任何輪次 | 目前沒有可判錯的輪次 |
| `STALE_ROUND` | 409 | 指定的輪次不是目前輪，且該輪尚未定案（理論上不會發生，為防禦） | 輪次已更新，請重新整理 |
| `RESULT_ALREADY_FINAL` | 409 | 該輪已定案（判錯、撤銷、不同版本的確認） | 本輪已定案，不能再修改（附定案版本） |
| `ACTIVITY_CANCELLED` | 409 | 活動已取消 | 活動已取消 |
| `STALE_RESULT_VERSION` | 409 | 確認的 `resultVersion` 不是最新 | 結果已更新，請重新檢視後再確認 |
| `FINALIZE_REJECTED` | 409／依 001 | 001 拒絕定案（階段剛好變動等） | 定案未生效，請重新整理後再試（附 001 的訊息） |

錯誤格式沿用 `{"error": {"code", "message"}}`；訊息不含堆疊、路徑、token。階段判定順序見 `data-model.md`。

## R13 日誌

只記 `activity`、`round`、`question`、`group`、`wrong`、`changed`、`version`、結果碼；不記答案內容、token、憑證（FR-032）。每個請求的通用日誌由 `RequestLogMiddleware` 處理，004 以 `annotate_request_log(request, result=..., version=...)` 補欄位。

## R14 效能與快取

- **重算成本**：一次整輪重算的運算量為「題數 × 該題候選數的排序」，上限約 50 題 × 99 組；以 `perf` 測試量測，不事先假設數值（SC-004）。
- **推送成本**：`snapshot_for` 對每條連線各呼叫一次擴充函式。學生資料與組別無關，老師資料只有一份，所以 `ReviewStore` 為每個 `(輪次, 結果版本, 角色種類)` 快取序列化後的 JSON 片段（版本變了就失效），避免 13～41 條連線各自重算同一份結果。
- **快照大小**：`ranking` 含所有已關輪輪次；每輪每題每候選一筆小物件，最大規模約 50 × 99 筆，遠小於 003 的 `published`（含答案原文）。若 20 組量測顯示明顯變慢，後續可改成只送目前輪並提供 GET 查詢舊輪（YAGNI，先量測再決定）。

## R15 測試策略

- 每個 Acceptance Scenario、OpenSpec Scenario 各至少一個測試，對照寫進 `tests/SCENARIO_MAP.md`。
- 核心：純資料測試，涵蓋 OpenSpec 公平／速度範例、確定性（同輸入 100 次）、回到原判錯集合結果相同（SC-003）、跨題連動、全部判錯、兩組不同題數配置（A：4 題；B：5 題含題組，且含無提交題）。
- 服務：真 `ActivityService` + `FakeClock` + `FakeSubmissionReader`（不呼叫 003 內部），涵蓋階段拒絕、權限、併發（兩個判錯同時、判錯與定案同時）、001 拒絕定案。
- 負對照：故意讓「不重算而累加」的錯誤實作應使 SC-003 測試失敗（在測試中以參數化的錯誤實作驗證測試有鑑別力）。
- 不呼叫真實 LLM、Google 或任何外部服務；效能測試標記 `perf`，使用本機真實 uvicorn。

## R16 跨子功能協調事項

| 對象 | 項目 | 處理 |
|---|---|---|
| 001 | 移除空的 finalize 路由、更新 `contracts/http-api.md` 第 8 項 | 004 的 PR 內一併完成，PR 說明列出影響範圍；既有測試改用 helper |
| 003 | 公開版資料的 `judgedWrong` 預留欄位一律 `false` | 004 不改 003 的資料與後端；前端不使用該欄位（003 前端只在其為 true 時顯示「答錯」，佔位值不會誤標）；是否移除留給 003 整理，tasks 列為待辦提醒 |
| 003 | 003 學生頁「已公開的作答」列出全部組答案（renderPublished） | 004 實作時改由 004 結果區塊呈現（spec FR-037）；只改 003 的前端與其測試，不改 003 的資料公開範圍；列入 004 tasks |
| 003 | 003 FR-024 寫「順位在關輪後由 004 標示『未定案』」 | 004 以活動階段「結果未定案／結果已定案」呈現（spec FR-031），不在每題標示；已記在 spec Traceability |
| 005 | 讀取定案結果 | 以 `RankingReader.finalized_rounds(code)` 唯讀提供，見 contracts/service-interfaces.md |
| 002 | 無 | 題號清單經 001 的輪次規則取得 |
