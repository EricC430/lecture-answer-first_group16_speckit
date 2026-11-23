# Research: 多題搶答與送出

**Date**: 2026-11-23 ｜ **Spec**: [spec.md](spec.md) ｜ **Plan**: [plan.md](plan.md)

Technical Context 沒有 NEEDS CLARIFICATION；以下是設計決策。每項格式為「決策／理由／考慮過的替代方案」。

## R1 提交資料存在哪裡

- **決策**：存在 003 自己的 `SubmissionStore`（`app/round_submission/store.py`，記憶體 dict：活動代碼 → `SubmissionLedger`）。`SubmissionLedger` 是不可變物件（`core/round_submission/models.py`），包含全部提交與下一個接收序號；每次接受時以新物件取代。
- **理由**：001 的 `Activity` 不需要知道答案；001 核心不依賴 003，模組邊界清楚。不可變 ledger 讓 `decide` 成為純函式，測試只需組資料。
- **替代方案**：把提交放進 001 的 `Activity`（001 核心要匯入 003 型別，相依方向變成 001 → 003，否決）。

## R2 原子性：判定、標記、保存與關輪互斥

- **決策**：001 新增 `ActivityService.record_submission(code, device_token, handler)`。在 **001 的同一把活動鎖內**依序：
  1. 依 token 找裝置與組號（找不到 → `NOT_IN_GROUP`；活動不存在 → `ACTIVITY_GONE`）。
  2. `now = clock.now()`（只取一次）。
  3. 組成 `SubmissionWindow`（組號、階段、目前輪次編號、本輪開放題、截止時間、`accepting = 搶答中且 now < 截止時間`）。
  4. 呼叫 `handler.decide(window, now)`（003 讀 ledger、呼叫純函式 `SubmissionRules.decide`）。
  5. 若結果是「接受」：套用新的核心指令 `RecordSubmission(System, group_number)`（只在搶答中且 `now < 截止時間` 生效，標記 `has_submissions`，**每次都算變更** → `revision + 1`，`version` 不變）；套用被拒時不保存、回傳拒絕。
  6. 套用成功後呼叫 `handler.commit()`（003 把新 ledger 寫入 store）。
  7. 釋放鎖後推送（`SyncPublisher.publish`）。
- **理由**：關輪、倒數截止、刪除組別都走同一把鎖，因此「提交」與「關輪」一定有先後；保存發生在鎖內，結果公開（關輪後推送）之前一定已經包含或拒絕這筆提交（FR-019）。001 契約要求的「先標記、成功才寫入」由這個順序保證（FR-013）。`RecordSubmission` 每次都遞增 revision，老師頁才能用（version, revision）分辨新舊快照。
- **替代方案**：
  - 003 自己的鎖 + 呼叫既有 `mark_group_submitted`：`mark_group_submitted` 第一次標記時會在鎖外 `await publish`，讓出執行權，關輪可能插在「標記」與「保存」之間 → 結果公開後才保存提交，違反 FR-019。另外同組第二題以後的標記「沒有變化」，不會遞增 revision，老師頁會丟棄內容不同但版本相同的快照。否決。
  - 讓 001 公開它的鎖給 003：鎖的生命週期與推送時機分散在兩個服務，容易出錯。否決。
- **相容性**：`mark_group_submitted` 保留不動（契約仍有效），003 不再直接呼叫。001 既有測試不需修改。

## R3 接收時間與接收序號

- **決策**：接收時間＝R2 第 2 步的 `now`（後端 `Clock`，UTC、毫秒以上精度）。接收序號存在 `SubmissionLedger.next_sequence`，活動建立後第一筆為 1，**只在接受時**遞增，跨輪次延續、不重設。排序鍵（`received_at`, `sequence`）。
- **理由**：同一個 `now` 同時用於截止判定與記錄，邊界一致；序號跨輪遞增讓「唯一遞增」在整個活動成立（FR-016）。被拒的嘗試不消耗序號，序號沒有跳號，方便人工核對。
- **替代方案**：每輪重設序號（輪內唯一即可，但跨輪比較與匯出時容易混淆，否決）；以 `time.monotonic` 排序（核心不能讀時鐘，否決）。

## R4 提交資料如何併入快照

- **決策**：001 新增 `SnapshotExtension` Protocol 與 `ActivityService.add_snapshot_extension(ext)`；`snapshot_for` 由靜態方法改為實例方法：先由 001 `SnapshotView` 產生快照，再依序呼叫擴充函式 `ext(activity, viewer)`，把回傳的欄位併入 `extra`。`viewer` 是 `TeacherViewer` 或 `GroupViewer(group_number)`。`WebSocketHub._push` 改呼叫 `self._service.snapshot_for(...)`。003 註冊的擴充函式回傳：
  - 老師：`submissions`（本輪看板 + 已公開輪次）、`questionShapes`（各題格數）。
  - 學生：`submissions`（本輪只有本組；已公開輪次全部）、`questionShapes`（只有本輪開放題的格數）。
