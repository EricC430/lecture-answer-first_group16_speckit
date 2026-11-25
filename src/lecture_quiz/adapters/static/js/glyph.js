// 006 介面：組別幾何記號與活動階段軌（只負責展示，不改任何資料與行為）。
// 每組一個形狀（圓、方、四分之一圓、半圓、環、斜角），第 7 組起換一組顏色重複；
// 記號只是輔助辨識，畫面上一律同時寫出「第 N 組」。

const SHAPES = 6;
const TONES = 2;

/** 組號對應的形狀編號（1～6）與色調（a／b）。 */
export function glyphKind(groupNumber) {
  const index = Math.max(0, Number(groupNumber) - 1);
  return {
    shape: (index % SHAPES) + 1,
    tone: Math.floor(index / SHAPES) % TONES === 0 ? "a" : "b",
  };
}

/** 建立組別記號元素（裝飾用，aria-hidden）。 */
export function glyph(groupNumber, size = "") {
  const node = document.createElement("span");
  const { shape, tone } = glyphKind(groupNumber);
  node.className = size ? `gl gl-${size}` : "gl";
  node.dataset.shape = String(shape);
  node.dataset.tone = tone;
  node.setAttribute("aria-hidden", "true");
  return node;
}

export const STAGE_ORDER = ["PREPARING", "JOINING", "ROUND_OPEN", "RESULT_PENDING", "RESULT_FINAL", "ENDED"];

/**
 * 更新頁首的階段軌：目前階段之前標為 done、目前階段標為 now。
 * 搶答中與結果階段會在多輪之間循環，軌道只表示「目前在哪一步」。
 * @param {HTMLElement|null} track 內含 `li[data-stage]` 的清單
 * @param {string|null} stage 快照的 stage；null 表示還沒有活動
 */
export function renderStageTrack(track, stage) {
  if (!track) return;
  document.body.dataset.stage = stage ?? "";
  const position = STAGE_ORDER.indexOf(stage);
  for (const item of track.querySelectorAll("li[data-stage]")) {
    const index = STAGE_ORDER.indexOf(item.dataset.stage);
    item.classList.toggle("done", position >= 0 && index < position);
    item.classList.toggle("now", item.dataset.stage === stage);
    if (item.dataset.stage === stage) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  }
  // 已取消不在主流程上：顯示在軌道最後一格
  track.classList.toggle("cancelled", stage === "CANCELLED");
}
