# 契約：設計基準值與對比檢查

**用途**：規定 `css/tokens.css` 必須提供的基準值名稱，以及 `tests/unit/ui/test_contrast.py` 要檢查的色彩組合。數值見 [research.md](../research.md) R2；名稱與用途見 [data-model.md](../data-model.md)。

## 規則

1. 只有 `tokens.css` 可以出現色碼（`#…`、`rgb()`、`hsl()`）；`app.css`、`projection.css` 與 HTML 只能用 `var(--…)`、`transparent`、`currentColor`（FR-004）。
2. 下列每一組都必須達到門檻；新增「承載文字或介面圖形」的色彩基準值時，要同時在本表登記。

## 文字對比（≥ 4.5:1）

| 前景 | 背景 |
|---|---|
| `--color-text` | `--color-canvas`、`--color-card`、`--color-band`、`--color-surface` |
| `--color-text-muted` | `--color-canvas`、`--color-card`、`--color-band`、`--color-surface` |
| `--color-on-primary`（白） | `--color-primary`、`--color-primary-hover`、`--color-secondary`、`--color-danger` |
| `--color-outline` | `--color-canvas`、`--color-card`、`--color-surface` |
| `--color-primary` | `--color-canvas`、`--color-surface`（連結文字） |
| `--color-success` | `--color-success-bg` |
| `--color-danger` | `--color-danger-bg` |
| `--color-warning` | `--color-warning-bg` |
| `--color-neutral` | `--color-neutral-bg` |

## 介面圖形對比（≥ 3:1）

| 前景 | 背景 |
|---|---|
| `--color-border-strong` | `--color-surface`、`--color-canvas`、`--color-card` |
| `--color-focus` | `--color-canvas`、`--color-card`、`--color-surface` |
| `--color-primary`（目前階段標記、選取中的分頁底線） | `--color-canvas`、`--color-card` |

## 不列入檢查

`--color-border`、`--color-accent`、`--color-rose`：只用在裝飾線與插圖，不承載文字或資訊；若有人拿來當文字或介面元件邊界，屬於違反本契約。

## 負對照

測試必須包含一組已知不合格的色對（`#777777` on `#ffffff`，4.48:1），確認判定函式回報不合格；若負對照通過，代表測試本身壞了。
