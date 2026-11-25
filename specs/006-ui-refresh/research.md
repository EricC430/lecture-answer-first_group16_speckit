# Research: 006 介面改版

**日期**：2026-11-25｜**依據**：[spec.md](spec.md)、[diagrams/006-ui-refresh-*.puml](../../diagrams/)、現有前端 `src/lecture_quiz/adapters/static/`（以 `feature/9-005-result-export` @ f0f45da 為基準）

每一項以「決定／理由／考慮過的替代方案」記錄。

## R1 前端技術：沿用原生 HTML／CSS／ES modules，不引入框架或建置步驟

- **決定**：維持 FastAPI 直接送出靜態檔、原生 ES modules 的架構；樣式用純 CSS 自訂屬性（CSS variables）。不加 Node、打包工具、Tailwind、React。
- **理由**：Issue #28 已決定；001～005 的畫面邏輯都是原生模組，換框架等於重寫並違反 FR-001／FR-003；憲章原則 VII 要求不做超出需求的設計；評分會對照 plan 與程式碼，新增建置鏈會擴大不一致的風險。
- **替代方案**：Tailwind CDN（需網路、違反 FR-006）、React／Next.js（重寫所有畫面，期限內不可行）。

## R2 樣式檔拆分與設計基準值

- **決定**：
  - `css/tokens.css`：只放 `:root` 的設計基準值（色彩、字體、字級、間距、圓角、動畫時間），是全站唯一定義數值的地方（FR-004）。
  - `css/app.css`：改寫為基礎樣式＋共用元件＋老師頁／學生頁版面，只引用 `var(--…)`。各子功能原本追加在檔尾的樣式改寫為引用基準值，類別名稱不變。
  - `css/projection.css`：投影畫面專用（大字與投影版面）。
  - 每個 HTML 先載入 `tokens.css` 再載入 `app.css`。
- **理由**：基準值集中一處，才能用自動測試檢查對比與「沒有寫死色碼」；檔案數少、不需要建置。
- **替代方案**：每個元件一個 CSS 檔（請求數多、無打包時載入順序難管理）；把基準值寫在 `app.css` 頂端（可行，但測試要解析整份檔案，且容易被後續追加的樣式混入色碼）。
- **色彩（取自參考範本的方向，最終數值以 R10 對比測試通過為準）**：

  | 基準值 | 值 | 用途 |
  |---|---|---|
  | `--color-canvas` | `#f2f8f7` | 頁面畫布（不用純白） |
  | `--color-surface` | `#ffffff` | 表單欄位、表格底 |
  | `--color-card` | `#e4f0f1` | 卡片、面板 |
  | `--color-band` | `#f2e8e2` | 交替區塊、投影畫面的結果帶 |
  | `--color-text` | `#283338` | 主要文字 |
  | `--color-text-muted` | `#4a5a60` | 次要文字（範本的 `#333333` 以外再加深一階，確保在 `--color-card` 上 ≥ 4.5:1） |
  | `--color-primary` | `#1c5d5f` | 唯一的主要按鈕底色、目前階段 |
  | `--color-on-primary` | `#ffffff` | 主要、次要、危險實心按鈕上的文字 |
  | `--color-primary-hover` | `#156152` | 主要按鈕 hover／按下 |
  | `--color-secondary` | `#16325a` | 次要實心按鈕 |
  | `--color-outline` | `#0e4749` | 幽靈按鈕邊框與文字 |
  | `--color-accent` | `#65b8a2` | 插圖、裝飾線（不承載文字） |
  | `--color-rose` | `#d6aec1` | 插圖、裝飾（不承載文字） |
  | `--color-border` | `#a2cbcd` | 裝飾細線、區塊分隔（不承載資訊，1.63:1，不列入對比檢查） |
  | `--color-border-strong` | `#5b7c80` | 輸入欄位、核取方塊、表格外框等介面元件邊界（對白底 4.53、畫布 4.21、卡片 3.89，≥ 3:1） |
  | `--color-success` / `--color-success-bg` | `#1b6b3a` / `#dcefe3` | 搶答成功、已送出、寫回成功 |
  | `--color-danger` / `--color-danger-bg` | `#9b1c2e` / `#f8e1e4` | 答錯、送出失敗、寫回失敗、破壞性按鈕 |
  | `--color-warning` / `--color-warning-bg` | `#7a4b00` / `#fff1cc` | 同步中斷、接近截止 |
  | `--color-neutral` / `--color-neutral-bg` | `#3d4a50` / `#e6eaeb` | 搶答失敗、未成功、未送出 |
  | `--color-focus` | `#16325a` | 焦點外框（3px，與底色對比 ≥ 3:1） |

  2026-11-25 以 WCAG 2.1 相對亮度公式試算（scratchpad 腳本，正式檢查由 R10 的測試負責）：主要文字 10.75～12.06、次要文字 5.96～6.69、白字在主色 7.55、在次要主色 12.82、在危險色 8.08，四組狀態色 5.45～7.56，焦點外框 ≥ 11.01；負對照 `#777777` on `#ffffff` 為 4.48（應判不合格）。

  成功、危險、警示、中性這四組語意色是範本沒有的，為狀態標籤（FR-015）新增；色相取自範本的青、玫瑰、沙色系並加深。

