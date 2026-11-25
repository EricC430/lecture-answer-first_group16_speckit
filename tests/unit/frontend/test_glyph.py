"""006 組別幾何記號與階段軌（`js/glyph.js`）的實際行為。

對應 spec US2、US1-AS5。

前端沒有 JavaScript 測試環境，所以用 node 載入**真正的** `glyph.js`，
以最小的假 DOM 執行，再檢查結果。沒有 node 時明確失敗，不跳過。
"""

import json
import shutil
import subprocess
from pathlib import Path

JS_DIR = Path(__file__).resolve().parents[3] / "src/lecture_quiz/adapters/static/js"

DRIVER = """\
class Node {
  constructor(tag) {
    this.tag = tag;
    this.className = "";
    this.textContent = "";
    this.dataset = {};
    this.attributes = {};
    this.classes = new Set();
    this.classList = {
      toggle: (name, on) =>
        on ? this.classes.add(name) : this.classes.delete(name),
    };
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  removeAttribute(name) {
    delete this.attributes[name];
  }
}
const stages = ["PREPARING", "JOINING", "ROUND_OPEN",
  "RESULT_PENDING", "RESULT_FINAL", "ENDED"];
const items = stages.map(
  (stage) => Object.assign(new Node("li"), { dataset: { stage } }));
const track = Object.assign(new Node("ol"), { querySelectorAll: () => items });
globalThis.document = {
  createElement: (tag) => new Node(tag),
  body: { dataset: {} },
};

const { glyph, glyphKind, renderStageTrack } = await import("./glyph.js");
const kinds = [1, 2, 6, 7, 12, 13, 99].map((n) => [n, glyphKind(n)]);
const mark = glyph(7, "sm");
renderStageTrack(track, "RESULT_PENDING");
const pending = items.map((i) => ({
  stage: i.dataset.stage,
  classes: [...i.classes].sort(),
  current: i.attributes["aria-current"] ?? null,
}));
renderStageTrack(track, null);
const cleared = items.every(
  (i) => i.classes.size === 0 && !i.attributes["aria-current"]);
console.log(JSON.stringify({
  kinds,
  mark: {
    className: mark.className,
    dataset: mark.dataset,
    attributes: mark.attributes,
    text: mark.textContent,
  },
  pending,
  cleared,
}));
"""


def run_glyph(tmp_path: Path) -> dict:
    """用 node 執行真正的 glyph.js，回傳結果。"""
    node = shutil.which("node")
    assert node is not None, "找不到 node，無法執行前端行為測試"
    (tmp_path / "package.json").write_text('{"type": "module"}', encoding="utf-8")
    shutil.copy(JS_DIR / "glyph.js", tmp_path / "glyph.js")
    (tmp_path / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        [node, str(tmp_path / "driver.mjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_each_group_number_maps_to_a_fixed_shape_and_tone(tmp_path):
    """第 1～6 組各一種形狀，第 7 組起換顏色重複，第 13 組回到第一組顏色。

    Scenario: US2-AS3
    """
    kinds = {n: kind for n, kind in run_glyph(tmp_path)["kinds"]}
    assert kinds[1] == {"shape": 1, "tone": "a"}
    assert kinds[2] == {"shape": 2, "tone": "a"}
    assert kinds[6] == {"shape": 6, "tone": "a"}
    assert kinds[7] == {"shape": 1, "tone": "b"}
    assert kinds[12] == {"shape": 6, "tone": "b"}
    assert kinds[13] == {"shape": 1, "tone": "a"}
    assert kinds[99] == {
        "shape": 3,
        "tone": "a",
    }  # (99 - 1) % 6 + 1 = 3；98 // 6 = 16 為偶數


def test_glyph_is_decorative_and_carries_no_text(tmp_path):
    """記號是裝飾（aria-hidden）且不帶文字，組號由旁邊的「第 N 組」表達。

    Scenario: US2-AS2
    """
    mark = run_glyph(tmp_path)["mark"]
    assert mark["text"] == ""
    assert mark["attributes"] == {"aria-hidden": "true"}
    assert mark["className"] == "gl gl-sm"
    assert mark["dataset"] == {"shape": "1", "tone": "b"}


def test_stage_track_marks_done_and_current_step(tmp_path):
    """階段軌把目前階段標為 now（aria-current）、之前的標為 done；無活動時清除。

    Scenario: US1-AS5
    """
    result = run_glyph(tmp_path)
    by_stage = {item["stage"]: item for item in result["pending"]}
    for stage in ("PREPARING", "JOINING", "ROUND_OPEN"):
        assert by_stage[stage]["classes"] == ["done"], by_stage[stage]
    assert by_stage["RESULT_PENDING"] == {
        "stage": "RESULT_PENDING",
        "classes": ["now"],
        "current": "step",
    }
    for stage in ("RESULT_FINAL", "ENDED"):
        assert by_stage[stage]["classes"] == [], by_stage[stage]
    assert result["cleared"] is True
