---

description: "007-browser-identity-sync 的任務清單"
---

# Tasks: 同一瀏覽器共用學生身分與跨分頁同步

**Input**: Design documents from `/specs/007-browser-identity-sync/`

**Prerequisites**: plan.md、spec.md、research.md（R1～R11）、data-model.md、contracts/http-and-sync-changes.md、quickstart.md

**Tests**: REQUIRED（憲章 v1.1.0 原則 VI）。
- 每個 Acceptance Scenario 至少要有一個自動化測試，測試函式的 docstring 寫 `Scenario: 007 USn-ASm`。
- 007 不涉及 Google。
- **學生路徑的測試一律不帶 Bearer**（research R8）：每個「瀏覽器」用獨立的 `TestClient`（各自的 cookie jar），或用獨立的 CDP browser context，以證明學生實際使用的 cookie 路徑可用。

**Diagrams**: REQUIRED（原則 II）。`diagrams/007-browser-identity-sync-{component,class,sequence}.puml` 與 PNG 已存在（2026-11-26 plan 階段更新）。最後一個 Phase 有「程式碼與圖表一致性驗證」任務。

**Architecture**: REQUIRED（技術限制 4）。
- 核心只改 `core/activity/commands.py` 的 `JoinGroup`（新增 `device_token_hash`）、`state_machine.py` 的 `_join_group` 與 `results.py` 的訊息，不知道 cookie 的存在。
- cookie 只出現在 `adapters/web/`。

**路徑**：以下皆相對於 repo 根目錄；Python 套件根目錄為 `src/lecture_quiz/`。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行（不同檔案、沒有相依）
- **[Story]**: US1～US3 對應 spec 的 User Story

---

## Phase 1: Setup

**Purpose**: 確認工作環境，並記下改動前的測試基準，供之後比對。

- [x] T001 建立 GitHub Issue「007 同一瀏覽器共用學生身分與跨分頁同步」，把本機分支 `feature/007-browser-identity-sync` 改名為 `feature/<issue>-007-browser-identity-sync`，並更新 `specs/007-browser-identity-sync/spec.md` 與 `plan.md` 開頭的 Feature Branch。
- [x] T002 記錄改動前的基準：在 repo 根目錄執行 `.venv\Scripts\pytest`（預設排除 perf、real_google），把日期、指令與通過／失敗／略過數寫進 `specs/007-browser-identity-sync/quickstart.md` 的「驗證紀錄」表（新增一列「改動前基準」）。
- [x] T003 [P] 確認 `pyproject.toml` 已有 Ruff 與 mypy 設定（憲章技術限制 2；001 已設定，沿用）。執行 `ruff check .`、`ruff format --check .`、`mypy` 確認改動前就是全部通過；沒有通過的項目要先記下來，以免之後誤算成 007 的回歸。

---

## Phase 2: Foundational（阻擋所有 User Story）

**Purpose**: 瀏覽器金鑰的產生、`browser-session` 端點、`request_token` 身分來源、加入端點的新契約，以及讓既有測試能繼續跑的輔助函式。完成前不能開始任何 User Story。

### 測試（先寫、先看到失敗）

- [x] T004 [P] 單元測試 `tests/unit/app/test_browser_key.py`，驗證 `new_browser_key()` 與 `is_browser_key(value)`：
  - 新金鑰長度 43、字元集符合 `[A-Za-z0-9_-]`，連續 1000 次不重複。
  - 空字串、`None`、42 或 44 字元、含 `.`、`=`、空白或中文時，`is_browser_key` 回 False。
- [x] T005 [P] 契約測試 `tests/contract/test_http_browser_session.py`，對應 contracts §1：
  - (a) 沒帶 cookie 時回 204、本文為空，`Set-Cookie` 含 `lq_browser=`、`HttpOnly`、`SameSite=Strict`、`Path=/`、`Max-Age=86400`，且不含 `Secure`、`Domain`。
  - (b) 帶格式正確的 cookie 再呼叫，回 204 且沒有 `Set-Cookie`。
  - (c) 帶格式錯誤的 cookie，回 204 並發新金鑰。
  - (d) 同一個 client 連續呼叫 3 次，cookie 值不變。
- [x] T006 [P] 契約測試 `tests/contract/test_http_request_token.py`，驗證 `request_token` 的優先順序（research R4）：
  - 同時帶 Bearer（老師 token）與 cookie（某組學生）時，以老師身分處理：老師專用操作成功。
  - 只有 cookie 時是學生身分。
  - cookie 格式錯誤時視為匿名。
