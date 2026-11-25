"""005 前端靜態檢查（憲章原則 V、FR-029、FR-032；Scenario: US2-AS5、US6-AS3）。

前端沒有 JavaScript 測試環境，以字串規則與 `node --check` 檢查：
1. `result-export.js` 不使用會解析 HTML 的 API（不可信文字一律 `textContent`）。
2. `result-export.js` 在模組頂層同步讀取網址的 `auth` 參數：002 的 `import.js` 會在收到
   第一份快照後刪除它，晚讀就拿不到（授權完成後回到預覽，FR-010）。
3. 保護前綴的固定說明文字存在（FR-029）。
4. 語法正確。
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[2] / "src/lecture_quiz/adapters/static"
JS = STATIC / "js" / "result-export.js"
FORBIDDEN = (
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "eval(",
    "new Function",
)
NOTE = "文字保護前綴只為安全開啟，不代表原答案被修改"


def _code() -> str:
    """去掉註解後的原始碼。"""
    text = JS.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", text)


def test_no_html_parsing_apis():
    """Scenario: US6-AS3 / FR-032：不使用會解析 HTML 的 API。"""
    code = _code()
    for word in FORBIDDEN:
        assert word not in code, word


def test_auth_param_is_read_synchronously_at_module_top():
    """Scenario: US2-AS5：auth 參數在模組頂層讀取，早於任何快照事件。"""
    code = _code()
    match = re.search(r"(?m)^const \w+ = .*window\.location\.search.*$", code)
    assert match, "必須在模組頂層讀取 window.location.search"
    assert match.start() < code.index("onTeacherSnapshot(")
    assert "history.replaceState" not in code, "不得自己清除參數，以免影響 002 的處理"


def test_protection_prefix_note_is_fixed_text():
    """Scenario: US6-AS3 / FR-029：說明文字是固定字串，不由後端或使用者輸入產生。"""
    page = (STATIC / "teacher.html").read_text(encoding="utf-8")
    assert NOTE in page or NOTE in JS.read_text(encoding="utf-8")


def test_javascript_syntax(tmp_path):
    """語法檢查（沒有 node 時明確失敗，不得跳過）。"""
    node = shutil.which("node")
    assert node is not None, "找不到 node，無法檢查 JavaScript 語法"
    copy = tmp_path / "result-export.mjs"
    copy.write_text(JS.read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(copy)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "element_id", ["export-reauth-button", "export-structure-list"]
)
def test_page_has_required_elements(element_id):
    """頁面有 JS 依賴的元素。"""
    assert f'id="{element_id}"' in (STATIC / "teacher.html").read_text(encoding="utf-8")
