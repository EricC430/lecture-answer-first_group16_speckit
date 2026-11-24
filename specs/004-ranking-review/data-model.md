# Data Model: 順位計算、判錯重算與定案

**Date**: 2026-11-24 ｜ 對應類別圖 [`diagrams/004-ranking-review-class.puml`](../../diagrams/004-ranking-review-class.puml)

所有核心型別都是 `@dataclass(frozen=True)`，集合用 `tuple`／`frozenset`／`MappingProxyType`；核心不讀時鐘，也不匯入 003 的型別。

## 核心（`core/ranking_review/`）

### 輸入

| 型別 | 欄位 | 說明 |
|---|---|---|
| `Candidate` | `group_number: int`、`question_number: int`、`received_at: datetime`、`sequence: int` | 一筆已被 003 接受的提交的排名所需欄位；由服務層從 003 的 `Submission` 轉出。答案不進核心的排名計算 |
| `RankingInput` | `question_numbers: tuple[int, ...]`、`fair_mode: bool`、`baseline: Mapping[int, int]`、`candidates: tuple[Candidate, ...]`、`wrong_marks: frozenset[tuple[int, int]]` | 整輪重算的完整輸入；`wrong_marks` 的元素是（組號, 題號）。`baseline` 沒有的組視為 0 |

**輸入不變式**（由 `RankingCalculator.recompute` 以斷言保護，違反是程式錯誤）：同一（題號, 組號）最多一個候選；`sequence` 在所有候選中不重複；每個候選的題號都在 `question_numbers`；`wrong_marks` 的每一項都對應一個候選。

### 輸出

| 型別 | 欄位 | 說明 |
|---|---|---|
| `WinReason` | `SOLE_CANDIDATE`、`EARLIER_SUBMISSION`、`FEWER_SUCCESSES`、`BACKEND_ORDER` | 勝出（或排在前一名之後）的理由，演算法見下 |
| `DisplayStatus` | `SUCCESS`（搶答成功，結果未定案）、`CORRECT`（搶答正確，定案後）、`WRONG`（答錯）、`FAILED`（搶答失敗） | 每筆提交的顯示狀態；`recompute` 只產生 `SUCCESS`／`WRONG`／`FAILED`，`CORRECT` 只在定案後出現（見下）；整題的「未成功」由 `QuestionRanking.success_group is None` 表示，不是 `DisplayStatus` |
| `RankEntry` | `group_number: int`、`rank: int \| None`、`count_at_processing: int \| None`、`reason: WinReason \| None`、`wrong: bool`、`display_status: DisplayStatus` | 一個候選在某題的排名；被判錯者 `rank`、`reason` 為 `None`；速度模式 `count_at_processing` 為 `None` |
| `QuestionRanking` | `question_number: int`、`entries: tuple[RankEntry, ...]`、`success_group: int \| None` | `entries` 先放有名次者（名次由小到大），再放被判錯者（依 `received_at`、`sequence`）；沒有任何有名次者時 `success_group` 為 `None`（「未成功」） |
| `RoundResult` | `order: tuple[int, ...]`、`rankings: tuple[QuestionRanking, ...]`、`group_counts: Mapping[int, int]`、`wins: Mapping[int, int]` | `order` 是固定題序；`rankings` 依題序排列；`group_counts` 是各組在本輪處理完後的暫算次數（基準＋本輪成功題數）；`wins` 是各組本輪成功題數（定案時的 `success_increments`） |

`DisplayStatus` 的推導（`display_status(rank, wrong)`）：被判錯 → `WRONG`；有名次且名次為 1 → `SUCCESS`；有名次且名次大於 1 → `FAILED`。**定案後**（`final=true`）：`ResultView` 與 `FinalizedResult.rankings` 把名次 1 的 `SUCCESS` 改為 `CORRECT`（`as_final(rankings)`，純函式）；`WRONG`、`FAILED` 不變（FR-033、spec US6-AS1、US7-AS14）。

**`RoundReview` 不變式**：`replaced[question]` 歷程中的每一組都必須在該題的 `wrong_marks` 內（以（組號, 題號）對應），且歷程中沒有重複的組；`RoundReviewRules.mark` 維持這項不變式（歷程只在「判錯且該組是判錯前的搶答成功者」時附加、撤銷時移除）。

`ResultView` 的 `replacedGroup`：`final=true` 時兩種角色都輸出 `null`；未定案時，老師版輸出 `RoundReview.replaced[question]` 歷程的**最後一位**（歷程為空則 `null`），學生版只有在該題 `success_group` 不是 `None`（有遞補者）時才輸出，否則 `null`（spec FR-036、US7-AS3、AS9）。