- [x] T007 修改 `tests/contract/test_http_join.py`，對應 contracts §3：
  - 成功回應的 key 只有 `groupNumber`、`credential`、`version`，不含 `deviceToken`。
  - 沒有 cookie 也沒有 Bearer 時回 `400 BROWSER_SESSION_REQUIRED`，訊息為「瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。」，而且老師快照的組別數不變（FR-013）。
  - 帶 cookie、代碼不存在時回 `404 ACTIVITY_NOT_FOUND`，不是 410。
  - 加入回應沒有 `Set-Cookie`。

### 實作

- [x] T008 [P] 在 `src/lecture_quiz/app/activity/secrets_gen.py` 新增 `new_browser_key() -> str`（`secrets.token_urlsafe(32)`）與 `is_browser_key(value: object) -> bool`（長度 43、字元集 `[A-Za-z0-9_-]`），附型別提示與 Google 風格 docstring（data-model「瀏覽器金鑰」）。
- [x] T009 新增 `src/lecture_quiz/adapters/web/browser_session.py`：
  - 常數 `COOKIE_NAME = "lq_browser"`、`COOKIE_MAX_AGE = 86400`。
  - `browser_key_from(cookies: Mapping[str, str]) -> str | None`：格式不符時回 None。
  - `create_router() -> APIRouter`，提供 `POST /browser-session`：已有合法金鑰時回 204、不設 cookie；否則以 `response.set_cookie(COOKIE_NAME, new_browser_key(), max_age=86400, httponly=True, samesite="strict", path="/")` 設定，不設 `secure` 與 `domain`，本文為空。
  - 只用 `annotate_request_log` 記錄結果，不記錄 cookie（research R10）。
- [x] T010 在 `src/lecture_quiz/main.py` 把 `browser_session.create_router()` 掛在 `/api` 之下，位置與 001 的 router 相同，必須在 `app.mount("/", NoCacheStaticFiles(...))` 之前。
- [x] T011 在 `src/lecture_quiz/adapters/web/common.py` 新增 dependency `request_token(authorization: Header, request: Request) -> str | None`：
  - 先用 `bearer_token` 的結果；沒有時才用 `browser_key_from(request.cookies)`。
  - `bearer_token` 保留不動，給只接受 Bearer 的用途。
  - 在 `src/lecture_quiz/adapters/web/http_api.py` 把 `Token = Annotated[str | None, Depends(bearer_token)]` 改成 `Depends(request_token)`。002～005 import 同一個 `Token`，會一起改變，確認它們不需要再改。
- [x] T012 修改 `src/lecture_quiz/app/activity/service.py` 的 `join()`：
  - 新增必填參數 `browser_key: str`。
  - 刪除 `token = new_token()`，改成 `IssuedSecrets(device_token_hash=hash_token(browser_key), group_credential=new_credential())`，並以 `JoinGroup(requester, number_raw, credential_raw, device_token_hash=hash_token(browser_key))` 建立指令（欄位由 T022 新增；T022 完成前先以預設值 None 呼叫也可）。
  - `build` 改用 `hash_token(browser_key)` 找裝置。
  - `JoinedDevice` 移除 `device_token` 欄位，並更新 docstring。
- [x] T013 修改 `src/lecture_quiz/adapters/web/http_api.py` 的 `join_group` 路由（contracts §3）：
  - 金鑰取 `bearer_token(...)`，沒有時取 cookie；兩者都沒有時拋 `ApiError(400, "BROWSER_SESSION_REQUIRED", "瀏覽器沒有保存身分，請允許本網站儲存資料後重新整理頁面。")`，不呼叫服務層。
  - 把金鑰傳給 `service().join(..., browser_key=...)`。
  - 回應本文移除 `deviceToken`。
  - 呼叫 `unwrap` 時第三個參數只傳 Bearer，不傳 cookie，所以活動不存在時回 404。
- [x] T014 新增測試輔助函式 `new_browser(client: TestClient) -> str`，放在 `tests/conftest.py`（research R8）：
  1. `client.cookies.clear()`。
  2. `POST /api/browser-session`。
  3. 從 `response.cookies["lq_browser"]` 取值並回傳。

  `join_group()` 改成先呼叫 `new_browser(client)`，再以 `headers={"Authorization": f"Bearer {key}"}` 加入，回傳該金鑰。docstring 註明「Bearer 路徑，學生實際的 cookie 路徑另由 007 測試涵蓋」。
