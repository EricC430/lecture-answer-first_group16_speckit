# Phase 1 資料模型：005-result-export

**日期**：2026-11-24 | **對應**：[plan.md](plan.md)、[research.md](research.md)、[spec.md](spec.md)、[類別圖](../../diagrams/005-result-export-class.puml)

型別名稱對應類別圖。核心層的型別都是不可變的資料類別（`@dataclass(frozen=True)`），只用標準函式庫與 `lecture_quiz.core` 內的模組；座標沿用 002 的 `CellRef`（0 起算的列, 欄）。

## 核心層（`core/result_export/`）

### 輸入（由應用層從 001～004 的唯讀資料轉成，核心不匯入 app 型別）

| 型別 | 欄位 | 來源 | 說明 |
|---|---|---|---|
| `FinalizedEntry` | `round_number`、`question_number`、`group_number`、`rank: int \| None`、`judged_wrong: bool` | 004 `FinalizedRound.result.rankings[].entries[]` | 一個已定案候選；被判錯者 `rank` 為 `None` |
| `FinalizedQuestion` | `round_number`、`question_number`、`success_group: int \| None` | 004 `QuestionRanking` | 某輪某題的搶答成功者（沒有為 `None`） |
| `SubmissionFact` | `round_number`、`question_number`、`group_number`、`answers: tuple[str, ...]`、`received_at: datetime` | 003 `Submission` | `answers[i]` 是第 i+1 格；`received_at` 含時區 |
| `BlankTarget` | `question_number`、`sub_index: int \| None`、`target: CellRef` | 002 `Blank` | 單題 `sub_index` 為 `None` |
| `CurrentCell` | `kind: CellKind`、`text: str \| None`、`display: str` | 005 轉接層（R4） | `kind` 為 `EMPTY`／`TEXT`／`OTHER`（數字、布林、公式）；`text` 只在 `TEXT` 有值 |

### 輸出

| 型別 | 欄位 | 說明 |
|---|---|---|
| `OverwriteImpact`（列舉） | `EMPTY`、`REPLACE`、`SAME` | 見下方「覆寫影響」 |
| `WritePlanItem` | `round_number`、`question_number`、`sub_index`、`group_number`、`answer`、`target: CellRef`、`impact`、`current_display: str \| None` | 預覽一列＝一個子空格；`current_display` 在 `REPLACE` 時為原內容（純文字、已截斷至 40 字元） |
| `ResultSnapshot` | `snapshot_id: str`、`items: tuple[WritePlanItem, ...]`、`unwritten_questions: tuple[int, ...]` | 預覽當下的成果快照；`items` 依（題號, 子編號）排序 |
| `DiffKind`（列舉） | `IDENTITY`、`UNRECOGNIZED`、`HEADER_POSITION`、`QUESTION_NUMBER`、`SUB_BLANK`、`ANSWER_CELL`、`MERGE_RANGE` | 見 research R5 |
| `StructureDifference` | `kind`、`at: CellRef \| None`、`detail: str` | `detail` 是固定的類別說明，不含試算表文字（避免洩漏） |
| `StructureCheck` | `ok: bool`、`differences: tuple[StructureDifference, ...]` | `ok` 為真時 `differences` 為空；依位置排序，確定性 |
| `CellCheck` | `question_number`、`sub_index`、`expected: str`、`current_display: str`、`matches: bool` | 核對時逐格結果 |
| `OutcomeStatus`（列舉） | `SUCCESS`、`FAILED`、`PENDING` | spec FR-015 的三種結果 |
| `Reconciliation` | `status`、`checks: tuple[CellCheck, ...]` | 見「核對判定」 |
| `ExportRow` | `round_number`、`question_number`、`sub_index: int \| None`、`group_number`、`answer`、`received_at`、`rank: int \| None`、`succeeded: bool`、`judged_wrong: bool` | CSV 一列 |

### 純函式（`ExportCore`，全部沒有 I/O、沒有時間參數）

| 函式 | 簽章（概念） | 對應 FR |
|---|---|---|
| `snapshot_id_of` | `(round_numbers) -> str` | FR-005 |
| `build_snapshot` | `(finalized_questions, submissions, blanks, question_numbers, current_cells, round_numbers) -> ResultSnapshot` | FR-002、FR-003、FR-011 |
| `compare_structure` | `(imported: StructureSnapshot, reparsed: ParseResult) -> StructureCheck` | FR-007～FR-009 |
| `reconcile` | `(expected: Sequence[tuple[BlankKey, CellRef, str]], current: Mapping[CellRef, CurrentCell]) -> Reconciliation` | FR-016 |
| `build_rows` | `(entries, submissions, blanks) -> tuple[ExportRow, ...]` | FR-023～FR-026 |
| `render_csv` | `(rows) -> str` | FR-024、FR-027、FR-028 |
| `protect_text` | `(value: str) -> str` | FR-028 |

