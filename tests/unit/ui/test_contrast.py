"""設計基準值的對比檢查（006 FR-025、SC-003；contracts/design-tokens.md）。"""

import pytest

from tests.unit.ui.tokens import contrast_ratio, read_color_tokens

SURFACES = ["--color-canvas", "--color-card", "--color-band", "--color-surface"]

# contracts/design-tokens.md「文字對比（≥ 4.5:1）」
TEXT_PAIRS = (
    [("--color-text", bg) for bg in SURFACES]
    + [("--color-text-muted", bg) for bg in SURFACES]
    + [
        ("--color-on-primary", bg)
        for bg in (
            "--color-primary",
            "--color-primary-hover",
            "--color-secondary",
            "--color-danger",
        )
    ]
    + [
        ("--color-outline", bg)
        for bg in ("--color-canvas", "--color-card", "--color-surface")
    ]
    + [("--color-primary", bg) for bg in ("--color-canvas", "--color-surface")]
    + [
        ("--color-success", "--color-success-bg"),
        ("--color-danger", "--color-danger-bg"),
        ("--color-warning", "--color-warning-bg"),
        ("--color-neutral", "--color-neutral-bg"),
    ]
)

# contracts/design-tokens.md「介面圖形對比（≥ 3:1）」
GRAPHIC_PAIRS = (
    [
        ("--color-border-strong", bg)
        for bg in ("--color-surface", "--color-canvas", "--color-card")
    ]
    + [
        ("--color-focus", bg)
        for bg in ("--color-canvas", "--color-card", "--color-surface")
    ]
    + [("--color-primary", bg) for bg in ("--color-canvas", "--color-card")]
)


@pytest.fixture(scope="module")
def tokens() -> dict[str, str]:
    return read_color_tokens()


def test_negative_control_is_rejected() -> None:
    """負對照：#777777 on #ffffff 為 4.48:1，必須判為不合格（否則判定本身壞了）。"""
    ratio = contrast_ratio("#777777", "#ffffff")
    assert 4.47 < ratio < 4.49
    assert not ratio >= 4.5


def test_positive_control_is_accepted() -> None:
    """正對照：黑字白底為 21:1。"""
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)


@pytest.mark.parametrize(("fg", "bg"), TEXT_PAIRS)
def test_text_pairs_meet_aa(tokens: dict[str, str], fg: str, bg: str) -> None:
    assert fg in tokens, f"tokens.css 缺少 {fg}"
    assert bg in tokens, f"tokens.css 缺少 {bg}"
    ratio = contrast_ratio(tokens[fg], tokens[bg])
    assert ratio >= 4.5, f"{fg} on {bg} = {ratio:.2f}:1，未達 4.5:1"


@pytest.mark.parametrize(("fg", "bg"), GRAPHIC_PAIRS)
def test_graphic_pairs_meet_aa(tokens: dict[str, str], fg: str, bg: str) -> None:
    assert fg in tokens, f"tokens.css 缺少 {fg}"
    assert bg in tokens, f"tokens.css 缺少 {bg}"
    ratio = contrast_ratio(tokens[fg], tokens[bg])
    assert ratio >= 3.0, f"{fg} on {bg} = {ratio:.2f}:1，未達 3:1"