- [x] T015 依 T014 的模式，改寫其餘直接讀 `deviceToken` 的測試，以 `grep -rn --include=*.py "deviceToken" tests` 列出全部位置後逐一處理（改動前共 12 個檔案、31 處）。涵蓋：
  - `tests/integration/conftest.py`、`tests/integration/ranking_world.py`、`tests/unit/app/ranking_review/conftest.py`
  - `tests/browser/conftest.py`（`World.join`）
  - `tests/perf/test_sync_latency.py`、`test_submission_latency.py`、`test_ranking_latency.py`、`test_export_latency.py`
  - 各個 `tests/integration/test_*.py`、`tests/contract/test_http_join.py`

  改完後 `grep -rn --include=*.py "deviceToken" tests` 只能剩下 T007「回應不含 deviceToken」的斷言。
- [x] T016 執行 `.venv\Scripts\pytest`，與 T002 的基準比對，並把結果記入 quickstart 驗證紀錄（2026-11-26 03:04：1387 passed、4 failed；4 個失敗皆屬 US1 尚未實作的 T023 訊息與 T026 前端，於 T030 再驗證；過程中發現並修正 P-01，見 verification.md）：
  - 通過數不少於基準（另加新增測試的數量）。
  - 失敗數為 0，或與基準相同且逐一說明原因。
  - 有新的失敗時，先修正再往下做，不得放寬斷言（AI 開發守則「測試不能是假綠燈」）。

**Checkpoint**：金鑰、端點與身分來源都已就緒，既有測試沒有回歸。

---

## Phase 3: User Story 1 - 同一瀏覽器只能代表一個組別 (Priority: P1) 🎯 MVP

**Goal**：同一瀏覽器在同一活動只有一個學生身分，從任何分頁加入他組都被拒絕；新分頁、重新整理、重開瀏覽器都恢復同一組。

**Independent Test**：同一個 `TestClient`（一個 cookie jar 等於一個瀏覽器）加入第 3 組後，再加入第 5 組被拒絕、第 5 組沒有被建立；另一個 `TestClient` 可以加入第 5 組。瀏覽器端對端測試中，同一個 context 的第二個分頁開 `?code=` 直接顯示第 3 組。

### 測試（先寫、先看到失敗）

- [x] T017 [P] [US1] 核心單元測試，加在 `tests/unit/core/test_state_machine_join.py`（data-model INV-1）：
  - `command.device_token_hash`（與 `issued.device_token_hash` 相同）已在 `activity.devices`，而請求者為 `Anonymous`（模擬「鎖外解析」的競爭）時，`_join_group` 回 `ALREADY_IN_GROUP`，`groups`、`devices`、`version` 都不變，`issued.group_credential` 沒有被寫入任何組。
  - 拒絕訊息為「這個瀏覽器已是第 3 組成員，請先離開本組。」（組號取自 `command.device_token_hash`）。
  - `command.device_token_hash` 與 `issued.device_token_hash` 不一致時拋 `ValueError`。
  - 驗證 US1-AS3、FR-007。
- [x] T018 [P] [US1] 整合測試 `tests/integration/test_007_browser_identity.py`（新檔），每個「瀏覽器」一個獨立的 `TestClient`，學生請求一律不帶 Bearer。測試函式如下：
  - `test_same_browser_restores_group_in_new_tab`：同一個 client 加入第 3 組後，以 cookie 取快照，`ownGroup.number == 3`（Scenario: 007 US1-AS1）。
  - `test_other_browser_joins_same_group_with_credential`：另一個 client 附上憑證加入第 3 組，兩者的 `ownGroup` 相同，老師看板第 3 組有 2 個成員（007 US1-AS2）。
  - `test_member_browser_join_other_group_rejected`：已是第 3 組的 client 加入第 5 組，回 `409 ALREADY_IN_GROUP` 並附上述訊息，老師快照沒有第 5 組（007 US1-AS3）。
  - `test_forged_or_foreign_key_is_anonymous`：竄改的 cookie、另一個活動的成員 cookie、格式錯誤的 cookie，對快照、003 提交、離開本組各試一次，全部被拒，回應本文不含任何憑證或金鑰字串（007 US1-AS4、SC-004）。
  - `test_key_persists_without_tab_state`：清掉 client 的所有狀態，只保留 `lq_browser` 這個 cookie，再取快照，仍是第 3 組（007 US1-AS5）。
  - `test_submission_ignores_claimed_group`：提交本文自稱第 5 組，仍歸第 3 組（007 US1-AS6）。
- [x] T019 [P] [US1] 整合測試，加在 `tests/integration/test_007_browser_identity.py`：
  - `test_ten_join_attempts_one_group`：同一個 client 依序加入組號 1～10（組數上限 10），只有第 1 次成功，其餘 9 次都是 `ALREADY_IN_GROUP`，老師快照的組別數為 1，回應中沒有任何新憑證（SC-001）。
  - `test_concurrent_joins_one_wins`：同一把金鑰以 `asyncio.gather` 直接呼叫 `ActivityService.join` 兩次（組號 3 與 5），重複 20 次，每次恰好 1 次成功、組別數為 1，落敗者的訊息含成功者的組號（SC-002、FR-007）。服務層呼叫需要用 `tests/conftest.py` 的 `call` 輔助函式在事件迴圈內執行。docstring 註明「直接呼叫服務層：HTTP 的身分解析在鎖外，競爭點就在服務層」。
