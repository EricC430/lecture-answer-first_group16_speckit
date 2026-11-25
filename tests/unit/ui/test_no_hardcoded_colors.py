"""色碼只能出現在 tokens.css（006 FR-004；contracts/design-tokens.md 規則 1）。"""

import re
from pathlib import Path

import pytest

from tests.unit.ui.tokens import STATIC_DIR

_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
_STYLE_ATTR = re.compile(r"""style\s*=\s*("[^"]*"|'[^']*')""", re.IGNORECASE)
# CSS 的 id 選擇器（#abc { 或 #abc, 或 #abc:）也符合 #[0-9a-f]{3,8}，用宣告值的位置判斷
_DECL_VALUE = re.compile(r":\s*([^;{}]+);")


def color_violations_in_css(text: str) -> list[str]:
    """回傳 CSS 宣告值中出現的色碼（不檢查選擇器）。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    found: list[str] = []
    for value in _DECL_VALUE.findall(text):
        found.extend(match.group(0) for match in _COLOR.finditer(value))
    return found


def color_violations_in_html(text: str) -> list[str]:
    """回傳 HTML style 屬性中出現的色碼。"""
    found: list[str] = []
    for attr in _STYLE_ATTR.findall(text):
        found.extend(match.group(0) for match in _COLOR.finditer(attr))
    return found


def test_negative_control_detects_hex_and_rgb() -> None:
    assert color_violations_in_css(".a { color: #fff; background: rgb(0, 0, 0); }") == [
        "#fff",
        "rgb(",
    ]
    assert color_violations_in_html('<p style="color:#123456">x</p>') == ["#123456"]


def test_positive_control_allows_variables_and_id_selectors() -> None:
    css = (
        "#abc, #def:hover { color: var(--color-text); border: 1px solid currentColor; }"
    )
    assert color_violations_in_css(css) == []


CSS_FILES = ["app.css", "projection.css"]


@pytest.mark.parametrize("name", CSS_FILES)
def test_css_uses_tokens_only(name: str) -> None:
    path = STATIC_DIR / "css" / name
    assert path.is_file(), f"缺少 {path}"
    assert color_violations_in_css(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "path", sorted(STATIC_DIR.glob("*.html")), ids=lambda p: Path(p).name
)
def test_html_style_attributes_use_tokens_only(path: Path) -> None:
    assert color_violations_in_html(path.read_text(encoding="utf-8")) == []
