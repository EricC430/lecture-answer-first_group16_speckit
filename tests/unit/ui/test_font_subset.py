"""本機字型子集涵蓋畫面上的中文（006 研究 R3、FR-006）。

需要 fontTools 讀取 woff2：沒有安裝時**明確失敗**（不跳過），請安裝 `.[fonts]`。
"""

import re

import pytest

from tests.unit.ui.tokens import STATIC_DIR

FONTS_DIR = STATIC_DIR / "fonts"
SERIF = FONTS_DIR / "NotoSerifTC-600-subset.woff2"
EXPECTED_FILES = [
    "NotoSerifTC-600-subset.woff2",
    "Inter-latin.woff2",
    "IBMPlexMono-400-latin.woff2",
    "IBMPlexMono-600-latin.woff2",
    "OFL-NotoSerifTC.txt",
    "OFL-Inter.txt",
    "OFL-IBMPlexMono.txt",
]
_CJK = re.compile(r"[　-〿㐀-鿿＀-￯]")


def _cmap() -> set[int]:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:  # 明確失敗，不靜默略過
        pytest.fail('缺少 fonttools，請安裝：python -m pip install ".[fonts]"')
    font = TTFont(str(SERIF))
    return set(font.getBestCmap())


@pytest.mark.parametrize("name", EXPECTED_FILES)
def test_font_and_license_files_exist(name: str) -> None:
    assert (FONTS_DIR / name).is_file(), f"缺少 static/fonts/{name}"


def test_total_font_size_within_budget() -> None:
    total = sum(p.stat().st_size for p in FONTS_DIR.glob("*.woff2"))
    assert total <= 600 * 1024, f"字型總量 {total / 1024:.1f} KB 超過 600 KB"


def test_serif_subset_covers_all_static_cjk_text() -> None:
    cmap = _cmap()
    missing: set[str] = set()
    for path in sorted(STATIC_DIR.rglob("*")):
        if path.suffix in {".html", ".js"}:
            for char in _CJK.findall(path.read_text(encoding="utf-8")):
                if ord(char) not in cmap:
                    missing.add(char)
    assert not missing, (
        f"字型子集缺少 {len(missing)} 個字：{''.join(sorted(missing))}；"
        "請重新執行 scripts/build_font_subset.py"
    )