- [x] T020 [P] [US1] 契約測試，修改 `tests/contract/test_ws_sync.py`（contracts §4）：
  - 送 `{"type":"auth"}` 或 `{"type":"auth","token":null}`，而握手帶第 3 組的 cookie，收到該組快照。
  - 不帶 cookie 時收到 `unauthorized INVALID_TOKEN`。
  - `token` 為數字時以 `CLOSE_BAD_FIRST_MESSAGE` 關閉。
  - 老師以 `{"type":"auth","token":"<老師 token>"}` 驗證，行為不變。
- [x] T021 [P] [US1] 瀏覽器端對端測試 `tests/browser/test_007_tabs.py`（新檔），在 `tests/browser/cdp.py` 或 conftest 新增「建立獨立 browser context」的輔助函式（CDP `Target.createBrowserContext`，並以 `browserContextId` 開分頁）。學生身分一律由頁面實際加入取得，不注入：
  - `test_second_tab_shows_same_group`：context 甲的分頁 A 從加入畫面加入第 3 組，再開分頁 B 到 `/student.html?code=K`，B 顯示第 3 組且加入表單隱藏（007 US1-AS1）。
  - `test_second_tab_join_other_group_shows_message`：分頁 B 開 `/student.html`（不帶代碼），輸入 K 與 5 送出，畫面顯示「這個瀏覽器已是第 3 組成員，請先離開本組。」，接著切換到第 3 組畫面（007 US1-AS3）。
  - `test_reopen_by_entering_code_restores_group`：關閉 context 甲的所有分頁（context 保留，代表瀏覽器的 cookie 還在），再開 `/student.html`，在加入畫面輸入 K 與任意組號送出，畫面切換到第 3 組；另開 `/student.html?code=K` 也直接顯示第 3 組（007 US1-AS5）。
  - `test_wrong_code_in_url_shows_not_found`：新的 context 開 `/student.html?code=ZZZZZZ`（不存在的代碼），顯示加入畫面與「找不到這個活動代碼，請確認後再輸入。」，不顯示「活動已失效」（spec Edge Case）。
  - `test_document_cookie_hides_key`：在分頁 A 執行 `document.cookie`，結果不含 `lq_browser`（FR-008）。

### 實作

- [x] T022 [US1] 核心：
  - 在 `src/lecture_quiz/core/activity/commands.py` 的 `JoinGroup` 新增欄位 `device_token_hash: str | None = None`（放在最後，保持既有呼叫相容），docstring 說明它是「服務層計算的瀏覽器金鑰雜湊」。
  - 在 `src/lecture_quiz/core/activity/state_machine.py` 的 `_join_group` 中：`command.device_token_hash` 不為 None 且與 `issued.device_token_hash` 不同時拋 `ValueError`。於既有 `isinstance(actor, Device)` 檢查之後、組號正規化之前加入 INV-1：`issued.device_token_hash in activity.devices` 時回 `_reject(activity, RejectionReason.ALREADY_IN_GROUP)`。docstring 註明「補足請求者在鎖外解析造成的競爭（007 research R3）」。
- [x] T023 [US1] 核心：在 `src/lecture_quiz/core/activity/results.py` 修改兩處：
  - `ALREADY_IN_GROUP` 的預設訊息改為「這個瀏覽器已經在某一組，請先離開本組。」
  - `_describe_group_rejection` 中 `JoinGroup` 的專屬訊息改為「這個瀏覽器已是第 {n} 組成員，請先離開本組。」，組號查找順序為 `command.device_token_hash`，沒有時才用 `command.actor.token_hash`（research R3）。
  - 用 `grep -rn "這台裝置" src tests` 找出並更新其他相依的測試斷言。
- [x] T024 [US1] 轉接層：修改 `src/lecture_quiz/adapters/web/ws_sync.py` 的 `_receive_auth`，改為回傳 `str | None | _Invalid`（或等效的區分方式）：
  - `token` 為字串時照舊。
  - `token` 缺少或為 `null` 時，改用 `browser_key_from(websocket.cookies)`。
  - `token` 為其他型別時，以 `CLOSE_BAD_FIRST_MESSAGE` 關閉。

  `serve()` 的後續流程（`gone`、`INVALID_TOKEN`）不變。更新模組開頭的說明（contracts §4）。
