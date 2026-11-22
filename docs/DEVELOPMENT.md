# 開發指南：環境、指令與子功能擴充約定

本文件說明共用骨架（Issue #5、`chore/5-project-skeleton`）的使用方式。002～005 依這裡的約定擴充，避免多人同時修改共用檔案時互相覆蓋。

## 環境建立（Windows，Python 3.11 以上）

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

`.venv/` 已列在 `.gitignore`，不要提交。

> **專案路徑含中文時（例如放在「中央大學」資料夾）**：Python 3.11 在繁中 Windows（cp950）讀不了 `pip install -e` 寫入的 `.pth`，`.venv` 裡的 Python 會直接啟動失敗（`UnicodeDecodeError: 'cp950' codec can't decode ...`）。安裝完成後執行下面這一行，改成 ASCII 相對路徑即可；之後重新執行 `pip install -e` 時要再改一次。
>
> ```powershell
> Set-Content .venv\Lib\site-packages\_editable_impl_lecture_quiz.pth "../../../src" -Encoding ascii
> ```

## 常用指令

| 用途 | 指令 |
|---|---|
| lint | `.venv\Scripts\ruff check .` |
| 格式檢查 | `.venv\Scripts\ruff format --check .`（自動排版：`ruff format .`） |
| 型別檢查 | `.venv\Scripts\mypy`（設定檔已指定 `src/`） |
| 測試 | `.venv\Scripts\pytest`（預設排除 `perf`） |
| 效能測試 | `.venv\Scripts\pytest -m perf` |
| 啟動後端 | `.venv\Scripts\python -m lecture_quiz`，開啟 <http://127.0.0.1:8000/> |

依憲章技術限制 2，提交前 `ruff check`、`ruff format --check`、`mypy` 三項都必須通過。

- `python -m lecture_quiz` 只監聽 `127.0.0.1`。連接埠可以用環境變數 `LECTURE_QUIZ_PORT` 指定，預設 8000。
- 這個指令會讓 uvicorn 的日誌也輸出到 stdout，並關閉 uvicorn 的 access log（access log 會記錄查詢字串）。
- 也可以用 `uvicorn lecture_quiz.main:app --host 127.0.0.1`，但 uvicorn 自己的日誌會輸出到 stderr。

## 目錄與分層

```text
src/lecture_quiz/
├── main.py                 # 組裝 app（共用檔案，見下方約定）
├── __main__.py             # python -m lecture_quiz
├── core/<能力>/            # 純函式：不得匯入 app、adapters、fastapi、starlette、asyncio、socket、time，不得讀系統時鐘
├── app/<能力>/             # 服務層：只依賴 core 與自己的 ports
└── adapters/
    ├── clock.py            # SystemClock
    ├── web/common.py       # 共用：錯誤格式、例外處理、請求日誌、Bearer／Idempotency-Key 解析
    ├── web/system.py       # GET /api/health（也是 router 寫法的範例）
    ├── web/<能力>.py       # 各子功能的 router
    └── static/             # 前端：index.html、teacher.html、student.html、css/、js/
tests/
├── conftest.py             # FakeClock、make_app、client fixture
├── architecture/           # test_core_is_pure.py 自動檢查核心是否為純函式
├── unit/core/、unit/app/、contract/、integration/、perf/
```

相依方向只能是 `adapters → app → core`（技術限制 4，NON-NEGOTIABLE）。`core` 違規時，`tests/architecture/test_core_is_pure.py` 會失敗。

## 子功能擴充約定（Issue #5）

| 檔案或目錄 | 約定 |
|---|---|
| `src/lecture_quiz/main.py` | 只在「子功能 router」區塊加**一行** |
| `teacher.html`／`student.html` | 只在「子功能區塊」加**一個** `<section>`，在「子功能 script」加**一行** `<script>` |
| `static/js/<能力>.js` | 各子功能的前端邏輯，例如 002 用 `js/import.js` |
| `static/css/app.css` | 子功能樣式追加在檔案最後 |
| `pyproject.toml` | 相依追加在列表最後（002 的 Google 套件同理） |
| 程式碼 | 放在自己的 `core/<能力>/`、`app/<能力>/`、`adapters/web/<能力>.py` |
| `tests/conftest.py` | 子功能專屬的 fixture 追加在最後，或放在自己測試目錄的 `conftest.py` |
| `docs/alignment.md` | 決議表都追加在最後；衝突時保留兩邊的列 |

