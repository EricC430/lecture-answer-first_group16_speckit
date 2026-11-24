# Specification Quality Checklist: 順位計算、判錯重算與定案（Ranking Review）

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Constitution / Project Gates

- [x] OpenSpec Traceability 涵蓋 ranking-review 全部 7 條 Requirement、12 個 Scenario（原則 I）
- [x] alignment.md 無待確認項影響本 spec；組別一律以組號識別（Q-07 已決議）
- [x] 三張圖（組件、類別、時序）已產出並轉出 PNG，檔名以 004 開頭，已開啟檢視（原則 II）
- [x] 順位計算為純函式的架構限制已寫入 Assumptions 與 FR-017（技術限制 4）
- [x] 原則 III／VI 的 Google 項目不適用於 004，理由已寫在 Assumptions；改以 SC-009 人工驗證

## Notes

- 初次驗證（2026-11-22）：由 specify 作者逐項檢視 spec.md；未經獨立審查。
- 更新驗證（2026-11-24）：依已合併的 001（contracts、data-model、實作）、003（spec、contracts、data-model、research、tasks、實作）、005 spec、002 實作與 alignment.md 2026-11-23 決議重新核對 spec；同樣只由 specify 作者逐項檢視，建議 `/speckit-clarify` 前由另一位組員讀過。
- 本次更新的 spec 變更：(1) 新增公開結果顯示狀態「搶答成功／答錯／搶答失敗／未成功」與「老師只需判到第一個未被判錯者、判錯免填原因」（FR-033、FR-034、US4-AS7／AS8、US5-AS8、US7-AS11～AS13；OpenSpec 組 2026-11-23 已確認）；(2) 新增 FR-035：003 公開資料與 004 結果必須是同一輪、同一結果版本；(3) 修正對 001、003 的相依描述（`current_round`、`FinalizeOutcome` 以組號為 key、重複定案由 004 自行回覆、`SubmissionReader.round_submissions`、結果版本與 001 狀態版本獨立）；(4) 組號與組數上限引用改為 alignment 2026-11-23 A1／A2（1～99）；(5) 效能驗證規模改為 001 的老師加 6 組、每組 2 條連線；(6) 判錯請求的階段名稱改用 001 的「結果未定案」，並補各階段拒絕訊息、離開本組／刪除空組、關輪原因、長答案與多行答案的 edge cases；(7) 圖表同步（DisplayStatus、FinalizeOutcome、`roundSubmissions`、結果擴充）並重新轉出 PNG。
- 已知文件不一致（不在本 spec 修改範圍）：各分支的 alignment.md 版本不同，003 分支與 002 實作分支的待確認表仍殘留 Q-23～Q-26 列，合併時需清理；003 FR-024 寫「順位在關輪後由 004 標示『未定案』」，本 spec 以活動階段「結果未定案」呈現（FR-031），不在每題標「暫定」。
- Clarify 第 1 題（2026-11-24）：結果資料公開查詢（不含勝出理由與他組成功次數），畫面依角色限縮（老師完整候選情況；學生只看本組狀態、答錯組別與搶答成功者），新增 FR-036、US7-AS4～AS6，User Story 7 的情境重新編號（原 AS4～AS10 改為 AS7～AS13）。所有檢查項重新對照後仍全數通過（21/21）。
- Clarify 第 2 題（2026-11-24）：「結果更新」標示只對應最近一次變更、定案後不再標示、不記錄誰看過；FR-016 補充，新增 US5-AS6，原 US5-AS6／AS7 改為 AS7／AS8。檢查項仍全數通過（21/21）。
- Clarify 第 3 題（2026-11-24）：SC-004 以自動化效能測試驗證，6 組為必過門檻，另量一次 20 組只記錄結果、不當合併門檻。檢查項仍全數通過（21/21）。
- 整合（2026-11-24）：jacky0407 另外在 PR #20（`feature/8-004-ranking-review`）提交了 004 的 specify／clarify 與 alignment 2026-11-24 決議列（Q-23、Q-24、Q-25）。本版以 EricC430 的 spec、plan 與設計文件為基底，併入 jacky0407 的 Q-23／24／25 決定與「結果已更新」用詞、跨能力 Traceability 列、速度模式不看成功次數的情境、撤銷後版本遞增與定案回應遺失重送的 edge case、兩頁同時確認的 SC。已合併 main（含 PR #11、#19，憲章 v1.1.0 已在 main）。
- 與 jacky0407 版本的差異（已於 2026-11-24 與 jacky0407 確認，三項都採 EricC430 的決定）：他的 spec 寫學生也看得到勝出理由與全部候選；本版依 EricC430 2026-11-24 的決定，學生資料不含勝出理由與他組成功次數，學生畫面只顯示本組狀態、答錯組別與搶答成功者（FR-036）。用詞也依 EricC430 2026-11-22 的決定統一為「搶答成功者」，不使用「暫定勝者」「勝者」；「未定案」以活動階段「結果未定案／結果已定案」呈現（FR-031）。
- 再次核對（2026-11-24，003 合併到 main 後）：自合併 main（79ec0ee）以來 main 只新增 003（PR #16）、CLAUDE.md 與 docs/DEVELOPMENT.md、alignment.md 的 003 決議列；001 與 002 的 spec／契約沒有新變動，憲章仍是 v1.1.0，OpenSpec 基準檔沒有變。spec 的調整：003 改為已合併、移除「該列在 003 分支」的說明、新增 FR-037（學生頁不得逐組列出全部組作答；003 目前的學生頁需配合調整）。plan 的調整：依 DEVELOPMENT.md 3.5「快照擴充函式必須是無副作用的純讀取」，初始結果改為由純計算導出、第一次判錯才建立並保存（研究 R2），並在研究 R5、R16 補上 003 學生頁需調整。alignment.md 已合併 003 的決議列與 jacky0407 的 2026-11-24 列（保留兩邊）。檢查項仍全數通過（21/21）。
- Clarify（2026-11-24，/speckit-analyze 之後）：問了 2 題。(1) 關輪後第一組立即顯示「搶答成功」，老師判錯後由下一組遞補，定案後「搶答成功」變「搶答正確」（新增狀態，定案以整輪為單位；US7-AS14、FR-031、FR-033、SC-010）；(2) 學生畫面每題顯示「目前的搶答成功者」與本組自己的狀態；老師把搶答成功者判錯而由下一組遞補時，剛被判錯的前一組（答案與「答錯」）與遞補者一起顯示給所有組，該題下一次判錯、撤銷或定案時被取代或移除（只留最近一次被替換的一組，新增實體「被替換的搶答成功者」）；整題無搶答成功者時只顯示「未成功」與本組狀態（FR-036、FR-037、US7-AS3、AS4、AS9、AS11、AS14）。因此 analyze 的 A1（「之前」的判準）與 A2（無搶答成功者時顯示哪些組別）已解除。檢查項仍全數通過（21/21）。
- 待同步（spec 以外）：plan、research R6、data-model（`DisplayStatus` 新增 `CORRECT`＝搶答正確、定案後才有）、contracts/sync-websocket.md（`displayStatus` 值、學生版說明，以及每題新增 `replacedGroup`：最近一次被替換的前一位搶答成功者組號或 `null`，判錯／撤銷／定案時更新，`RoundReview` 需保存）、類別圖，以及 tasks（T009、T028、T033、T061、T071、T076、T094 與 quickstart 步驟 5～7）需依本次澄清更新。
- Clarify 第 3 題（2026-11-24）：老師「依候選順序判錯、到正確的為止」只在老師介面限制（每題只對目前的搶答成功者提供「判錯」、只對最近一次被替換的那一組提供「撤銷判錯」），系統與 API 仍允許對任一提交判錯，OpenSpec 組認同、無偏離、不列入 alignment.md（FR-034、新增 US4-AS9）。檢查項仍全數通過（21/21）。待同步：tasks T052（老師按鈕只對目前搶答成功者顯示）、quickstart 步驟 5～8、T094。
- 同步（2026-11-24，澄清與 /speckit-analyze 之後）：已把 `搶答正確`（`DisplayStatus.CORRECT`）、`replacedGroup`（被替換的搶答成功者）、老師介面判錯順序與學生畫面新規則同步到 plan（含 Constitution Check VII、結構與 Complexity Tracking 補上對 003 學生頁的調整）、research R5／R6、data-model、contracts（sync-websocket、service-interfaces）、三張圖、quickstart 步驟 3～10 與 tasks（T005、T009、T011、T028、T033、T043、T049、T052、T055 移到 US4、T058、T061、T064、T068、T071、T076、T094，新增 T095 與 FR／SC 對照表，每個 Story 的 Checkpoint 前執行 lint 與 mypy）。analyze 的 A1、A2、I1、I2、I3、C1、I4、U2、U3 已處理。檢查項仍全數通過（21/21）。
- 第 2 次 /speckit-analyze 後的修正（2026-11-24）：A1 撤銷改為「退回上一步」（`RoundReview.replaced` 改為依判錯順序的歷程；spec 新增 US4-AS10、澄清一條）；U2 T047 補「API 對非搶答成功者判錯仍回 200」並在 http-api.md 註明；I1 關鍵實體「被替換的搶答成功者」改為也用於老師介面的撤銷；I2 T094 改為「四項前端專屬檢查」；U1 把「哪些按鈕要顯示」放進老師版快照 `actions.{judgeGroup, undoGroup}`（核心純函式產生並測試，前端只照顯示，T028、T033、T052）。檢查項仍全數通過（21/21）。
- 第 3 次 /speckit-analyze 後的修正（2026-11-24）：I1 快照快取鍵加入「是否定案」（定案不增加結果版本卻改變輸出；data-model、research R2／R14、T006、T012、T034，並在 T061 加「定案前後同版本但快取內容必須更新」的測試）；U2 data-model 補 `RoundReview` 不變式（`replaced` 歷程的每一組都在該題 `wrong_marks` 內、無重複），T043 以任意操作序列的參數化測試驗證；D1 T028 精簡，`actions` 的定義只留一處。檢查項仍全數通過（21/21）。
