# Phase 1 資料模型：002-guided-notes-import

**日期**：2026-11-22 | **對應**：[plan.md](plan.md)、[research.md](research.md)、[類別圖](../../diagrams/002-guided-notes-import-class.puml)

所有型別以名稱對應類別圖。核心層的型別都是不可變的資料類別（`@dataclass(frozen=True)`），只用標準函式庫；座標一律是 0 起算的（列, 欄）。

## 核心層（`core/guided_notes_import/`）

### 輸入：工作表快照

| 型別 | 欄位 | 說明 |
|---|---|---|
| `CellRef` | `row: int`、`col: int` | 一個儲存格位置 |
| `CellValue` | `number: float \| None`、`text: str \| None`、`display: str` | 來自 `effectiveValue.numberValue`／`stringValue`；`display` 取 `formattedValue`，只用於訊息引用。布林、錯誤值、公式結果不是數字也不是文字時，`number` 與 `text` 都是 `None`、`display` 保留原樣 |
| `MergeRange` | `first_row`、`first_col`、`last_row`、`last_col`（皆含） | 由 `GridRange` 轉換；結束索引為「不含」，轉接層轉成「含」（⚠ 待真實驗證，research R3） |
| `SheetSnapshot` | `spreadsheet_id`、`sheet_id`、`sheet_name`、`row_count`、`col_count`、`cells: Mapping[CellRef, CellValue]`、`merges: tuple[MergeRange, ...]` | 只含有內容的儲存格；列欄總數用來判斷「右側沒有儲存格」 |

### 輸出：解析結果

| 型別 | 欄位 | 說明 |
|---|---|---|
| `ParseResult` | `ok: bool`、`questions`、`blanks`、`structure: StructureSnapshot \| None`、`issues: tuple[ValidationIssue, ...]` | `ok` 為真時 `issues` 為空；`ok` 為假時 `questions`、`blanks`、`structure` 全空（原子，FR-016） |
| `Question` | `number: int`、`blank_count: int`、`is_group: bool` | 題組算一題（FR-018） |
| `Blank` | `question_number: int`、`sub_index: int \| None`、`target: CellRef` | 單題 `sub_index` 為空；`target` 是答案格（合併範圍的左上角），永遠不是編號格（FR-010） |
| `StructureSnapshot` | `header_number: CellRef`、`header_answer: CellRef`、`answer_cols: tuple[int, int]`、`data_start_row: int`、`merges: tuple[MergeRange, ...]`、`row_numbers: Mapping[int, int]`、`answer_cells: Mapping[tuple[int, int | None], CellRef]` | 匯入時結構，涵蓋 OpenSpec result-export「來源結構一致性檢查」所列：表頭位置、題號、子空格、相關合併範圍、答案格映射（試算表與工作表身分在 `ImportRecord.source`）。`merges` 只含與表頭列及資料區相交者 |
| `ValidationIssue` | `kind: IssueKind`、`at: CellRef \| None`、`quoted: str \| None`、`hint: str` | `at` 對缺表頭這類沒有位置的問題可為空；`quoted` 是被引用的儲存格文字（已截斷） |

`IssueKind`：`MISSING_HEADER_NUMBER`、`MISSING_HEADER_ANSWER`、`AMBIGUOUS_HEADER`、`NON_NUMERIC_NUMBER`、`NUMBER_GAP`、`NON_ADJACENT_DUPLICATE`、`SUB_INDEX_MISSING`、`SUB_INDEX_DUPLICATE`、`ORPHAN_SUB_BLANK`、`MISSING_ANSWER_CELL`、`TARGET_OVERLAP`。

**驗證規則（對應 FR）**：