## R3 字體：本機提供開源字體，中文標題用子集化的襯線字

- **決定**：
  - **標題（襯線）**：Noto Serif TC（SIL OFL 1.1），只取 600 字重，以 fonttools 子集化：收錄 `static/` 下所有 HTML、JS 中出現的中日韓字元與 ASCII，輸出一個 woff2。子集外的字（例如答案裡的罕用字，但答案不用標題字體）退回系統字體。
  - **內文與操作元件（無襯線）**：Inter 可變字體（OFL，只取 Latin 子集）處理英數；中文用系統字體 `"Microsoft JhengHei", "Noto Sans TC", "PingFang TC", sans-serif`。
  - **眉標、活動代碼、倒數（等寬）**：IBM Plex Mono 400／600（OFL，Latin）。
  - 字型檔放 `static/fonts/`，同目錄附 OFL 授權文字；`font-display: swap`。
  - 子集化工具 `scripts/build_font_subset.py`（開發者手動執行，產物 commit 進 repo）；fonttools 與 brotli 列為選用的 `[project.optional-dependencies] fonts`，不進執行期相依。
- **理由**：FR-006 要求離線可用；參考範本的專有字型（Sofia Pro、P22 Mackinac Pro）不能用；完整的 Noto Serif TC 每個字重約數 MB，子集化後只剩數百 KB；中文內文用系統字體，避免下載大字型且閱讀體驗穩定。2026-11-25 已確認 google/fonts repo 的三個字型檔可下載（HTTP 200）。
- **替代方案**：Google Fonts CDN（需網路，違反 FR-006）；中文標題也用系統字體（Windows 只有新細明體可當襯線，大字效果差）；整套 Noto Serif TC（檔案過大）。
- **風險**：日後新增的畫面文字若不在子集中，會退回系統襯線字。緩解：`tests/unit/ui/test_font_subset.py` 檢查 `static/` 中所有標題可能出現的中文字都在子集內（讀取 woff2 的 cmap），漏字時測試失敗並提示重新執行子集化。

## R4 老師頁兩欄與分頁：搬移既有區塊，不改區塊 id

- **決定**：
  - `teacher.html` 改為 `<div class="teacher-layout">`，左欄 `<aside id="teacher-sidebar">` 放 `#activity-section`（含開輪表單）與「開啟投影畫面」按鈕；右欄 `<div id="teacher-workspace">` 放分頁列 `role="tablist"` 與四個分頁面板 `role="tabpanel"`。
  - 既有的 `<section>` 原封搬進對應面板，id、`data-feature`、內部元素 id 都不變：「匯入」＝`#import-section`；「作答看板」＝`#round-submission-section`＋`#published-section`；「順位與判錯」＝`#ranking-review-section`；「寫回」＝`#export-section`。
  - 新增 `js/teacher-layout.js`：
    1. 用 `MutationObserver` 監看各區塊的 `hidden` 屬性：面板內的區塊全部隱藏時，該分頁標籤也隱藏（FR-017d，顯示時機與改版前一致，因為仍由各子功能腳本決定區塊是否顯示）。
    2. 透過 `onTeacherSnapshot` 取得階段；只有在 `snapshot.stage` 與上一次不同時，才依階段對照表切換分頁（FR-017b）。
    3. 監看非作用中面板內的 DOM 變動（`childList`、`characterData`、`subtree`），有變動就在標籤加上「有更新」（FR-017c）；切到該分頁時移除。
    4. 分頁標籤的鍵盤操作依 WAI-ARIA Tabs 樣式：左右方向鍵移動、Home／End、Enter／空白鍵選取（自動啟用模式不採用，避免方向鍵就切換造成閱讀中斷）；`aria-selected`、`aria-controls`、`tabindex` 由此模組維護（FR-017e）。
  - 1024px 以下以 CSS 改成單欄（FR-017a）。