- **理由**：沿用 001 的快照、hub 去重（內容相同不送）、重連取完整狀態與版本排序，不需要第二條通道；學生版只含本組資料，他組提交不會改變本組快照內容，所以 hub 不會推送（FR-022、001 FR-030）。
- **替代方案**：另開提交專用 WebSocket 訊息（前端要合併兩個來源、版本規則重做，否決）；在 001 `SnapshotView` 直接讀 003 資料（001 核心依賴 003，否決）。

## R5 版本規則

- **決策**：提交被接受＝老師可見變更 → `revision + 1`、`version` 不變（R2 的 `RecordSubmission`）。學生快照的 `version` 不變，但提交組自己的快照內容變了，前端 `sync.js` 對同版本的快照照常套用（現行邏輯只丟棄 `version` 較小者），同一條 WebSocket 上的訊息有序，因此同組另一台裝置會在 2 秒內看到。關輪是公開變更（`version + 1`），所有人收到包含公開提交的快照。
- **理由**：完全沿用 001 FR-027／FR-030，不新增欄位。
- **替代方案**：給學生快照加 `ownRevision`（現行有序通道已足夠，留待需要時再加）。

## R6 每題子空格數的來源

- **決策**：003 定義 `QuestionShapeSource` Protocol：`blanks_per_question(code) -> Mapping[int, int] | None`（題號 → 格數；尚未成功匯入時為 `None`）。由 002 的 `ImportService` 實作（`ImportRecord.blanks` 依題號計數；已與 EricC430 口頭協調）。002 合併前：`dev_seed` 的 seed 可指定每題格數，並提供 `DevQuestionShapeSource`；只在 dev seed 啟用時組裝。
- **理由**：格數一律來自匯入結果（憲章原則 III）；重新匯入只在第一輪前，搶答中格數不變。
- **替代方案**：001 的 `replace_questions` 改傳格數（改動 001 與 002 已對齊的契約，否決）；003 直接讀 002 的 `ImportRecord`（耦合 002 內部型別，否決）。
- **防禦**：開放題在 `QuestionShapeSource` 查不到格數時，`decide` 回 `QUESTION_NOT_OPEN` 並記錄 WARNING（不應發生，代表 002／001 資料不一致）。

## R7 HTTP API 形狀

- **決策**：`POST /api/activities/{code}/submissions`，`Authorization: Bearer <裝置 token>`，本文 `{"roundNumber": int, "questionNumber": int, "answers": [str, ...]}`（多送的欄位一律忽略，前端時間不影響判定）。
  - 接受：`201`，`{"result": "accepted", "submission": {...}}`。
  - 本組已送出（含重送）：`200`，`{"result": "alreadySubmitted", "submission": {...既有}}`。
  - 拒絕：沿用 001 的錯誤格式（`common.py`），`error.code` 為 `SubmissionRejection` 值。
  - 不使用 `Idempotency-Key`：重送本來就會走「本組已送出」，不會產生第二筆。
- **理由**：「本組已送出」不是錯誤，前端要顯示既有答案，以 200 回傳較直接；其他狀況沿用 001 錯誤處理與日誌中介層。
- **替代方案**：`409 ALREADY_SUBMITTED` 附資料（001 錯誤格式不帶業務資料，否決）。

## R8 答案規則（Q-20 提議，集中可調）

- **決策**：`core/round_submission/answer_rules.py` 集中：`MAX_ANSWER_CHARS = 500`（以 Python 字元數計）；判空時去除的空白＝`str.strip()` 的空白（含全形空白 U+3000、Tab、換行）；保存原文；允許 `\n`、`\r\n`。答案不是字串 → `INVALID_ANSWER`；格數不符 → `WRONG_BLANK_COUNT`（附需要格數）；有空格 → `BLANK_EMPTY`（附全部空格的格號）；超過上限 → `ANSWER_TOO_LONG`（附格號）。同時有空格與超長時，先回報空格。
- **理由**：OpenSpec 組 2026-11-23 已同意；若日後再改，只需改這一個檔案與對應測試。
- **替代方案**：字數以位元組計（中文 3 位元組，與使用者感受不符，否決）。

## R9 Q-22 與 001 學生快照的成功次數

- **現況**：001 學生快照的 `ownGroup.successCount` 一直顯示本組成功次數；003 原本的 Q-22 提議是「搶答中看不到本組成功次數」，兩者衝突。
- **決策（2026-11-23 jacky0407 選 B）**：修正 Q-22 提議為「搶答中學生可看本組成功次數（沿用 001），看不到排名與他組任何資訊」。001 不需修改；003 spec Clarifications、US4-AS3、FR-021 與 alignment.md 同步修正。`view.py` 的 `STUDENT_SEES_OWN_SUCCESS_DURING_ROUND = True`；OpenSpec 組若要求隱藏，改為 `False`，由 003 快照擴充覆寫 `ownGroup.successCount = null`。
- **理由**：OpenSpec 原文只要求學生看不到他組資料，沒有要求隱藏本組資料；沿用 001 改動最小。
- **替代方案**：搶答中隱藏本組成功次數（要改 001 學生快照與 001 spec，否決）。