### 演算法與規則

**成果快照（`build_snapshot`）**

1. 對每個 `FinalizedQuestion` 且 `success_group is not None`，找該（輪次, 題號, 組號）的 `SubmissionFact`；找不到就**明確失敗**（資料不一致，不略過）。
2. 該題的每個 `BlankTarget`（依 `sub_index`，單題為單一個）對應 `answers[i]`；`answers` 長度必須等於該題的格數，否則明確失敗。
3. 覆寫影響：`current_cells[target]`——`EMPTY` → `EMPTY`；`TEXT` 且 `text == answer` → `SAME`；其他 → `REPLACE`。
4. `unwritten_questions` ＝ `question_numbers` 中沒有搶答成功者的題號（尚未成功、全被判錯、無人提交都在內，依題號排序）。
5. 一題最多出現一次（成功後不再開放，004／001）；若同一題出現兩個搶答成功者，視為資料不一致，明確失敗。

**結構比對（`compare_structure`）**——`reparsed.ok` 為假 → 單一差異 `UNRECOGNIZED`；否則依序比對並收集全部差異（不在第一個就停）：

1. `header_number`、`header_answer`、`answer_cols`、`data_start_row` 任一不同 → `HEADER_POSITION`（`at` 為對應表頭位置）。
2. `row_numbers`：兩邊的列集合與各列題號不同 → `QUESTION_NUMBER`（`at` 為該列第 0 欄）。
3. `answer_cells`：鍵（題號, 子編號）只在一邊 → `SUB_BLANK`；同鍵但位置不同 → `ANSWER_CELL`。
4. `merges`：集合不同（以四個座標比對）→ `MERGE_RANGE`（`at` 為合併範圍左上角）。

輸出依（列, 欄, 類別）排序；相同輸入必得相同輸出。

**核對判定（`reconcile`）**——對每個目標格：`current.kind is TEXT and current.text == expected` → `matches`。全部 `matches` → `SUCCESS`；全部不 `matches` → `FAILED`（原因 `NOT_WRITTEN` 由應用層加上）；其他 → `PENDING`。預期為空集合時不會被呼叫（快照至少一個目標格才可寫回，FR-006）。

**CSV 資料列（`build_rows`）**

1. 只處理傳入的 `FinalizedEntry`（只含已定案輪次，由應用層保證）。
2. 每個 entry 找對應 `SubmissionFact`（找不到明確失敗）；依該題的 `BlankTarget`／`answers` 展開成一列一個子空格；`sub_index` 單題為 `None`。
3. `rank` 取 entry 的 `rank`（被判錯為 `None`）；`succeeded ＝ rank == 1 and not judged_wrong`；`judged_wrong` 取 entry 的旗標。
4. 排序鍵：（輪次, 題號, 被判錯者排後〔`rank is None`〕, `rank`, 接收時間, 子編號）。被判錯者之間依接收時間，確定性（FR-026）。

**CSV 文字（`render_csv`、`protect_text`）**

- 表頭固定：`輪次,題號,子空格,組別,答案,送出時間,順位,是否成功,是否被判錯`。
- `protect_text(value)`：`value` 以 `=`、`+`、`-`、`@`、`\t`、`\r` 開頭時前面加 `'`，否則原樣；只套用在「組別」與「答案」欄（FR-028）。
- 時間 `received_at.isoformat(timespec="milliseconds")`；布林「是」「否」；`rank`、`sub_index` 為 `None` 時輸出空字串。
- 以標準 `csv.writer`（`\r\n`）產生字串；BOM 與編碼在轉接層編成位元組時加上。

## 應用層（`app/result_export/`）

| 型別 | 欄位 | 說明 |
|---|---|---|
| `AttemptKind`（列舉） | `WRITE`、`RETRY` | 第一次確認寫回，或重試 |
| `AttemptReason`（列舉） | `NOT_AUTHORIZED`、`AUTH_EXPIRED`、`PERMISSION_DENIED`、`REJECTED`、`RATE_LIMITED`、`STRUCTURE_CHANGED`、`NOT_CONFIGURED`、`NOT_WRITTEN`、`UNKNOWN` | 失敗或待確認的原因類別（只有代碼；訊息在 `messages.py`） |
| `WriteAttempt` | `attempt_id: int`、`kind`、`snapshot_id`、`items: tuple[WritePlanItem, ...]`、`status: AttemptStatus`、`reason: AttemptReason \| None`、`differences: tuple[StructureDifference, ...]`、`cell_checks: tuple[CellCheck, ...]`、`started_at`、`finished_at: datetime \| None` | `items` 是這次嘗試對應的快照內容，重試與核對都用它；`started_at`／`finished_at` 由服務層從 `Clock` 取得 |
| `AttemptStatus`（列舉） | `IN_PROGRESS`、`SUCCESS`、`FAILED`、`PENDING` | `IN_PROGRESS` 只是暫時狀態，不屬於 spec 的三種結果 |
| `ExportRejection`（列舉） | 見 [contracts/http-api.md](contracts/http-api.md) 的錯誤表 | 服務不拋業務錯誤，失敗時 `Result.ok=False` |
| `ExportStore` | `attempts: dict[str, list[WriteAttempt]]`、`locks: dict[str, asyncio.Lock]` | 依活動代碼為 key；只在記憶體（憲章原則 VII） |