- **理由**：既有腳本都以 `getElementById` 與 `section[data-feature]` 取元素（2026-11-25 grep 確認，沒有依賴 `main > section` 的程式），搬移位置不影響行為；`hidden` 仍由原本的子功能腳本控制，分頁只「跟隨」它，不會產生新的顯示規則。
- **替代方案**：各子功能腳本自行通知分頁模組（要改 5 個子功能的腳本，違反只改呈現的原則）；用 CSS `:has()` 隱藏空分頁（無法處理「有更新」與自動切換）。
- **階段 → 分頁對照**：`PREPARING`、`JOINING` → 匯入；`ROUND_OPEN` → 作答看板；`RESULT_PENDING`、`RESULT_FINAL` → 順位與判錯；`ENDED` → 寫回；`CANCELLED` → 不切換（寫回分頁本來就隱藏）。目標分頁若被隱藏，則改選第一個可見分頁。

## R5 投影畫面的資料來源：沿用老師的同步通道，前端以白名單轉成投影檢視

- **決定**：
  - 新頁面 `projection.html?code=XXXX`（活動代碼不是機密，學生本來就要知道；token 不放網址）。頁面以 `identity.getTeacherToken(code)` 取得同一瀏覽器的老師 token（localStorage，分頁共用，001 研究 R5），用既有 `sync.connectSync` 連線。沒有 token 時顯示「請從老師頁開啟投影畫面」，不連線。
  - 收到的老師快照**只**交給純函式 `toProjectionView(snapshot)`（`js/projection-view.js`），由它依白名單建立一個新物件；畫面渲染只讀這個新物件，不碰原始快照（FR-031、FR-032）。白名單見 [contracts/projection-view.md](contracts/projection-view.md)。
  - 搶答中（`stage === "ROUND_OPEN"`）白名單**完全不讀** `submissions.current`；關輪後只讀 `submissions.published`（003 已對所有角色公開）與 `ranking.rounds` 中與 004 學生版相同的欄位（`rank`、`groupNumber`、`displayStatus`、`judgedWrong`、`successGroup`、`replacedGroup`、`final`、`resultVersion`），丟棄 `reason`、`countAtProcessing`、`groupCounts`、`actions`。
  - 只顯示「目前輪」（001 快照的目前輪次）已關輪的結果；進入下一輪搶答中時清空結果（US7-AS7）。
  - 各輪記住最大 `resultVersion`，較小的不覆蓋（FR-034；沿用 004 前端的做法）。
- **理由**：FR-031 規定不得新增後端資料或放寬權限；老師快照已包含所需資料，而且投影畫面就在老師自己的瀏覽器裡執行，沒有把資料交給學生的裝置。風險在「畫面誤顯示搶答中的答案」，所以把過濾集中成一個可單獨測試的純函式，並以真實瀏覽器測試檢查搶答中的 DOM 文字不含任何答案（SC-010）。
- **替代方案**：新增後端「投影檢視者」角色與快照裁切（最安全，但違反 FR-031，且要改 001 的身分模型）；以裝置 token 加入一個假組別（會占用組號、出現在老師的組別表，改變行為）；直接渲染老師快照再用 CSS 隱藏（答案仍在 DOM 中，可被誤顯示，不採用）。

## R6 學生頁：送出狀態與題號導覽

