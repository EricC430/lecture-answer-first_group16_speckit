"""學生頁（004 的 ranking-review.js）實際畫出的內容（spec US7-AS9；issue #22 第 1 點）。

前端沒有 JavaScript 測試環境，所以這裡用 node 載入**真正的** `ranking-review.js`（與
`ranking-common.js`、`submission.js`），以最小的假 DOM 執行 `render`，餵入後端產生的學生
快照（真實 JSON 形狀），再檢查畫面上每一題的標題與內容。只有 `student.js` 用替身取代
（它一載入就連 WebSocket）。沒有 node 時明確失敗，不跳過。

曾經發生：`render` 只在「本組有提交或有搶答成功者」時才畫出題目，所以某題沒人提交、或
唯一的提交被判錯時，沒有提交的組在學生頁上完全看不到那一題（應顯示「未成功」）。後端的
資料與測試都對，只有畫面少了，所以沒有任何測試發現。
"""

import json
import shutil
import subprocess
from pathlib import Path

from tests.integration.ranking_world import (
    answer,
    close_round,
    open_ranking_round,
    snapshot,
)

JS_DIR = Path(__file__).resolve().parents[3] / "src/lecture_quiz/adapters/static/js"

STUDENT_STUB = """\
export function onStudentSnapshot(fn) {
  globalThis.__render = fn;
}
export function onStudentReset() {}
"""

DRIVER = """\
import fs from "node:fs";

const snapshot = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

class Node {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.className = "";
    this.hidden = false;
    this.dataset = {};
  }
  setAttribute() {}
  append(...nodes) {
    this.children.push(...nodes);
  }
  replaceChildren(...nodes) {
    this.children = [...nodes];
  }
}

const section = new Node("section");
const list = new Node("div");
const byId = {
  "ranking-review-student-section": section,
  "ranking-review-student-list": list,
};
globalThis.document = {
  createElement: (tag) => new Node(tag),
  getElementById: (id) => byId[id],
};

await import("./ranking-review.js");
globalThis.__render(snapshot);

const dump = (n) => ({
  tag: n.tag,
  className: n.className,
  text: n.textContent,
  children: n.children.map(dump),
});
console.log(JSON.stringify({ hidden: section.hidden, list: dump(list) }));
"""


def render_student_page(tmp_path: Path, student_snapshot: dict) -> dict:
    """用 node 執行真正的 ranking-review.js，回傳假 DOM 的內容。"""
    node = shutil.which("node")
    assert node is not None, "找不到 node，無法執行前端行為測試"
    (tmp_path / "package.json").write_text('{"type": "module"}', encoding="utf-8")
    for name in ("ranking-review.js", "ranking-common.js", "submission.js", "glyph.js"):
        shutil.copy(JS_DIR / name, tmp_path / name)
    (tmp_path / "student.js").write_text(STUDENT_STUB, encoding="utf-8")
    (tmp_path / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    data = tmp_path / "snapshot.json"
    data.write_text(json.dumps(student_snapshot), encoding="utf-8")
    result = subprocess.run(
        [node, str(tmp_path / "driver.mjs"), str(data)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _text(node: dict) -> str:
    return node["text"] + "".join(_text(child) for child in node["children"])


def questions_of(page: dict) -> dict[str, list[str]]:
    """最新一輪每一題：標題 → 該題顯示的各行文字。"""
    rounds = page["list"]["children"]
    assert rounds, "學生頁沒有任何輪次"
    blocks = [c for c in rounds[0]["children"] if c["className"] == "ranking-question"]
    out: dict[str, list[str]] = {}
    for block in blocks:
        # 判錯後受影響的題目標題會多「（結果已更新）」，這裡只比題號
        title = _text(block["children"][0]).replace("（結果已更新）", "")
        lines = [_text(li) for ul in block["children"][1:] for li in ul["children"]]
        out[title] = lines
    return out


def test_questions_without_a_winner_are_still_shown_as_unsolved(client, tmp_path):
    """Scenario: US7-AS9：沒人提交的題，沒有提交的組也要看到「未成功」。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2, 3), questions=3)
    answer(client, teacher, devices, 1, 1)  # 只有第 1 題有人提交
    answer(client, teacher, devices, 2, 2)  # 第 2 題只有第 2 組提交
    close_round(client, teacher)
    page = render_student_page(
        tmp_path, snapshot(client, teacher.code, devices[3])
    )  # 第 3 組什麼都沒提交
    shown = questions_of(page)
    assert set(shown) == {"第 1 題", "第 2 題", "第 3 題"}, shown
    assert shown["第 3 題"] == ["未成功"]
    assert any("目前搶答成功者：第 1 組" in line for line in shown["第 1 題"])


def test_question_whose_only_submission_was_judged_wrong_is_shown(client, tmp_path):
    """Scenario: US7-AS9：唯一的提交被判錯 → 沒提交的組看到「未成功」，不洩漏他組。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2, 3), questions=3)
    answer(client, teacher, devices, 1, 1)
    answer(client, teacher, devices, 2, 2)
    close_round(client, teacher)
    judged = client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/2/groups/2/judgement",
        json={"wrong": True},
        headers=teacher.headers,
    )
    assert judged.status_code == 200, judged.text
    page = render_student_page(tmp_path, snapshot(client, teacher.code, devices[3]))
    shown = questions_of(page)
    assert "第 2 題" in shown, shown
    assert shown["第 2 題"] == ["未成功"], (
        "沒有遞補者時不顯示他組，也不顯示剛被判錯的前一組"
    )


def test_own_wrong_submission_is_shown_to_that_group(client, tmp_path):
    """Scenario: US7-AS9：本組的提交被判錯，本組看到自己的「答錯」。"""
    teacher, devices = open_ranking_round(client, groups=(1, 2, 3), questions=3)
    answer(client, teacher, devices, 2, 2)
    close_round(client, teacher)
    client.put(
        f"/api/activities/{teacher.code}/rounds/1/questions/2/groups/2/judgement",
        json={"wrong": True},
        headers=teacher.headers,
    )
    shown = questions_of(
        render_student_page(tmp_path, snapshot(client, teacher.code, devices[2]))
    )
    assert any("本組" in line and "答錯" in line for line in shown["第 2 題"]), shown
    assert "未成功" in shown["第 2 題"]