- [x] T025 [US1] 前端：修改 `src/lecture_quiz/adapters/static/js/identity.js`：
  - 刪除 `deviceKey`、`getDeviceToken`、`setDeviceToken`、`clearDeviceToken`。
  - `clearIdentity(code)` 只清除老師 token。
  - 更新開頭註解：學生身分改由 HttpOnly cookie 保存，頁面讀不到（research R7）。
- [x] T026 [US1] 前端：修改 `src/lecture_quiz/adapters/static/js/student.js`（research R7）：
  - (1) `init()` 先呼叫 `apiRequest("POST", "/api/browser-session")`，完成前停用加入按鈕；失敗時以 `showError` 顯示「無法建立瀏覽器身分，請重新整理頁面」。
  - (2) 網址有 `?code=` 時直接 `startSync(code)`，不帶 token。
  - (3) `connectSync` 以 `token = null` 呼叫。第一次連線就收到 `INVALID_TOKEN` 時，安靜地顯示加入表單、不顯示錯誤；之後收到的 `LEFT_GROUP`、`GROUP_DELETED`，維持原本的提示。
  - (4) `joinGroup` 成功後不再保存 token，改呼叫 `startSync(code)`。收到 `409 ALREADY_IN_GROUP` 時，顯示訊息並 `startSync(code)`、把網址改成 `?code=`，切換到本組畫面（spec US1-AS3、US1-AS5；contracts §7）。
  - (4b) 記錄這個分頁是否曾經同步成功（收到第一份快照）。第一次連線就收到 `gone` 時，改顯示加入畫面與「找不到這個活動代碼，請確認後再輸入。」，不顯示「活動已失效」；同步成功過之後的 `gone` 維持 001 行為（research R4、contracts §7）。
  - (5) `currentIdentity()` 回傳 `{ code, connected }`。
  - (6) `leaveGroup` 不再附 token。
  - (7) `joinAnother` 不清除任何身分，只重設畫面。
  - 檔頭註解同步更新。
- [x] T027 [US1] 前端：修改 `src/lecture_quiz/adapters/static/js/sync.js`，讓 `connectSync(code, token, …)` 在 `token` 為 null 時送出 `{"type":"auth"}`，更新 JSDoc 的參數說明。`gone` 時呼叫的 `clearIdentity` 沿用 T025 的新行為。
- [x] T028 [US1] 前端：修改 `src/lecture_quiz/adapters/static/js/round-submission.js`，送出答案時不再附 token：把 `if (!code || !token) return;` 改成以 `currentIdentity().connected` 判斷，`apiRequest` 不傳 `token`。用 `grep -rn "currentIdentity\|getDeviceToken" src/lecture_quiz/adapters/static` 確認沒有其他頁面還在讀學生 token（004 的 `ranking-review.js` 等）。
- [x] T029 [US1] 修改 `tests/browser/test_pages.py`：原本把 token 寫進 `sessionStorage` 的 `open_student_page`，改成在該組專屬的 browser context 以 CDP `Network.setCookie` 寫入 `lq_browser`（值取自 T015 改寫後 `World.join` 保存的金鑰，`url` 為 live server 的 base），再開學生頁。docstring 註明「模擬該瀏覽器先前已加入」（research R8）。
- [x] T030 [US1] 執行 T017～T021、T029 與 Phase 2 的測試，全部通過；再跑一次完整的 `.venv\Scripts\pytest`，把數字記入 quickstart 驗證紀錄。（2026-11-26 03:12：1428 passed、0 failed，與 US2、US3 一起執行）

**Checkpoint**：US1 可以獨立驗收，同一瀏覽器在同一活動只能代表一個組別。

---

## Phase 4: User Story 2 - 同一瀏覽器的分頁狀態同步 (Priority: P1)

**Goal**：加入、離開、組別被刪除、提交狀態與活動失效，都在 2 秒內反映到同一瀏覽器的所有分頁。

**Independent Test**：同一個 context 開分頁 A、B，A 加入後 B 在 2 秒內自動切換；B 離開後 A 在 2 秒內回到加入畫面。

### 測試（先寫、先看到失敗）

