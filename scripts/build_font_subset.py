r"""產生 006 介面改版用的本機字型子集（specs/006-ui-refresh/research.md R3）。

開發者手動執行；產物 commit 進 repo，執行期不需要 fonttools。

需要的來源字型（從 https://github.com/google/fonts 的 `ofl/` 下載，SIL OFL 1.1）
放在同一個目錄，以 `--source-dir` 或環境變數 `FONT_SOURCE_DIR` 指定：

- `NotoSerifTC[wght].ttf`（ofl/notoseriftc）
- `Inter[opsz,wght].ttf`（ofl/inter）
- `IBMPlexMono-Regular.ttf`、`IBMPlexMono-SemiBold.ttf`（ofl/ibmplexmono）
- `OFL-NotoSerifTC.txt`、`OFL-Inter.txt`、`OFL-IBMPlexMono.txt`
  （各字型目錄的 `OFL.txt`，改名）

用法：
    .venv\Scripts\python -m pip install ".[fonts]"
    .venv\Scripts\python scripts/build_font_subset.py --source-dir <下載目錄>
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger("build_font_subset")

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "src" / "lecture_quiz" / "adapters" / "static"
DEFAULT_OUT_DIR = STATIC_DIR / "fonts"

SOURCES = {
    "serif": "NotoSerifTC[wght].ttf",
    "inter": "Inter[opsz,wght].ttf",
    "mono_regular": "IBMPlexMono-Regular.ttf",
    "mono_semibold": "IBMPlexMono-SemiBold.ttf",
}
LICENSES = ("OFL-NotoSerifTC.txt", "OFL-Inter.txt", "OFL-IBMPlexMono.txt")

# Latin 子集：基本拉丁、Latin-1 補充、常用標點與符號。
LATIN_RANGES = [
    (0x0020, 0x007E),
    (0x00A0, 0x00FF),
    (0x2010, 0x2027),
    (0x2030, 0x203A),
    (0x20AC, 0x20AC),
    (0x2122, 0x2122),
    (0x2190, 0x2193),
    (0x2212, 0x2212),
]


def latin_codepoints() -> set[int]:
    """Latin 子集的碼位。

    Returns:
        碼位集合。
    """
    points: set[int] = set()
    for start, end in LATIN_RANGES:
        points.update(range(start, end + 1))
    return points


def collect_static_text_codepoints(static_dir: Path) -> set[int]:
    """收集 static/ 下所有 HTML 與 JS 中出現的非 ASCII 字元（中文、全形標點等）。

    Args:
        static_dir: 靜態檔目錄。

    Returns:
        碼位集合（不含控制字元）。
    """
    points: set[int] = set()
    for path in sorted(static_dir.rglob("*")):
        if path.suffix not in {".html", ".js"}:
            continue
        for char in path.read_text(encoding="utf-8"):
            code = ord(char)
            if code > 0x7E and char.isprintable():
                points.add(code)
    return points


def _require_sources(source_dir: Path) -> dict[str, Path]:
    names = [*SOURCES.values(), *LICENSES]
    missing = [name for name in names if not (source_dir / name).is_file()]
    if missing:
        raise SystemExit(
            f"來源目錄 {source_dir} 缺少字型檔：{', '.join(missing)}。"
            "請從 https://github.com/google/fonts 的 ofl/notoseriftc、ofl/inter、"
            "ofl/ibmplexmono 下載（見本檔開頭說明）。"
        )
    return {key: source_dir / name for key, name in SOURCES.items()}


def _subset(font: object, codepoints: set[int], out_path: Path) -> None:
    from fontTools import subset  # noqa: PLC0415  只在執行本腳本時需要

    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=sorted(codepoints))
    subsetter.subset(font)
    font.flavor = "woff2"  # type: ignore[attr-defined]
    font.save(str(out_path))  # type: ignore[attr-defined]
    logger.info(
        "%s：%d 字元，%.1f KB",
        out_path.name,
        len(codepoints),
        out_path.stat().st_size / 1024,
    )


def build(source_dir: Path, out_dir: Path) -> None:
    """產生四個 woff2 子集並複製三份授權檔。

    Args:
        source_dir: 來源 TTF 所在目錄。
        out_dir: 輸出目錄（通常是 static/fonts/）。
    """
    try:
        from fontTools.ttLib import TTFont  # noqa: PLC0415
        from fontTools.varLib import instancer  # noqa: PLC0415
    except ImportError as exc:
        raise SystemExit(
            '缺少 fonttools，請先安裝：python -m pip install ".[fonts]"'
        ) from exc

    sources = _require_sources(source_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    latin = latin_codepoints()
    cjk = collect_static_text_codepoints(STATIC_DIR)
    logger.info("static/ 中收集到 %d 個非 ASCII 字元", len(cjk))

    serif = instancer.instantiateVariableFont(
        TTFont(str(sources["serif"])), {"wght": 600}
    )
    _subset(serif, latin | cjk, out_dir / "NotoSerifTC-600-subset.woff2")

    _subset(TTFont(str(sources["inter"])), latin, out_dir / "Inter-latin.woff2")
    _subset(
        TTFont(str(sources["mono_regular"])),
        latin,
        out_dir / "IBMPlexMono-400-latin.woff2",
    )
    _subset(
        TTFont(str(sources["mono_semibold"])),
        latin,
        out_dir / "IBMPlexMono-600-latin.woff2",
    )

    for name in LICENSES:
        shutil.copyfile(source_dir / name, out_dir / name)
    total = sum(p.stat().st_size for p in out_dir.glob("*.woff2"))
    logger.info("字型總量 %.1f KB", total / 1024)


def main(argv: list[str] | None = None) -> int:
    """命令列入口。

    Args:
        argv: 命令列參數（測試用）。

    Returns:
        結束碼。
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default=os.environ.get("FONT_SOURCE_DIR"))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)
    if not args.source_dir:
        raise SystemExit(
            "請以 --source-dir 或環境變數 FONT_SOURCE_DIR 指定來源字型目錄。"
        )
    build(Path(args.source_dir), Path(args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