### 1. 後端 router

在 `adapters/web/<能力>.py` 提供 `create_router(app: FastAPI) -> APIRouter`，寫法參考 `adapters/web/system.py`：

```python
from fastapi import APIRouter, FastAPI


def create_router(app: FastAPI) -> APIRouter:
    """建立 Guided Notes 匯入的 router。"""
    router = APIRouter(tags=["import"])
    # 需要時間時用 app.state.clock.now()，不要直接讀系統時鐘
    ...
    return router
```

再到 `main.py` 的區塊加一行（路徑自動加上 `/api` 前綴）：

```text
    # ── 子功能 router：每個子功能只加一行（順序不限）──
    api.include_router(system.create_router(app))
    api.include_router(guided_notes.create_router(app))   # ← 002 只加這一行
    # ── 子功能 router 結束 ──
```

靜態檔掛在 `/`，必須最後掛載；router 與 WebSocket 路由都要加在它之前。`create_app` 已經處理好這個順序。

### 2. 錯誤與日誌

- **業務錯誤**：`raise ApiError(狀態碼, "錯誤代碼", "可修正的中文說明")`，或直接回傳 `error_response(...)`。格式一律是 `{"error": {"code", "message"}}`。
- **請求格式不符**：自動回 400 `INVALID_REQUEST`，訊息會指出欄位。
- **未預期的例外**：自動回 500 與通用訊息，不含堆疊追蹤；細節只寫入伺服端日誌。因此例外訊息裡不得放 token 或憑證。
- **請求日誌**：每個請求自動記錄一行 `INFO`，只含方法、路徑樣板、活動代碼、結果代碼、狀態碼、版本號、耗時。需要補上版本號或結果代碼時，呼叫 `annotate_request_log(request, result=..., version=...)`。不要自己記錄標頭或本文。
- **身分與去重**：用 dependency 取得 token 與 key：

  ```python
  token: Annotated[str | None, Depends(bearer_token)]
  key: Annotated[str | None, Depends(idempotency_key)]
  ```

- **日誌寫法**：只用 `logging.getLogger(__name__)`，不用 `print`，不得記錄 token、授權碼、client secret（技術限制 3）。

### 3. 前端

在 `teacher.html`（或 `student.html`）加一個區塊和一行 script：

```html
    <!-- ── 子功能區塊開始 ── -->
    <section id="import-section" data-feature="002-guided-notes-import"></section>
    <!-- ── 子功能區塊結束 ── -->
  ...
  <!-- ── 子功能 script 開始（每個子功能一行）── -->
  <script type="module" src="js/import.js"></script>
  <!-- ── 子功能 script 結束 ── -->
```

`js/<能力>.js` 是 ES module，可以使用以下共用模組：

| 模組 | 提供 |
|---|---|
| `js/api.js` | `apiRequest(method, path, {token, body, idempotencyKey})`：自動帶 `Authorization`，POST／DELETE 自動帶 `Idempotency-Key`，網路失敗重試時沿用同一個 key；回傳 `{ok, status, data, error}`。`showError(element, error)` 以 `textContent` 顯示錯誤 |
| `js/identity.js` | `getTeacherToken`、`setTeacherToken`（localStorage，⚠ Q-04）、`getDeviceToken`、`setDeviceToken`（sessionStorage）、`clearIdentity`、`normalizeCode` |
| `js/sync.js` | `connectSync(code, token, {onSnapshot, onGone, onUnauthorized})`：處理 auth、重連、25 秒無訊息判定中斷、丟棄舊版本、`gone`、右下角 `v{version}｜延遲` |

- 不可信的文字（組名、學習單內容、學生答案）一律用 `textContent` 輸出，不得用 `innerHTML`（原則 V）。
- 「成功」類提示加上 `class="success-hint"`；同步中斷時會自動隱藏（FR-028）。

### 4. 測試

- 需要時間的測試用 `fake_clock` fixture，以 `advance(seconds)` 控制時間。
- 需要 HTTP 的測試用 `client` fixture（`TestClient`）。
- 每個 Acceptance Scenario 至少要有一個測試，docstring 第一行寫 `Scenario: USn-ASm`（原則 VI）。
