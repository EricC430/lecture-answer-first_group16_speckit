// 006 新資料提示（spec US3-AS3、FR-020；research.md R7）。
// 監看作答看板、已公開作答、順位清單與投影結果區；新出現的列短暫加上 .is-new（樣式在 app.css），
// 不呼叫 focus()，不影響任何資料流程。減少動態效果時 CSS 改為靜態外框（FR-016）。
// 子功能常常整塊重畫，所以用「列的文字內容」判斷是否看過：重畫出一模一樣的列不算新資料。

const WATCHED = ["submission-board", "published-list", "ranking-review-list", "projection-results"];
const ROW = "tr, li, .projection-entry";
const HIGHLIGHT_MS = 1500;
const SETTLE_MS = 1500; // 頁面剛載入時畫出的內容不算新資料

const started = Date.now();

function rowsIn(node) {
  return node.matches(ROW) ? [node] : [...node.querySelectorAll(ROW)];
}

function watch(container) {
  const known = new Set();
  const remember = () => {
    for (const row of container.querySelectorAll(ROW)) known.add(row.textContent);
  };
  remember();
  new MutationObserver((records) => {
    const settled = Date.now() - started >= SETTLE_MS;
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        for (const row of rowsIn(node)) {
          if (!settled || known.has(row.textContent)) continue;
          row.classList.add("is-new");
          setTimeout(() => row.classList.remove("is-new"), HIGHLIGHT_MS);
        }
      }
    }
    remember();
  }).observe(container, { childList: true, subtree: true });
}

for (const id of WATCHED) {
  const container = document.getElementById(id);
  if (container) watch(container);
}