| 規則 | FR | 說明 |
|---|---|---|
| 表頭只認「題號」「作答」，去首尾空白（含全形空白） | FR-006 | 不接受同義詞，不猜結構 |
| 缺表頭或多區塊 → 拒絕 | FR-007 | 指出缺哪個或歧義 |
| 題號正規化（research R5） | FR-013 | 數值 1.0、文字「1」皆為 1 |
| 題號從 1 起連續遞增 | FR-014 | 依出現順序 |
| 子編號從 1 起連續不重複 | FR-014 | 題組內 |
| 空白列忽略 | FR-026 | 不影響相鄰與連續 |
| 非相鄰重複、跳號、非數字、孤立子空格、缺答案格、目標重疊 | FR-015 | 全部收集後一起回報 |

### 不變量

- `ParseResult.ok` 為真 ⇒ `Question.number` 為 1..N 連續；每題的 `Blank` 數等於 `blank_count`；所有 `Blank.target` 兩兩不同。
- 沒有任何型別含題目敘述（FR-008）。
- 核心型別不含時間、不含 I/O，所以解析是確定性的：相同快照必得到相同結果。

## 應用層（`app/guided_notes_import/`）

| 型別 | 欄位 | 說明 |
|---|---|---|
| `SourceRef` | `spreadsheet_id: str`、`sheet_id: int` | 來源識別（FR-002） |
| `SpreadsheetInfo` | `spreadsheet_id`、`title: str`、`sheets: tuple[SheetInfo, ...]`、`auto_select_sheet_id: int \| None` | 檢視結果；`SheetInfo` 含 `sheet_id`、`title`、`hidden`（轉接層回報，服務濾除）。`sheets` 只含可見工作表（隱藏的不列入、不計張數，2026-11-23 澄清）。`auto_select_sheet_id` 由服務計算：`sheets` 恰好一張時為其 `sheet_id`，否則 `None`（FR-002） |
| `SourceSelection` | `source: SourceRef`、`sheet_title: str` | 老師選定的來源；取消選檔不寫入 |
| `ImportRecord` | `source: SourceRef`、`sheet_title: str`、`blanks: tuple[Blank, ...]`、`structure: StructureSnapshot`、`question_numbers: tuple[int, ...]`、`version: int` | 最後一次成功匯入；每次成功**整份取代**（FR-019、FR-024） |
| `ImportPreview` | `question_numbers`、`blanks_per_question: Mapping[int, int]`、`total_questions`、`total_blanks` | 題組只算一題；總格數累計子空格（FR-017、FR-018） |
| `ImportOutcome` | `ok: bool`、`preview: ImportPreview \| None`、`issues: tuple[ValidationIssue, ...]`、`rejection: ImportRejection \| None`、`version: int \| None`、`sheet_title: str` | 服務不拋業務錯誤（沿用 001 契約的風格） |
| `ImportRejection` | 列舉 | 見 [research.md](research.md) R8 |
| `GoogleSession` | `access_token`、`refresh_token`、`expires_at` | 只在記憶體；不進日誌。實際形態由轉接層決定，應用層只看到「是否已授權」 |
| `ImportStore` | `sessions`、`selections`、`records`、`locks` | 依活動代碼為 key 的四個字典；`locks` 是每個活動一把 `asyncio.Lock` |

### 狀態與轉換

```text
（無來源） --PUT source--> 已選來源 --import 成功--> 已匯入（ImportRecord）
     ^                        |                         |
     |                        +--import 失敗：維持原狀--+
     +-- 第一輪開始前（001 的 PREPARING、JOINING）才可重選／重新匯入；整份取代；第一輪開始後全部拒絕
```

- 「第一輪開始後」不由 002 維護，由 001 的 `stage(code)` 決定（research R6）。
- 失敗（授權、讀取、驗證、001 拒絕）一律不改動 `selections`（除 PUT source 本身成功時）與 `records`。

## 外層

- 轉接層型別（Google 回應、`HttpError`）**不得**出現在核心與應用層；轉接層負責轉成上述型別或 `ImportRejection`。
- 5 個 HTTP 回應型別見 [contracts/http-api.md](contracts/http-api.md)。