`ResultView` 老師版每題另有 `actions`（純函式輸出，前端只照它顯示按鈕，不自行判斷；學生版沒有）：`judgeGroup` ＝ 未定案時的 `success_group`（沒有則 `null`），`undoGroup` ＝ 未定案時 `replaced[question]` 歷程的最後一位（歷程為空則 `null`）；`final=true` 時兩者皆為 `null`（spec FR-034、US4-AS9、AS10）。

### 判定與狀態

| 型別 | 欄位 | 說明 |
|---|---|---|
| `RoundReview` | `round_number: int`、`version: int`、`wrong_marks: frozenset[tuple[int, int]]`、`result: RoundResult`、`affected: frozenset[int]`、`replaced: Mapping[int, tuple[int, ...]]`、`finalized: FinalizedResult \| None` | 一輪的審閱狀態；`replaced` 是「被替換的搶答成功者」：題號 → 依判錯順序保存的歷程：因判錯而被下一組取代的前一位搶答成功者的組號（最後一位是最近一位；撤銷判錯時移出歷程，所以可「退回上一步」；定案時清空，初始為空）；`version` 從 1 開始，只在實際變更時加 1；`affected` 是最近一次變更影響的題號（初始為空） |
| `FinalizedResult` | `version: int`、`rankings: tuple[QuestionRanking, ...]`、`final_counts: Mapping[int, int]`、`solved_questions: frozenset[int]`、`success_increments: Mapping[int, int]` | 定案時保存，之後只讀；`final_counts` 是各組定案後的累計成功次數（基準＋本輪成功題數） |
| `ReviewRejection` | 見 research R12 | `StrEnum`，每個值有 HTTP 狀態碼與預設訊息 |
| `MarkDecision` | `ok: bool`、`changed: bool`、`review: RoundReview \| None`、`rejection: ReviewRejection \| None` | 判錯／撤銷的判定結果；`changed=False` 時 `review` 是原物件 |

## 演算法（`RankingCalculator`）

### 固定題序（FR-004、FR-005）

`QuestionOrder.compute(question_numbers, candidates)`：

1. 每題取「該題全部候選（不論是否被判錯）中 `(received_at, sequence)` 最小者」作為決定題序的依據。
2. 有依據的題依該鍵遞增排列；沒有任何候選的題接在後面，依題號遞增。

題序只在建立 `RoundReview` 時（`recompute` 的第一次呼叫）決定一次並保存在 `RoundResult.order`；之後的重算 **傳入已保存的題序**，不重新計算（所以判錯不會移動題序）。

### 速度模式（`rank_speed`，FR-006、FR-009）

對每題：候選去掉被判錯者，依 `(received_at, sequence)` 遞增排名 1、2、3…；第一名為 `success_group`；被判錯者附在後面。與成功次數無關。

### 公平模式（`rank_fair`，FR-007、FR-008）

```text
counts = baseline 的複本（沒有的組以 0 計）
for question in order:
    candidates = 該題未被判錯的候選
    依 (counts[group], received_at, sequence) 遞增排名
    每個候選的 count_at_processing = 處理當下的 counts[group]
    第一名成為 success_group；counts[success_group] += 1
    其他候選的 counts 不變
```

題組是一筆提交，成功只加 1。整輪重算一律從 `baseline` 開始，不使用上一版的暫算次數（FR-015）。

### 理由（`WinReason`，研究 R9）

對每個有名次的候選，與前一名比較（第一名與第二名比較）：只有一個候選 → `SOLE_CANDIDATE`；公平模式且次數不同 → `FEWER_SUCCESSES`；時間不同 → `EARLIER_SUBMISSION`；時間（與次數）都相同 → `BACKEND_ORDER`。

### 受影響題目（`diff`，研究 R10）

逐題比較舊新 `QuestionRanking`（成功者與所有 `RankEntry`），不同者為受影響題。初始結果沒有舊版，回傳空集合。

### 確定性（FR-017、SC-002）

`recompute` 對相同的 `RankingInput` 與 `order` 產生逐項相等的 `RoundResult`。沒有隨機、時間、字典順序依賴（所有迭代都在排序後的序列上進行）。

## 判定規則（`RoundReviewRules`）

核心只做「給定已查好的資料，回傳決定」，不讀 001、003：

