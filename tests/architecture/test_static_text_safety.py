"""US6：前端靜態檢查（FR-031、FR-032、SC-008；Scenario: US6-AS1、AS2、AS4）。

前端沒有 JavaScript 測試環境，以字串規則檢查三件事：
1. 顯示答案與訊息的檔案不使用會解析 HTML 的 API（文字一律 `textContent`）。
2. 倒數歸零時停用作答表單；沒有截止時間時顯示「由老師結束」。
3. 「已送出」只在收到成功回應，或依後端快照（同組其他裝置已送出）時顯示；
   網路錯誤顯示「送出結果未確認，請重試」。

003 的前端依 DEVELOPMENT.md 放在獨立模組（問題紀錄 P-07、P-18）。
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

JS_DIR = Path(__file__).resolve().parents[2] / "src/lecture_quiz/adapters/static/js"
CHECKED = (
    "submission.js",
    "round-submission.js",
    "round-submission-teacher.js",
    "student.js",
    "teacher.js",
)
FORBIDDEN = (
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "eval(",
    "new Function",
)


def _source(name: str) -> str:
    """去掉註解後的原始碼（註解裡的說明文字不算數）。"""
    text = (JS_DIR / name).read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", text)


def _block(source: str, start: int) -> tuple[int, int]:
    """從 `start` 之後第一個 `{` 起，回傳對應的區塊範圍。"""
    open_at = source.index("{", start)
    depth = 0
    for index in range(open_at, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return open_at, index
    raise AssertionError("大括號不成對")


def _function(source: str, name: str) -> tuple[int, int]:
    match = re.search(rf"\bfunction\s+{name}\s*\(|^\s*{name}\s*\(", source, re.M)
    assert match, f"找不到函式 {name}"
    _, end = _block(source, match.end())
    return match.start(), end  # 含參數列（預設值也算在函式內）


def _inside(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position <= end for start, end in spans)


@pytest.mark.parametrize("name", CHECKED)
def test_no_html_parsing_apis(name):
    """Scenario: US6-AS1（OpenSpec「特殊文字答案」）：答案與訊息以純文字顯示。"""
    source = _source(name)
    for api in FORBIDDEN:
        assert api not in source, f"{name} 使用了 {api}"


def test_deadline_disables_forms_and_open_ended_round_is_labelled():
    """Scenario: US6-AS2、US6-AS3：倒數歸零停用作答；沒有截止時間顯示由老師結束。"""
    source = _source("round-submission.js")
    start, end = _function(source, "lockAfterDeadline")
    assert "setDisabled(true)" in source[start:end]
    start, end = _function(source, "scheduleDeadline")
    body = source[start:end]
    assert "deadline" in body and "lockAfterDeadline" in body
    assert "由老師結束" in body


def test_submitted_shown_only_after_success_or_from_snapshot():
    """Scenario: US6-AS4（FR-032）：未收到成功回應前不顯示已送出。"""
    source = _source("round-submission.js")
    start, _ = _function(source, "submitAnswer")
    ok_branch = _block(source, source.index("if (result.ok", start))
    from_snapshot = _function(source, "markOwnSubmissions")
    allowed = [ok_branch, from_snapshot]
    calls = [m.start() for m in re.finditer(r"showSubmitted\(", source)]
    assert calls, "應該有顯示已送出的呼叫"
    assert all(_inside(p, allowed) for p in calls)
    texts = [m.start() for m in re.finditer("已送出", source)]
    assert all(_inside(p, allowed) for p in texts)

    shared = _source("submission.js")
    display = _function(shared, "showSubmitted")
    assert all(_inside(m.start(), [display]) for m in re.finditer("已送出", shared))


def test_network_error_is_reported_as_unconfirmed():
    """Scenario: US6-AS4：網路錯誤或逾時顯示「送出結果未確認，請重試」。"""
    source = _source("submission.js")
    start, end = _function(source, "describeSubmitError")
    body = source[start:end]
    assert "NETWORK_ERROR" in body
    assert "送出結果未確認，請重試" in body


@pytest.mark.parametrize("name", sorted(p.name for p in JS_DIR.glob("*.js")))
def test_javascript_parses(name, tmp_path):
    """每支前端模組都能被解析（PR #16 審查第 1 項：重複宣告讓整支模組不執行）。

    以 `.mjs` 副本檢查：Node 22 以後對含 `import` 的 `.js` 執行 `node --check`，
    即使有語法錯誤也可能回傳 0（模組自動偵測），所以必須明確當成 ES module。
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("找不到 node，無法檢查 JavaScript 語法")
    copy = tmp_path / (Path(name).stem + ".mjs")
    copy.write_text((JS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(copy)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_busy_state_does_not_reenable_locked_form():
    """PR #16 審查第 4 項：送出途中倒數歸零，送出結束後按鈕仍維持停用。"""
    source = _source("submission.js")
    start, end = _function(source, "setBusy")
    body = source[start:end]
    assert "button.disabled = busy;" not in body
    assert "locked" in body


def test_missing_shape_notice_is_not_duplicated():
    """PR #16 審查第 2 項：缺格數的提示每題只有一則，格數載入後移除。"""
    source = _source("round-submission.js")
    start, end = _function(source, "render")
    body = source[start:end]
    assert "notices.has(key)" in body and "notices.delete(key)" in body
