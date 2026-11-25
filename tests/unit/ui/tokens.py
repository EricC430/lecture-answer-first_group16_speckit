"""006 介面測試共用：讀取 tokens.css 的色彩基準值與 WCAG 2.1 對比計算。"""

import re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parents[3] / "src/lecture_quiz/adapters/static"
TOKENS_CSS = STATIC_DIR / "css" / "tokens.css"

_DECL = re.compile(r"(--color-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;")


def read_color_tokens(path: Path = TOKENS_CSS) -> dict[str, str]:
    """回傳 `:root` 中以六位十六進位定義的 `--color-*`（第一次出現者為準）。"""
    tokens: dict[str, str] = {}
    for name, value in _DECL.findall(path.read_text(encoding="utf-8")):
        tokens.setdefault(name, value.lower())
    return tokens


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 相對亮度。"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.1 對比值（1～21）。"""
    a, b = sorted(
        (relative_luminance(foreground), relative_luminance(background)), reverse=True
    )
    return (a + 0.05) / (b + 0.05)
