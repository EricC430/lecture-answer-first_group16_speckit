"""老師頁只能有 004 的「確認定案」按鈕（PR #20 審查意見 1）。"""

from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "src/lecture_quiz/adapters/static"


def test_001_finalize_button_is_gone():
    """001 舊按鈕送空本文會得 400，且與 004 的按鈕重複。"""
    assert "finalize-round" not in (STATIC / "teacher.html").read_text(encoding="utf-8")
    assert "finalize-round" not in (STATIC / "js/teacher.js").read_text(
        encoding="utf-8"
    )


def test_004_provides_the_only_finalize_button():
    """定案按鈕與 `resultVersion` 本文只在 004 的老師腳本。"""
    js = (STATIC / "js/ranking-review-teacher.js").read_text(encoding="utf-8")
    assert "/rounds/current/finalize" in js and "resultVersion" in js
    others = [
        p
        for p in (STATIC / "js").glob("*.js")
        if p.name != "ranking-review-teacher.js"
        and "/rounds/current/finalize" in p.read_text(encoding="utf-8")
    ]
    assert others == []
