// 006 老師頁版面：右欄分頁、依階段自動切換、「有更新」標記、左欄階段進度、開啟投影畫面
// （spec US3；FR-017～FR-018、FR-030；research.md R4；data-model.md「老師頁分頁」）。
// 只「跟隨」既有子功能腳本的結果：區塊是否顯示仍由各子功能決定，這裡只依區塊的 hidden
// 決定分頁標籤是否出現，不新增任何顯示規則或操作。

import { onTeacherReset, onTeacherSnapshot, STAGE_LABELS } from "./teacher.js";

const $ = (id) => document.getElementById(id);

const TABS = ["tab-import", "tab-board", "tab-ranking", "tab-export"];
const TAB_FOR_STAGE = {
  PREPARING: "tab-import",
  JOINING: "tab-import",
  ROUND_OPEN: "tab-board",
  RESULT_PENDING: "tab-ranking",
  RESULT_FINAL: "tab-ranking",
  ENDED: "tab-export",
};
const PROGRESS = ["PREPARING", "JOINING", "ROUND_OPEN", "RESULT_PENDING", "RESULT_FINAL", "ENDED"];

const ui = {
  selected: null,
  lastStage: null,
  code: null,
  quietUntil: 0, // 剛載入或換活動後的短暫期間，不把各子功能的補畫算成「有更新」
};

function tab(id) {
  return $(id);
}

/** 只在值不同時才設定 hidden（相同值也會產生 MutationRecord，會讓觀察者無限循環）。 */
function setHidden(element, value) {
  if (element.hidden !== value) element.hidden = value;
}

function panelOf(tabId) {
  return $(tab(tabId).getAttribute("aria-controls"));
}

function tabVisible(tabId) {
  const panel = panelOf(tabId);
  return [...panel.querySelectorAll("section[data-feature]")].some((s) => !s.hidden);
}

function setBadge(tabId, on) {
  const element = tab(tabId);
  const badge = element.querySelector(".tab-badge");
  if (on && !badge) {
    const span = document.createElement("span");
    span.className = "tab-badge";
    span.textContent = "有更新";
    element.append(span);
  } else if (!on && badge) {
    badge.remove();
  }
}

function select(tabId, { focus = false } = {}) {
  ui.selected = tabId;
  for (const id of TABS) {
    const on = id === tabId;
    const element = tab(id);
    if (element.getAttribute("aria-selected") !== String(on)) element.setAttribute("aria-selected", String(on));
    element.tabIndex = on ? 0 : -1;
    setHidden(panelOf(id), !on);
  }
  if (tabId && ui.selected === tabId) {
    setBadge(tabId, false);
    if (focus) tab(tabId).focus();
  }
}

function firstVisible() {
  return TABS.find((id) => !tab(id).hidden) ?? null;
}

/** 依各面板內區塊的 hidden 更新分頁標籤是否顯示（FR-017d）。 */
function syncVisibility() {
  let any = false;
  for (const id of TABS) {
    const visible = tabVisible(id);
    setHidden(tab(id), !visible);
    if (!visible) setBadge(id, false);
    any = any || visible;
  }
  setHidden($("teacher-tabs"), !any);
  setHidden($("workspace-empty"), any);
  if (!any) {
    for (const id of TABS) setHidden(panelOf(id), true);
    ui.selected = null;
    return;
  }
  if (!ui.selected || tab(ui.selected).hidden) select(firstVisible());
}

function renderProgress(stage) {
  const list = $("stage-progress");
  const steps = stage === "CANCELLED" ? [...PROGRESS.slice(0, 2), "CANCELLED"] : PROGRESS;
  const items = steps.map((key) => {
    const item = document.createElement("li");
    item.textContent = STAGE_LABELS[key];
    item.dataset.stage = key;
    if (key === stage) item.setAttribute("aria-current", "step");
    return item;
  });
  list.replaceChildren(...items);
  list.hidden = false;
}

function onSnapshot(snapshot, state) {
  // 剛載入或換活動時，各子功能會非同步補畫內容（例如匯入結果）：這段時間不算「有更新」
  if (ui.code !== state.code) ui.quietUntil = Date.now() + 1500;
  ui.code = state.code;
  document.body.dataset.stage = snapshot.stage;
  renderProgress(snapshot.stage);
  $("open-projection").hidden = !state.code;
  syncVisibility();
  if (snapshot.stage !== ui.lastStage) {
    ui.lastStage = snapshot.stage;
    const target = TAB_FOR_STAGE[snapshot.stage];
    if (target) {
      // 各子功能可能在同一個快照稍後才顯示區塊：等這一輪渲染完成再切換
      queueMicrotask(() => {
        syncVisibility();
        select(!tab(target).hidden ? target : firstVisible());
      });
    }
  }
}

function onReset() {
  ui.lastStage = null;
  ui.selected = null;
  delete document.body.dataset.stage;
  $("stage-progress").hidden = true;
  $("open-projection").hidden = true;
  for (const id of TABS) setBadge(id, false);
  syncVisibility();
}

function onKeydown(event) {
  const visible = TABS.filter((id) => !tab(id).hidden);
  const index = visible.indexOf(document.activeElement?.id);
  if (index < 0) return;
  let next = null;
  if (event.key === "ArrowRight") next = visible[(index + 1) % visible.length];
  else if (event.key === "ArrowLeft") next = visible[(index - 1 + visible.length) % visible.length];
  else if (event.key === "Home") next = visible[0];
  else if (event.key === "End") next = visible[visible.length - 1];
  else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    select(document.activeElement.id);
    return;
  }
  if (next) {
    event.preventDefault();
    for (const id of visible) tab(id).tabIndex = id === next ? 0 : -1;
    tab(next).focus();
  }
}

function start() {
  for (const id of TABS) {
    tab(id).addEventListener("click", () => select(id));
    // 區塊 hidden 改變 → 分頁標籤跟著改變
    new MutationObserver((records) => {
      // 只關心面板內各子功能區塊的 hidden；面板本身的 hidden 是這裡設定的
      if (records.some((r) => r.target !== panelOf(id))) syncVisibility();
    }).observe(panelOf(id), {
      subtree: true,
      attributes: true,
      attributeFilter: ["hidden"],
    });
    // 背景分頁的內容變動 → 「有更新」（FR-017c）
    new MutationObserver((records) => {
      if (id === ui.selected || tab(id).hidden || Date.now() < ui.quietUntil) return;
      const real = records.some((r) => r.type !== "attributes" || r.attributeName !== "hidden");
      if (real) setBadge(id, true);
    }).observe(panelOf(id), { subtree: true, childList: true, characterData: true });
  }
  $("teacher-tabs").addEventListener("keydown", onKeydown);
  $("open-projection").addEventListener("click", () => {
    if (!ui.code) return;
    // token 不放網址：投影畫面從同一瀏覽器的 localStorage 取得老師身分（research.md R5）
    window.open(`projection.html?code=${encodeURIComponent(ui.code)}`, "_blank", "noopener");
  });
  onTeacherSnapshot(onSnapshot);
  onTeacherReset(onReset);
  syncVisibility();
}

start();