- **決定**：
  - 送出狀態：`submission.js` 現有的 `setBusy`／錯誤／成功流程**只增加**在作答卡片上設定 `data-submit-state="idle|busy|done|error"`（不改流程、不改文字），樣式由 CSS 依屬性呈現（FR-009）。「已送出」標籤沿用既有 `success-hint` 類別，同步中斷時自動隱藏（001 FR-028，FR-012）。
  - 題號導覽：新增 `js/question-nav.js`，監看 `#answer-forms` 的子元素與各卡片的 `data-submit-state`，在 `#round-submission-section` 頂端產生 `<nav aria-label="題號導覽">`，每題一個連結（`href="#…"` 指向卡片標題、點擊後把焦點移到標題）；`position: sticky`，高度不超過 56px，不遮倒數（倒數列也 sticky、排在導覽上方）（FR-008a）。只有本輪開放題數 ≥ 2 時出現。資料只來自本頁已渲染的本組卡片，沒有他組資訊。
  - 接近截止：`round-submission.js` 已有倒數；**只增加**剩餘 ≤ 10 秒時在倒數元素設定 `data-urgent`，CSS 以顏色與粗框表示，不閃爍（FR-010）。
- **理由**：送出流程與倒數邏輯完全不變，只多一個屬性給 CSS；導覽由獨立模組根據既有 DOM 產生，不需要改 003 的資料流。
- **替代方案**：重寫作答卡片的渲染（風險高）；只用文字狀態（不符合 FR-009 的視覺區分）。

## R7 一致的狀態標籤與新資料提示

- **決定**：
  - 新增 `css` 元件 `.status-label` 與修飾類 `.status-label--success|danger|warning|neutral`，每個標籤包含 SVG 圖示（勾、叉、驚嘆號、橫線）＋文字，不只靠顏色（FR-015）。004 的 `status-*` 類別（`ranking-entry.status-success` 等）由 CSS 對應到同一套外觀，不改 004 腳本；005 的寫回狀態文字由 CSS 選擇器套用。對照表見 [data-model.md](data-model.md)「狀態標籤」。
  - 新資料提示：新增 `js/feedback.js`，用 `MutationObserver` 監看作答看板、順位清單與投影結果區，對新加入的列加上 `.is-new`，CSS 以 1.5 秒的背景淡出提示，不移動焦點（FR-020）。`prefers-reduced-motion: reduce` 時不做動畫，改為 1.5 秒的靜態外框（FR-016）。
- **理由**：不改各子功能腳本即可統一外觀；`MutationObserver` 只看 DOM 結果，不影響資料流程。
- **替代方案**：在每個子功能腳本加呼叫（改動面大）。

## R8 動畫與減少動態效果

- **決定**：動畫時間基準值 `--duration-fast: 150ms`、`--duration-base: 250ms`、`--duration-highlight: 1500ms`；只用 `opacity`、`background-color`、`transform`（不動畫寬高）。`@media (prefers-reduced-motion: reduce)` 下全域把 `animation` 與 `transition` 設為無，並把基準值歸零（FR-016）。狀態切換不得延遲新內容顯示：過場一律在內容已更新之後才播放（FR-014）。
- **理由**：符合 ui-ux-pro-max 的 UX 規則（150～300ms、ease-out、尊重減少動態效果、每個畫面只有 1～2 個重點動畫）。
- **替代方案**：GSAP（需外部函式庫，沒有必要）。

## R9 插圖

- **決定**：
  - 空狀態小插圖：Claude 手寫 SVG，集中在 `static/img/illustrations.svg`（`<symbol>` 精靈圖），頁面以 `<svg><use href="img/illustrations.svg#…"></use></svg>` 引用；線條與填色用 `currentColor` 與 CSS 自訂屬性（自訂屬性會繼承到 `<use>` 的內容），因此顏色跟著基準值。純裝飾的插圖加 `aria-hidden="true"`（FR-024）。至少四張：`empty-groups`（尚未有組別）、`empty-import`（尚未匯入）、`empty-round`（尚未開輪／等待老師）、`empty-results`（尚無結果）。
  - 首頁主插圖：組員依 Claude 提供的提示詞以 AI 生成，Claude 轉成 `static/img/hero.webp`（寬 1600px、≤ 300KB），附替代文字；生成工具、提示詞、日期與服務條款確認寫在 `specs/006-ui-refresh/illustrations.md`（FR-023）。提示詞在 tasks 階段提供，主題與色票取自 R2。
  - 主插圖尚未交付前，首頁以一張手寫 SVG 暫代，確保版面與測試不因插圖缺席而中斷。
