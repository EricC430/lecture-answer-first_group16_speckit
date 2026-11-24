# HTTP API 契約：004-ranking-review

**用途**：老師在結果階段判錯／撤銷判錯，並確認定案。**讀取結果一律透過 001 的快照**（`GET /api/activities/{code}/snapshot` 與 WebSocket 推送），見 [sync-websocket.md](sync-websocket.md)。共通規則（基底 `/api`、JSON、`Authorization: Bearer <token>`、錯誤格式、`Idempotency-Key`）沿用 001 [`http-api.md`](../../001-activity-session/contracts/http-api.md)。

## 端點

| # | 方法與路徑 | 身分 | 請求本文 | 成功回應 | Spec |
|---|---|---|---|---|---|
| R1 | `PUT /activities/{code}/rounds/{round}/questions/{q}/groups/{g}/judgement` | 老師 token | `{"wrong": true \| false}` | `200 {"changed": bool, "resultVersion": int, "affectedQuestions": [int, ...]}` | FR-011～FR-016、FR-025、FR-034 |
| R2 | `POST /activities/{code}/rounds/current/finalize` | 老師 token | `{"resultVersion": int}` | `200 {"version": int, "resultVersion": int, "alreadyFinalized": bool}` | FR-019～FR-023 |

- `{round}`、`{q}`、`{g}` 是輪次編號、題號、組號，必須是正整數；否則 `400 INVALID_REQUEST`。
- R1 **不限於**目前的搶答成功者：只要是該輪已接受的提交，對任何一筆（含非搶答成功者）判錯或撤銷都接受（OpenSpec 原文，FR-011）；老師介面每題只提供「判錯」給目前的搶答成功者、「撤銷判錯」給最近一位被替換者，那只是介面限制（FR-034）。
- R1 是「設定狀態」：`wrong=true` 判錯、`wrong=false` 撤銷判錯。對已是該狀態的提交重送，回 `200` 且 `changed=false`、`resultVersion` 不變、`affectedQuestions` 為空（FR-025）。
- R1 的 `affectedQuestions` 是這次變更影響的題號（與快照的 `ranking.rounds[].affectedQuestions` 相同）；`changed=false` 時為空。
- R2 取代 001 預留的空定案實作（同一路徑；研究 R7）。`version` 是 001 定案後的活動狀態版本；`resultVersion` 是被確認的結果版本；`alreadyFinalized=true` 表示這是對已定案同一版本的重複確認（冪等，不再呼叫 001、歷史成功次數不重複增加，FR-022）。
- R2 可帶 `Idempotency-Key`（沿用 001 的做法），但不需要：冪等已由 `resultVersion` 與定案紀錄保證。
- 判錯**不需要**原因欄位（FR-034）；本文多送的欄位一律忽略（`extra="ignore"`）。
- 兩個端點都只有該活動的老師可以呼叫；老師身分由 001 的 `resolve_requester` 判定，不採信本文或前端的任何宣稱（FR-026）。

## 規則

- **階段**：R1 只在活動處於「結果未定案」且目標輪是目前輪時接受；R2 同。判定順序見 [data-model.md](../data-model.md)「判定規則」。
- **版本**：R2 的 `resultVersion` 必須等於該輪目前的結果版本，否則 `409 STALE_RESULT_VERSION`，不更動任何狀態（FR-021）。
- **原子性**：被拒時不產生部分結果、不增加版本、不推送（FR-027）；R2 若被 001 拒絕，004 不留下定案紀錄（先由 001 接受，004 才標示定案）。
- **推送**：實際變更後 2 秒內，老師與學生的快照都會含新的 `ranking`（FR-030）；沒有變化時不推送。

## 錯誤

`{"error": {"code": "<code>", "message": "..."}}`：

| code | 狀態 | 何時 |
|---|---|---|
| `INVALID_REQUEST` | 400 | 本文不是 JSON 物件、缺 `wrong`／`resultVersion`、`wrong` 不是布林、`resultVersion` 不是整數、路徑上的輪次／題號／組號不是正整數 |
| `NOT_TEACHER` | 403 | 不是該活動的老師（學生、其他活動的老師、匿名） |
| `ACTIVITY_NOT_FOUND` | 404 | 活動代碼不存在且沒帶 token；帶 token 時改回 `410 ACTIVITY_GONE`（沿用 001 `unwrap` 的規則） |
| `ROUND_NOT_FOUND` | 404 | 輪次編號不存在 |
| `SUBMISSION_NOT_FOUND` | 404 | 該輪該題該組沒有已接受的提交（含從未提交、被 003 拒絕的提交） |
| `ROUND_STILL_OPEN` | 409 | 目前輪仍在搶答中：「本輪尚未關閉，無法判錯」 |
| `NO_ROUND` | 409 | 活動還沒有任何輪次 |
| `STALE_ROUND` | 409 | 指定的輪次不是目前輪且尚未定案（防禦用，正常情況不會發生） |
| `RESULT_ALREADY_FINAL` | 409 | 該輪已定案：「本輪已定案，不能再修改」（含定案後、後續輪次開始後的判錯／撤銷，以及不同版本的確認，訊息附定案版本） |
| `ACTIVITY_CANCELLED` | 409 | 活動已取消 |
| `STALE_RESULT_VERSION` | 409 | 確認的結果版本不是最新：「結果已更新，請重新檢視後再確認」 |
| `FINALIZE_REJECTED` | 依 001 | 001 拒絕定案（階段剛好變動、活動已失效等），訊息沿用 001 |

訊息一律讓老師知道原因與如何處理，且**不含**堆疊追蹤、檔案路徑、token、憑證或他組資料（FR-027）。

## 日誌

沿用 001 的請求日誌（路徑樣板、活動代碼、結果碼、版本）；服務層另記 `activity round question group wrong changed version`，不記答案與 token（FR-032）。