```text
mark(review, input, group, question, wrong) -> MarkDecision
  (group, question) 沒有候選            -> SUBMISSION_NOT_FOUND
  已是 wrong 狀態                       -> ok, changed=False（版本不變）
  否則 wrong_marks 加／減一項 -> recompute -> version+1 -> affected = diff(old, new)
  判錯且該組在判錯前是該題 success_group -> 把該組附加到 replaced[question] 末端；
  判錯非搶答成功者 -> replaced 不變；
  撤銷某組 -> 若該組在 replaced[question] 歷程中就移除它（最後一位被撤銷即「退回上一步」，
              前一位成為最近一位）；不在歷程中則 replaced 不變

finalize_plan(review, baseline) -> (solved_questions, success_increments, final_counts)
  solved_questions = 有 success_group 的題號
  success_increments = result.wins
  final_counts = baseline + wins
  rankings = as_final(result.rankings)   # SUCCESS -> CORRECT，replaced 歷程清空
```

階段與身分的檢查在服務層（需要 001 的活動資料），順序如下（第一個不成立的就是拒絕原因）：

| 順序 | 檢查 | 拒絕 |
|---|---|---|
| 1 | 活動存在 | `ACTIVITY_NOT_FOUND` |
| 2 | 請求者是該活動老師 | `NOT_TEACHER` |
| 3 | 活動沒有被取消 | `ACTIVITY_CANCELLED` |
| 4 | 活動已有輪次 | `NO_ROUND` |
| 5 | 輪次編號存在 | `ROUND_NOT_FOUND` |
| 6 | 該輪已定案（輪次小於目前輪，或階段是結果已定案、已結束） | `RESULT_ALREADY_FINAL`（確認定案且版本相同時改為冪等成功） |
| 7 | 輪次是目前輪且已關閉（階段結果未定案）；搶答中 → `ROUND_STILL_OPEN` | 見 research R12 |
| 8 | （確認定案）`resultVersion` 等於目前結果版本 | `STALE_RESULT_VERSION` |
| 9 | （判錯）該（組, 題）有候選 | `SUBMISSION_NOT_FOUND` |

## 應用層（`app/ranking_review/`）

| 型別 | 說明 |
|---|---|
| `ReviewStore` | 記憶體：`reviews: dict[(code, round_number), RoundReview]`、`locks: dict[code, asyncio.Lock]`、`cache: dict[(code, round, version, final, kind), JsonDict]`（`final` 必須在鍵裡：定案不增加結果版本卻會改變輸出）；活動被移除時一起清空（後端重啟即清空） |
| `RankingService` | `mark_wrong`／`unmark_wrong`（呼叫 `_set_wrong`）、`finalize`、`snapshot_extension`、`finalized_rounds`（`RankingReader`）；建構時向 001 註冊快照擴充 |
| `RankingReader`（Protocol） | 給 005：`finalized_rounds(code) -> tuple[FinalizedRound, ...]` |
| `FinalizedRound` | `round_number: int`、`result: FinalizedResult`；已定案輪次的唯讀視圖 |

## 狀態轉移

```text
（輪次關閉）
    │  尚無判錯：由純計算導出初始結果（版本 1），不寫入存放區（研究 R2）
    ▼
導出的初始結果 v1（未定案）
    │  第一次實際判錯：以它為起點建立 RoundReview 並保存（版本 2）
RoundReview（未定案）
    │  mark／unmark 實際變更：version+1、affected 與 replaced 更新
    │  mark／unmark 無變化：不變
    │  finalize(resultVersion == version) 且 001 接受
    ▼
RoundReview（finalized = FinalizedResult）──之後只讀；任何修改 → RESULT_ALREADY_FINAL
```

001 的階段與 004 的審閱狀態對應：`ROUND_OPEN` 沒有 `RoundReview`；`RESULT_PENDING` 的目前輪是「未定案」；`RESULT_FINAL`／`ENDED` 與所有較早的輪次都是「已定案」（`ranking.final = true`）。

## 與 003、001 資料的對應

| 004 欄位 | 來源 |
|---|---|
| `Candidate.*` | 003 `Submission.group_number`、`question_number`、`received_at`、`sequence`（`SubmissionReader.round_submissions`） |
| `RankingInput.question_numbers`、`fair_mode` | 001 `Round.rules.question_numbers`、`Round.rules.fair_mode` |
| `RankingInput.baseline` | 001 `Round.baseline`（key 為組號；開輪時保存） |
| `FinalizeOutcome.solved_questions` | `finalize_plan.solved_questions` |
| `FinalizeOutcome.success_increments` | `finalize_plan.success_increments`（key 為組號；只含有成功題的組，其餘視為 0） |
| 答案、接收時間、送出先後（畫面） | 003 的 `submissions.published`，前端以（輪次、題號、組號）合併 |
