"""006 設計基準值（spec US4-AS1、US4-AS2；Issue #28 驗收條件）。

1. 色碼只定義在 `app.css` 的 `:root`，其餘樣式與頁面一律引用 CSS 變數。
2. 畫面上實際使用的文字／背景配對，對比度都達 WCAG AA（4.5:1）。
   配對清單對應 app.css 中的使用位置；新增配色時要一起加進來。
"""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[2] / "src/lecture_quiz/adapters/static"
CSS = (STATIC / "css/app.css").read_text(encoding="utf-8")
HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")


def _root_block() -> str:
    start = CSS.index(":root")
    return CSS[start : CSS.index("}", start)]


def _tokens() -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", _root_block()))


def _without_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def test_colors_are_defined_only_in_root():
    """Scenario: US4-AS1 — `:root` 以外的樣式沒有寫死的色碼。"""
    body = _without_comments(CSS.replace(_root_block(), ""))
    # 去掉選擇器裡的 id（例如 #cancel-activity），只檢查宣告值
    values = re.findall(r":\s*([^;{}]+);", body)
    leaked = [v for v in values if HEX.search(v)]
    assert leaked == [], leaked


@pytest.mark.parametrize("page", ["index.html", "teacher.html", "student.html"])
def test_pages_have_no_inline_colors(page):
    """Scenario: US4-AS1 — 頁面沒有 style 屬性或內嵌色碼。"""
    html = re.sub(
        r"<!--.*?-->", "", (STATIC / page).read_text(encoding="utf-8"), flags=re.DOTALL
    )
    assert "style=" not in html
    assert not HEX.search(re.sub(r'href="[^"]*"', "", html))


def _luminance(color: str) -> float:
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    """WCAG 2.x 對比度。"""
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# (文字, 背景, 使用位置)
PAIRS = [
    ("ink", "bg", "內文"),
    ("grey", "bg", "次要文字、標籤、階段軌"),
    ("grey", "wash", "未出題方塊"),
    ("red-ink", "bg", "搶答成功、判錯按鈕、未成功方塊、倒數文字"),
    ("red-ink", "danger-bg", "錯誤訊息"),
    ("on-color", "red", "主要按鈕、結果未定案色塊（含 13px 說明）"),
    ("on-color", "red-ink", "主要按鈕 hover"),
    ("on-color", "blue", "成功題數色塊"),
    ("on-color", "ink", "輪次色塊、作答中方塊、同步狀態列"),
    ("ink", "yellow", "搶答中色塊、待定案方塊、同步中斷橫幅、本輪題目列"),
    ("ink", "wash", "總覽題目方塊、圓環倒數"),
]


@pytest.mark.parametrize(("text", "background", "usage"), PAIRS)
def test_text_contrast_meets_wcag_aa(text, background, usage):
    """Scenario: US4-AS2 — 文字與背景對比度至少 4.5:1。"""
    tokens = _tokens()
    ratio = contrast(tokens[text], tokens[background])
    assert ratio >= 4.5, f"{usage}：--{text} on --{background} = {ratio:.2f}:1"


def test_contrast_check_catches_a_failing_pair():
    """負對照：淺灰字在白底（#9e9e9e on #ffffff）要被判為不及格，確認檢查本身有效。"""
    assert contrast("#9e9e9e", "#ffffff") < 4.5
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
