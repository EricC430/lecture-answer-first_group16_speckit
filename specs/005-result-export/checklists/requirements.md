# Specification Quality Checklist: 定案成果寫回 Google Sheets 與 CSV 匯出

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-22
**Updated**: 2026-11-24（main 合併後重寫）
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

## Project-specific（憲章 v1.1.0）

- [x] OpenSpec Traceability 涵蓋 result-export 全部 6 條 Requirement、12 個 Scenario（原則 I）
- [x] 偏離或新增只有「取消的活動不提供寫回與 CSV」，已記於 alignment 2026-11-23（C8，OpenSpec 組同意）
- [x] 組件圖、類別圖、時序圖 .puml 與 PNG 已重新產出並目視檢查（原則 II）
- [x] 原則 III（動態定位、兩份版面驗證）、V（資料可見性、輸入驗證）、VI（Google mock、真實路徑、人工驗證）與純函式架構限制已明寫

## Notes

- 驗證方式：逐項對照 spec 內容（2026-11-24，人工閱讀；未執行自動化指令）。圖表以 `java -jar plantuml.jar` 只轉 005 的三個檔，並開啟 PNG 目視檢查。
- **2026-11-24 重寫的變更**（依已合併的 001～004 spec、contracts 與實作）：
  1. 取消的活動：原稿寫成「下載只含表頭的 CSV」，與 001 `export_view`（已取消一律拒絕）與 alignment C8 不符，改為拒絕預覽、寫回與 CSV（US1-AS7、FR-001、SC-006）。
  2. 資料來源改為各子功能實際提供的唯讀資料：004 已定案輪次（含全部候選名次與答錯標記）、003 全部輪次的有效提交（含未定案輪次，須過濾）、002 ImportRecord、001 匯出檢視（FR-023、Key Entities、Assumptions）。
  3. 結構比對：002 規定 005 以同一個 parse 重新辨識目前工作表後與保存的結構比對，補上「來源已無法辨識」也算不符（FR-007、US2-AS2、SC-003）。
  4. 用詞對齊 004：搶答成功者、答錯、搶答失敗；「是否被判錯」只在被老師判錯時為是（FR-025，依 alignment 2026-11-23 Q-28 的顯示方式）。
  5. 作答格內佔位文字：002 把「寫回是否覆寫」交給 005；決定為成功題取代（預覽顯示原內容）、未成功題保留（FR-012、US3-AS5）。
  6. Google 授權：沿用 002 授權；002 只申請 `drive.file`，是否足以寫入尚待真實驗證，列入 SC-009（FR-010、Assumptions）。
  7. 新增 edge case：一題跨多輪（先前無人成功後重新開放）。
- **alignment.md**：合併 main 後發現「待確認」表格被舊版合併帶回 Q-04～Q-33，與說明段（2da31dd 已縮減為只留 Q-07）不一致；已在本分支以獨立 commit 還原縮減版（只動待確認表格，決議紀錄與說明段不變）。因此沒有仍待確認的項目，spec 沒有 `[NEEDS CLARIFICATION]`。
- 「UTF-8」「CSV」「文字保護前綴」屬使用者可見的檔案行為，不視為實作細節；保護前綴的具體字元、授權範圍、檔名由 plan 決定。
- 分支與 Issue：Issue #9；分支 `feature/9-005-result-export`（已合併 `origin/main`）。