## R10 判定順序與拒絕原因

- **決策**：`SubmissionRules.decide` 依下列順序，第一個不符合的條件決定結果（data-model.md 有完整表）：
  1. 輪次識別不是整數，或不等於目前輪次 → `STALE_ROUND`（沒有任何輪次時亦同）。
  2. `accepting` 為假（不在搶答中、已截止、已關輪）→ `ROUND_CLOSED`。
  3. 題號不是整數或不在本輪開放題 → `QUESTION_NOT_OPEN`。
  4. 本組本輪本題已有提交 → `ALREADY_SUBMITTED`（附既有提交）。
  5. 答案內容（R8）。
  6. 接受，產生 `Submission`（序號 = `next_sequence`）。
- 身分與活動存在性在 001 `record_submission` 的第 1 步處理（`NOT_IN_GROUP`、`ACTIVITY_GONE`），沒有到 `decide`。
- **理由**：舊頁面送出時先提示「輪次已更新」比「本輪已結束」更有用；已送出優先於內容檢查，學生重送無效內容時看到的是既有答案（US2-AS4）。
- **注意**：學生停在第 1 輪頁面、第 1 輪已關閉但第 2 輪還沒開時，輪次識別等於目前輪次 → 回 `ROUND_CLOSED`「本輪已結束」，符合 US3-AS3。

## R11 關輪公開與歷史輪次

- **決策**：`SubmissionView` 的「公開輪次」＝輪次編號小於目前輪次，或等於目前輪次且階段不是 `ROUND_OPEN`。公開輪次對所有角色顯示全部組的提交（依排序鍵）與「無人提交」旗標；本輪開放中只對老師全部顯示、對學生只顯示本組。每題的 `noSubmission: true` 即畫面「未成功」；「候選皆被判錯」的未成功由 004 擴充。
- **理由**：單純以階段判斷，不需要額外狀態；所有輪次的資料都在 ledger。
- **Q-26 預留**：公開版每筆提交保留 `judgedWrong` 欄位，003 一律為 `false`，由 004 提供真值；`STUDENT_SEES_JUDGED_WRONG = True` 常數控制學生是否看得到。

## R12 前端

- **決策**：新增 `static/js/submission.js`：
  - `renderAnswerForm(question, blanks)`：每格一個 `<textarea>`（允許換行、`maxlength=500` 只是提示，後端才是準）；送出期間停用按鈕；只有收到 2xx 才顯示「已送出」；網路錯誤或逾時顯示「送出結果未確認，請重試」。
  - `renderOwnSubmissions`、`renderBoard`、`renderPublished`：一律 `textContent`／`createElement`，不使用 `innerHTML`。
  - 倒數沿用 001 `countdown.js`（依快照的 `deadline` 推算）；沒有截止時間時顯示「由老師結束」；歸零後停用送出按鈕。
- **理由**：沿用 001 的頁面結構與 `api.js`／`sync.js`；文字安全集中在一個檔案。

## R13 日誌

- **決策**：`SubmissionService` 以 INFO 記錄 `activity=… round=… question=… group=… result=accepted|alreadySubmitted|<rejection>`，不含 token、不含答案內容；請求日誌沿用 001 `RequestLogMiddleware`（只記路徑模板與狀態碼）。
- **理由**：憲章原則 V；答案可能含個資或惡意字串，不寫入日誌。

## R14 測試策略

- **核心單元測試**：`decide` 的每個順序分支、R8 的每條規則（含全形空白、換行、恰好 500／501 字）、排序（同時間不同序號）、`SubmissionView` 三種版本（學生版不含他組任何欄位）。
- **服務測試**：真的 `ActivityService` + `FakeClock` + 假 `QuestionShapeSource`；
  - 同組兩台裝置 `asyncio.gather` 同時提交 × 50 次 → 只保存 1 筆（SC-002）。
  - 關輪與提交 `gather` × 50 次 → 公開結果中不會出現關輪後保存的提交（SC-004）。
  - 截止邊界：`deadline - 1ms` 接受、`deadline` 與 `deadline + 1ms` 拒絕。
  - 兩份版面格數配置（A：[2,2,1,1]；B：[1,3,1,2,1]）。
- **契約／整合測試**：HTTP 狀態碼與本文；WebSocket：他組提交時本組收不到訊息（沿用 001 `test_fr030_student_push.py` 的寫法）、同組另一台收到、老師收到、關輪後全部收到公開資料；含 HTML 的答案原樣出現在 JSON（前端 `textContent` 由人工驗證與 quickstart 檢查）。
- **效能**：`tests/perf/test_submission_latency.py`，老師 + 6 組 × 2 連線，20 次提交，量測到老師與同組另一台裝置收到快照的時間 < 2 秒（SC-006）。
- **真實路徑**：002 合併後，以兩份真實 Google 學習單匯入（002 的路徑）→ 開輪 → 提交 → 關輪，記錄在 `verification.md`；由 EricC430 人工驗證。