- [x] T031 [P] [US2] 整合測試，加在 `tests/integration/test_007_browser_identity.py`（同一個 client 開兩條 WebSocket，代表兩個分頁）：
  - `test_leave_closes_all_tabs_of_browser`：在開放加入階段，一個分頁離開本組後，兩條連線都收到 `unauthorized LEFT_GROUP`；另一個瀏覽器（第 3 組另一位成員）的連線仍在，該組提交與成功次數不變（007 US2-AS2）。
  - `test_leave_rejected_during_round_keeps_all_tabs`：搶答中離開，回 409；兩條連線都沒有收到 unauthorized（007 US2-AS3）。
  - `test_group_delete_closes_all_tabs`：老師刪除從未提交的第 3 組，兩條連線都收到 `unauthorized GROUP_DELETED`（007 US2-AS4）。
  - `test_submission_state_reaches_other_tab`：一個分頁提交後，另一條連線在同一次推送中收到該題已送出（007 US2-AS5）。
  - `test_restart_makes_all_tabs_gone`：建立新的 app（模擬後端重啟），帶舊 cookie 連線，收到 `gone`；以 HTTP 取快照回 410（007 US2-AS6、FR-011）。
  - `test_stale_tab_action_after_leave_rejected`：離開後，同一把金鑰再送離開本組或提交，都被拒絕，原組別的資料不變（FR-012）。
- [x] T032 [P] [US2] 瀏覽器端對端測試，加在 `tests/browser/test_007_tabs.py`：
  - `test_join_in_one_tab_switches_other_tabs`：context 甲的分頁 A、B、C 都開不帶代碼的 `/student.html`，在 A 加入第 3 組，B、C 都在 2 秒內顯示第 3 組，網址變成 `?code=K`（007 US2-AS1、FR-010、SC-003）。
  - `test_leave_in_one_tab_resets_other_tabs`：在 B 按「離開本組」，A、B、C 都在 2 秒內顯示加入表單與「已離開本組」提示（007 US2-AS2、SC-003）。
  - `test_group_delete_resets_all_tabs`：A、B、C 重新加入第 1 組（從未提交）後，老師以 API 刪除第 1 組，A、B、C 都在 2 秒內顯示加入表單與「此組已被老師刪除」（007 US2-AS4、SC-003）。
  - `test_blocked_cookie_shows_message`：以 CDP `Network.setBlockedURLs` 或 `Emulation`／`Network.setCookieControls` 等方式封鎖 cookie（擇一可行的方式並記錄在測試 docstring），加入時畫面顯示 `BROWSER_SESSION_REQUIRED` 的訊息（FR-013）。若 CDP 無法封鎖 cookie，改在 quickstart 人工步驟 13 驗證，並在測試檔註明原因，不得用 mock 冒充。

### 實作

- [x] T033 [US2] 前端：在 `src/lecture_quiz/adapters/static/js/student.js` 加入跨分頁通知（research R6、contracts §5）：
  - 建立 `BroadcastChannel("lq-identity")`，瀏覽器不支援時跳過，不拋錯。
  - 加入成功後 `postMessage({ type: "joined", code })`。
  - 收到訊息時，只有在 `state.sync === null`（加入畫面），且 `code` 為字串、符合 `normalizeCode` 後長度為 6 的情況下，才 `startSync(code)` 並 `history.replaceState(null, "", "?code=" + encodeURIComponent(code))`。
  - 其他情況（已經連著某活動、格式不符）一律忽略。
- [x] T034 [US2] 確認後端不需要為 US2 修改：離開與刪除時依雜湊關閉連線，是 001 `WebSocketHub.disconnect_device` 的既有行為（research R2）。若 T031 有失敗，先查明原因再修正，並把原因寫進 `specs/007-browser-identity-sync/verification.md` 的實作問題紀錄（P-01～，比照 003～005）。
- [x] T035 [US2] 執行 T031、T032，全部通過；把結果數字記入 quickstart 驗證紀錄。

**Checkpoint**：US1、US2 都可以獨立驗收。

---

## Phase 5: User Story 3 - 老師與學生在同一瀏覽器時互不干擾 (Priority: P2)

**Goal**：同一瀏覽器的學生加入、離開或組別被刪除，都不影響老師身分；學生身分拿不到老師權限。

**Independent Test**：同一個 client 以 Bearer 建立活動，再以 cookie 加入第 1 組、離開、再加入；每一步之後，老師操作都成功。

### 測試

- [x] T036 [P] [US3] 整合測試，加在 `tests/integration/test_007_browser_identity.py`（同一個 client：老師請求帶 Bearer，學生請求不帶）：
  - `test_student_join_keeps_teacher_control`：學生加入第 1 組後，老師開輪成功（007 US3-AS1）。
  - `test_student_leave_or_delete_keeps_teacher`：學生離開本組、老師刪除第 1 組之後，老師關輪、開放加入都成功（007 US3-AS2）。
  - `test_cookie_only_cannot_do_teacher_ops`：只帶 cookie，對 10 種老師專用操作（開放加入、開輪、關輪、定案、結束、取消、刪除組別、匯入、匯出、判錯）各送一次，全部被拒，活動版本不變（007 US3-AS3、SC-005）。