**不變量**

- 每個活動同時間最多一個 `IN_PROGRESS` 的嘗試（R1）。
- `WriteAttempt` 一旦脫離 `IN_PROGRESS`，除了由 `recheck` 產生新的狀態外不再變動；`recheck` 與 `retry` 只作用在**最新**一次嘗試。
- 005 對活動唯讀：不呼叫任何會改變 001～004 狀態的方法（以測試保證，見 quickstart 步驟 8）。

### 狀態轉移（單次嘗試）

```text
（confirm／retry）→ IN_PROGRESS
   ├─ 憑證失敗／讀取失敗／結構不符／無法辨識 ─→ FAILED（零寫入）
   ├─ batchUpdate 200 ─→ SUCCESS
   ├─ batchUpdate 4xx（400/401/403/404/429）─→ FAILED（原子：沒有任何格被改）
   └─ batchUpdate 5xx／逾時／連線中斷 ─→ PENDING

PENDING／FAILED／SUCCESS ──recheck──→ SUCCESS（全符）｜FAILED(NOT_WRITTEN)（全不符）｜PENDING（部分符）
PENDING／FAILED／SUCCESS ──retry────→ 新的 IN_PROGRESS（同一份 items，重新結構檢查）
```

### 狀態與格數對照（FR-021）

`WriteAttempt`、快照擴充 `export` 與 `Attempt` JSON 的三個格數（`confirmedCells`＝已確認寫入、`notWrittenCells`＝確認未寫入、`pendingCells`＝待確認）依下表填入，`totalCells` 為 `items` 的子空格數；三者相加恆等於 `totalCells`。

| 情況 | `confirmedCells` | `notWrittenCells` | `pendingCells` |
|---|---|---|---|
| `IN_PROGRESS` | 0 | 0 | `totalCells` |
| `SUCCESS`（寫入成功，或核對全符） | `totalCells` | 0 | 0 |
| `FAILED`（零寫入：授權、讀取、結構、4xx 被拒，或核對全不符） | 0 | `totalCells` | 0 |
| `PENDING`（寫入結果無法證實） | 0 | 0 | `totalCells` |
| `PENDING`（核對部分相符） | 相符格數 | 0 | 不符格數 |

核對（`recheck`）時 Google 讀取失敗不改變該嘗試的狀態與格數，只回錯誤（見 [contracts/http-api.md](contracts/http-api.md) X3）。

## 驗證規則（對應 FR）

| 規則 | FR | 位置 |
|---|---|---|
| 只有活動老師；已取消一律拒絕 | FR-001 | 服務層入口（先 `ActivityService.export_view`） |
| 沒有已定案成功題 → `NO_RESULTS`，不碰 Google 寫入 | FR-006 | 服務層 |
| `snapshot_id` 不等於目前 → `STALE_SNAPSHOT` | FR-005 | 服務層 |
| 同活動一次一個寫入 | FR-020 | 服務層＋`ExportStore` |
| 每次寫入與重試前重新讀取並比對結構 | FR-007、FR-014 | 服務層呼叫核心 `compare_structure` |
| 目標位置只取 002 的 `Blank.target`，不寫死 | FR-011 | 核心 `build_snapshot` 的輸入 |
| 答案以 `stringValue` 逐字寫入，不加保護前綴 | FR-013 | 轉接層 `GoogleSheetsWriter` |
| 不修改非目標格與屬性（`fields="userEnteredValue"`） | FR-012 | 轉接層 |
| CSV 只含已定案輪次、不虛構列、無資料只有表頭 | FR-023 | 服務層過濾＋核心 `build_rows` |
| CSV 欄位順序、列順序固定 | FR-024、FR-026 | 核心 |
| 組別與答案文字保護、系統欄位不保護 | FR-028 | 核心 `protect_text` |
| 外部輸入驗證、錯誤訊息不含內部細節 | FR-031 | HTTP 層＋服務層 |
| 日誌不含答案與機敏資訊 | FR-033 | 服務層 |