- **理由**：Clarification 第 3 題的決定；SVG 精靈圖離線可用、可換色、體積小。
- **替代方案**：內嵌 SVG 到每個 HTML（重複、難維護）；`<img src="*.svg">`（無法繼承 CSS 變數）。

## R10 驗證方式

- **決定**：
  1. **既有測試全數通過**（FR-003、SC-001）：`pytest`（預設排除 `perf`、`real_google`）含 `tests/browser/`。
  2. **對比自動檢查**（FR-025、SC-003）：`tests/unit/ui/test_contrast.py` 解析 `tokens.css` 的色彩基準值，依 [contracts/design-tokens.md](contracts/design-tokens.md) 列出的「文字／背景」與「圖形／背景」組合計算 WCAG 2.1 對比；文字 < 4.5 或圖形 < 3.0 即失敗。負對照：測試內加入一組已知不合格的色對（`#777777` on `#ffffff`，4.48:1），確認判定函式會失敗。
  3. **沒有寫死色碼**（FR-004）：`tests/unit/ui/test_no_hardcoded_colors.py` 掃描 `app.css`、`projection.css` 與 `static/*.html` 的 `style` 屬性，除 `tokens.css` 外出現 `#rgb`、`rgb(`、`hsl(` 即失敗（允許 `transparent`、`currentColor`）。
  4. **真實瀏覽器測試**（新增 `tests/browser/test_ui_*.py`，每個 User Story 一個檔案，沿用 CDP 工具）：分頁自動切換與手動切換、「有更新」標記、投影畫面搶答中不含任何答案（SC-010，掃描 DOM 文字是否出現任何已送出答案）、判錯後 2 秒內出現遞補（量 10 次）、題號導覽、送出狀態屬性、375px 無整頁水平捲動（`scrollWidth <= clientWidth`）、點擊目標 ≥ 44×44、減少動態效果（CDP `Emulation.setEmulatedMedia`）下計算後的 `animation-duration` 為 0、頁面沒有載入任何外部網域的字型或圖片（離線，SC-009）。
  5. **截圖**：同一組測試以 CDP `Page.captureScreenshot` 在 375／768／1024／1440 與投影 1280×720／1920×1080 存下截圖到 `specs/006-ui-refresh/screenshots/`，作為 SC-002、SC-005 的人工比對依據，並由人實際打開檢視。
  6. **效能**（SC-008）：沿用 001 的 `perf` 測試（老師 + 6 組 × 2 條連線），改版後重跑並記錄數字。
  7. **人工驗證**（SC-004、SC-006、SC-007、SC-011，憲章原則 VI）：非實作者依 [quickstart.md](quickstart.md) 操作並記錄。
- **理由**：每個 Scenario 都要有自動化測試（原則 VI）；對比與色碼可以用純計算驗證；版面與互動只能在真實瀏覽器驗證。
- **替代方案**：axe-core（需外部函式庫或網路，且 CDP 工具已足夠涵蓋本 spec 的檢查項）。

## R11 擴充約定與文件

- **決定**：更新 `docs/DEVELOPMENT.md` 的前端擴充約定：老師頁的新子功能區塊放進右欄的對應分頁面板（或新增分頁，並在 `teacher-layout.js` 的對照表登記）；新樣式只能引用 `tokens.css` 的基準值。CLAUDE.md 的「專案現況」在決定併入 main 時才更新（spec Assumptions：實驗分支）。
- **理由**：組員後續新增畫面時不會破壞版面或寫死色碼。

## R12 與 005 分支的關係

- **決定**：本分支疊在 `feature/9-005-result-export`（PR #25）上；005 若再修改畫面，006 以 `git rebase origin/feature/9-005-result-export` 跟進。改版只動 HTML 結構、CSS 與新增模組，對既有子功能腳本只做兩處「加屬性」的修改（R6：`submission.js` 的 `data-submit-state`、`round-submission.js` 的 `data-urgent`），以降低衝突。
- **理由**：Issue #28「分支策略」。