- [x] T037 [P] [US3] 瀏覽器端對端測試，加在 `tests/browser/test_007_tabs.py`：
  - `test_teacher_and_student_same_context`：同一個 context 開老師頁建立活動，另一個分頁以學生身分加入第 1 組再離開；之後老師頁仍顯示老師控制區，開輪按鈕可用（007 US3-AS1、AS2）。

### 實作

- [x] T038 [US3] 確認 `src/lecture_quiz/adapters/static/js/teacher.js` 的每個請求與 WebSocket auth 都帶老師 token（Bearer 優先，research R4），不需要修改；有遺漏就補上。執行 T036、T037，全部通過並記錄。

**Checkpoint**：三個 User Story 都可以獨立驗收。

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T039 [P] 同步 001 文件，每處都加註「由 007 修訂（2026-11-26）」：
  - `specs/001-activity-session/spec.md`：FR-008、FR-009、FR-012、FR-034、US2 敘述、Key Entities「裝置身分」。
  - `specs/001-activity-session/research.md`：R5「每個分頁是一台獨立裝置」。
  - `specs/001-activity-session/contracts/http-api.md`：#3 加入回應移除 `deviceToken`、`ALREADY_IN_GROUP` 訊息、不記錄 `lq_browser` cookie。
  - `specs/001-activity-session/contracts/sync-websocket.md`：auth 的 token 可省略。
- [x] T040 [P] 同步 `diagrams/001-activity-session-component.puml`、`diagrams/001-activity-session-sequence.puml`：學生畫面與活動 API 的身分來源改為 cookie，並加註 007。重新執行 `java -jar plantuml.jar "./diagrams/001-*.puml"`，開啟 PNG 確認沒有文字重疊（憲章原則 II 補充規定 3）。
- [x] T041 [P] 改寫 `specs/001-activity-session/quickstart.md`、`specs/003-round-submission/quickstart.md`、`specs/004-ranking-review/quickstart.md`、`specs/006-ui-refresh/quickstart.md` 中「以多個分頁模擬多台裝置或多組」的步驟（4 份 quickstart 共 31 處提到「分頁」，逐一判斷是否要改），改成「以不同瀏覽器或瀏覽器設定檔模擬」，網址統一為 `http://127.0.0.1:8000`（research R9）。
- [x] T042 [P] 憲章修訂（research R11、analyze D1／D2）：已於 2026-11-26 修訂為 v1.2.0，獨立 commit `ca29a0c`。內容：技術限制 1 改為以多個瀏覽器模擬各組學生；子功能拆分表加入 006、007。CLAUDE.md 的版本已同步。剩下的工作：在 007 的 PR 說明中交代這次修訂（依使用者指示不另開 PR）。
- [x] T043 [P] 更新 `CLAUDE.md` 的「專案現況」，加入 007 一段：分支、程式位置（`adapters/web/browser_session.py`、`request_token`、INV-1），以及「學生身分改為同一瀏覽器共用、人工驗證要用不同瀏覽器模擬不同組、一律用 127.0.0.1」。
- [x] T044 [P] 更新 `tests/SCENARIO_MAP.md`：
  - 新增「007-browser-identity-sync」區段，列出 US1-AS1～AS6、US2-AS1～AS6、US3-AS1～AS3 對應的測試（依各測試 docstring 的 `Scenario: 007 USn-ASm` 掃描）。
  - 001 區段中受 T015 改名影響的測試路徑一併更新。
- [x] T045 日誌與回應檢查（SC-007、FR-008，research R10）：在 `tests/integration/test_007_browser_identity.py` 新增 `test_browser_key_never_logged_or_returned`。
  - 以 `caplog`（INFO）擷取「建立 → 匯入 → 開放加入 → browser-session → 加入 → 開輪 → 提交 → 關輪 → 離開」整個流程。
  - 斷言金鑰字串在日誌中出現 0 次、在所有回應本文中出現 0 次。
  - 用 `grep -rn "print(" src` 確認沒有新增 `print`。
- [x] T046 效能驗證（SC-006）：修改 `tests/perf/test_sync_latency.py`，讓每組 2 條連線來自 2 把不同的金鑰（2 個瀏覽器），老師加上 6 組。執行 `.venv\Scripts\pytest -m perf tests/perf/test_sync_latency.py`，記錄最大延遲，必須 ≤ 2 秒，記入 quickstart 驗證紀錄。
- [x] T047 程式碼與圖表一致性驗證（憲章原則 II）：逐一比對 `diagrams/007-browser-identity-sync-{component,class,sequence}.puml` 與實作，項目如下：
  - 組件名稱：`browser-session`、`request_token`、`WebSocketHub` auth、`ActivityStateMachine._join_group`、`BroadcastChannel lq-identity`。
  - 類別欄位：`BrowserKey`、`DeviceIdentity.token_hash`、`ActivityService.join` 的參數。
  - 時序：先發金鑰 → 加入 → 通知 → 拒絕 → 離開 → 舊身分。

  有差異時先改圖，再執行 `java -jar plantuml.jar "./diagrams/007-*.puml"`，並開啟 PNG 檢查。
