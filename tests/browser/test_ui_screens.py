"""006 截圖（quickstart B；SC-002、SC-005）。

預設把截圖寫到 pytest 的暫存目錄（只確認每個畫面都能渲染、無整頁水平捲動）；
要更新 repo 內的截圖時設定環境變數 UI_SCREENSHOTS_DIR
（例如 specs/006-ui-refresh/screenshots），
再由人實際打開每一張檢查。
"""

import os
import time
from pathlib import Path

import pytest

from tests.browser.ui_helpers import (
    open_projection,
    open_student,
    open_teacher,
    wait_stage,
)

WIDTHS = [(375, 812), (768, 1024), (1024, 768), (1440, 900)]
PROJECTION = [(1280, 720), (1920, 1080)]


def _out(tmp_path: Path) -> Path:
    target = os.environ.get("UI_SCREENSHOTS_DIR")
    out = Path(target) if target else tmp_path
    out.mkdir(parents=True, exist_ok=True)
    return out


def _shot(page, out: Path, name: str) -> None:
    page.eval("document.fonts.ready.then(()=>new Promise(r=>setTimeout(r,250)))")
    assert page.eval(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    ), name
    started = time.time()
    page.screenshot(str(out / f"{name}.png"))
    print(f"{name} {time.time() - started:.2f}s", flush=True)


@pytest.mark.timeout(240)  # 40 多張截圖，超過預設 30 秒
def test_capture_screenshots(page, world, tmp_path):
    out = _out(tmp_path)
    for width, height in WIDTHS:
        page.set_viewport(width, height)
        page.goto(f"{world.server.base}/index.html")
        _shot(page, out, f"index-{width}")

    world.create()
    world.join(1, 2)
    student = page.browser.new_page()
    proj = page.browser.new_page()
    stages = [
        ("joining", "開放加入", None),
        (
            "round",
            "搶答中",
            lambda: (world.open_round([3, 4]), world.submit(1, 3, 2, ["第二組答案"])),
        ),
        (
            "results",
            "結果未定案",
            lambda: (
                world.submit(1, 3, 1, ["第一組答案"]),
                world.close_round(),
                world.judge(1, 3, 2, True),
            ),
        ),
        ("ended", "已結束", lambda: (world.finalize(), world.api("POST", "/end"))),
    ]
    for name, label, action in stages:
        if action:
            action()
        for width, height in WIDTHS:
            page.set_viewport(width, height)
            open_teacher(page, world)
            wait_stage(page, "activity-stage", label)
            _shot(page, out, f"teacher-{name}-{width}")
            student.set_viewport(width, height)
            open_student(student, world, 1)
            wait_stage(student, "student-stage", label)
            _shot(student, out, f"student-{name}-{width}")
        for width, height in PROJECTION:
            proj.set_viewport(width, height)
            open_projection(proj, world)
            proj.wait_for(
                "document.getElementById('projection-stage').textContent.length > 0"
            )
            _shot(proj, out, f"projection-{name}-{width}x{height}")
    assert len(list(out.glob("*.png"))) == len(WIDTHS) * (1 + 2 * len(stages)) + len(
        PROJECTION
    ) * len(stages)
