# 插圖來源紀錄（006 FR-023、FR-024；research.md R9）

## 清單

| id | 檔案 | 用途 | 替代文字 | 來源 | 狀態 |
|---|---|---|---|---|---|
| `empty-groups` | `static/img/illustrations.svg#empty-groups` | 老師頁「尚未有組別加入」 | 裝飾（`aria-hidden`），旁有說明文字 | Claude 手寫 SVG，2026-11-25 | 已完成 |
| `empty-import` | `static/img/illustrations.svg#empty-import` | 老師頁「還沒有匯入學習單」 | 裝飾 | Claude 手寫 SVG，2026-11-25 | 已完成 |
| `empty-round` | `static/img/illustrations.svg#empty-round` | 學生頁「等老師開始搶答」 | 裝飾 | Claude 手寫 SVG，2026-11-25 | 已完成 |
| `empty-results` | `static/img/illustrations.svg#empty-results` | 老師頁右欄「建立活動後……」 | 裝飾 | Claude 手寫 SVG，2026-11-25 | 已完成 |
| `hero-placeholder` | `static/img/illustrations.svg#hero-placeholder` | 首頁主插圖的暫代圖 | 「幾組學生圍著桌子舉手搶答，旁邊有一個大計時器」 | Claude 手寫 SVG，2026-11-25 | 使用中，待 `hero` 取代 |
| `hero` | `static/img/hero.webp` | 首頁主插圖 | 同上 | 組員以 AI 生成（下方提示詞） | **待組員生成（tasks T082）** |

手寫 SVG 只用 `currentColor` 與 `tokens.css` 的插圖填色變數，檔內沒有色碼；不臨摹、不使用參考範本（User Interviews）原品牌的插圖。

## 首頁主插圖：交給組員的提示詞（tasks T081）

**規格**：1600×1000 px（16:10），交回 PNG 或 WebP 原檔即可，Claude 會轉成 `hero.webp`（≤ 300KB）。背景用純色或透明；不要文字、不要 logo、不要浮水印。

**提示詞（英文，給 ChatGPT／Gemini／Midjourney 等）**：

```
Hand-drawn editorial line illustration in a "research field notes" style: single-weight
dark ink outlines (#283338), minimal flat color fills in deep teal (#1c5d5f), soft sage
green (#65b8a2) and dusty rose (#d6aec1), on a warm off-white paper background (#f2e8e2).
Scene: a university classroom; three small groups of students sit around round tables,
several students eagerly raising their hands to answer a quiz question; a large friendly
countdown timer floats in the upper right; a teacher stands at the side next to a big
worksheet / spreadsheet on a board with blank answer boxes. Friendly, calm, inclusive,
diverse students, simple rounded shapes, generous white space, flat 2D, no gradients,
no shadows, no text, no letters, no numbers, no logos, no brand references.
Wide composition 16:10, subjects centered, clean edges so it can sit inside a rounded card.
```

**中文說明（給組員自己確認用）**：手繪單線條、深色輪廓，平塗只用深青、鼠尾草綠、灰粉三色，暖白紙底；場景是大學教室，三組學生圍圓桌舉手搶答，右上一個大計時器，旁邊老師站在貼著學習單的白板邊；畫面不要有任何文字、數字或品牌。

## 組員交付後要記錄（tasks T082）

| 項目 | 內容 |
|---|---|
| 生成工具與版本 | （待填） |
| 實際使用的提示詞 | （待填；若有修改，貼上最終版本） |
| 生成日期 | （待填） |
| 服務條款確認 | （待填：該服務是否允許產出用於課堂專題與 Demo 影片；附條款連結） |
| 交付檔名與大小 | （待填，T083 轉檔後由 Claude 補上） |