- [x] T048 執行 `ruff check .`、`ruff format --check .`、`mypy`，全部通過，記錄指令與結果（憲章技術限制 2）。
- [x] T049 執行完整的 `.venv\Scripts\pytest`（預設排除 perf、real_google），記錄日期、指令與通過／失敗／略過數，與 T002 的基準比對後寫入 quickstart 驗證紀錄（憲章原則 VI）。
- [x] T050 獨立審查：交給另一個 agent 或 session 審查本分支的差異（例如 `harness:silent-failure-hunter`、`harness:pr-test-analyzer`），重點如下：
  - 加入競爭（INV-1）。
  - cookie 路徑是否真的被測試走到（沒有任何 007 測試帶 Bearer 冒充學生）。
  - 金鑰外洩。
  - 老師與學生在同一瀏覽器時的互動。

  把發現與處理方式記入 `specs/007-browser-identity-sync/verification.md` 的實作問題紀錄（P-01～，比照 003～005）。
- [x] T051 非實作者依 `specs/007-browser-identity-sync/quickstart.md` 人工驗證 1～14 項，記錄日期、執行者、操作與結果（憲章原則 VI）；沒有實際執行的項目不得勾選。

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：沒有相依。T002 必須在任何程式改動之前完成，否則基準就失去意義。
- **Foundational（Phase 2）**：相依於 Phase 1，阻擋所有 User Story。T016 通過後才能進入 Phase 3。
- **US1（Phase 3）**：相依於 Phase 2。
- **US2（Phase 4）**：前端部分（T033）相依於 US1 的 `student.js` 改寫（T026）；後端測試（T031）只相依於 Phase 2。
- **US3（Phase 5）**：只相依於 Phase 2，可以與 US1、US2 平行；T037 的瀏覽器測試相依於 T026。
- **Polish（Phase 6）**：相依於 US1～US3 都完成。T039～T044 可以彼此平行；T047～T051 依序執行。

### Within Each Phase

- 先寫測試並確認失敗，再實作。
- 核心（T022、T023）在轉接層（T024）之前；後端在前端（T025～T028）之前。
- 同一個檔案的任務不標 [P]。例如 T018、T019、T031、T036、T045 都改 `tests/integration/test_007_browser_identity.py`，彼此依序執行；它們的 [P] 只表示可以和「其他檔案」的任務平行。

### Parallel Opportunities

- Phase 2：T004、T005、T006 可以平行；T008 與 T009 可以平行。
- Phase 3：T017（核心測試）、T020（WS 契約）、T021（瀏覽器測試）可以平行撰寫。
- Phase 6：T039～T044 都是不同檔案，可以平行。

---

## Parallel Example: User Story 1

```text
Task: "T017 核心單元測試 INV-1 in tests/unit/core/test_state_machine_join.py"
Task: "T020 WebSocket auth 讀 cookie 的契約測試 in tests/contract/test_ws_sync.py"
Task: "T021 同一個 context 兩個分頁的瀏覽器測試 in tests/browser/test_007_tabs.py"
```

---

## Implementation Strategy

### MVP First（User Story 1）

1. Phase 1：記下基準。
2. Phase 2：完成金鑰、端點、身分來源與測試輔助函式；完整測試沒有回歸（T016）。
3. Phase 3：完成 US1。這時「同一瀏覽器開多分頁佔用他組」已經被擋下，達成本子功能的主要目的。
4. **STOP and VALIDATE**：執行 quickstart 人工步驟 1～3、9。

### Incremental Delivery

1. US1 → 擋下佔用他組（MVP）。
2. US2 → 跨分頁同步，畫面不再停在過期的狀態。
3. US3 → 確認老師與學生在同一瀏覽器時不受影響。
4. Polish → 文件、圖表、憲章同步，以及效能、日誌、人工驗證。

---

## Notes

- 所有學生路徑的 007 測試都不帶 Bearer；Bearer 只用於老師請求，以及 T014、T015 改寫後的既有測試輔助函式（research R8）。
- 測試失敗時不得放寬斷言或改用 mock 繞過；CDP 做不到的項目改成人工驗證，並註明原因（T032）。
- 每完成一個 Phase 就 commit 一次，commit 格式為 `<type>: <summary>`。
