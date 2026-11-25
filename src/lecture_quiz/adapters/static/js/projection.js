// 006 投影畫面（spec US7；FR-030～FR-037；research.md R5）。
// - 從網址取活動代碼；老師 token 取自同一瀏覽器的 localStorage（001 研究 R5），不放在網址。
// - 沒有 token：只顯示提示，不連線（學生打開連結也拿不到任何資料）。
// - 快照只交給 toProjectionView（白名單純函式），渲染只讀它的輸出；所有文字用 textContent。
// - 各輪記住最大 resultVersion，較舊的結果不覆蓋較新的（FR-034）。

import { getTeacherToken, normalizeCode } from "./identity.js";
import { toProjectionView } from "./projection-view.js";
import { connectSync } from "./sync.js";

const $ = (id) => document.getElementById(id);

const STATUS_TEXT = {
  SUCCESS: "搶答成功",
  CORRECT: "搶答正確",
  WRONG: "答錯",
  FAILED: "搶答失敗",
};
const STATUS_CLASS = {
  SUCCESS: "status-label--success",
  CORRECT: "status-label--success",
  WRONG: "status-label--danger",
  FAILED: "status-label--neutral",
};
const ROTATE_MS = 8000; // 卡片放不下時自動輪播（FR-037）

const state = {
  code: normalizeCode(new URLSearchParams(window.location.search).get("code")),
  versions: new Map(), // roundNumber → 已顯示的最大 resultVersion
  winners: new Map(), // `${round}:${question}` → 上一次顯示的成功組（只用來決定要不要播放遞補過場）
  roundNumber: null,
  countdownTimer: null,
  rotateTimer: null,
  page: 0,
};

function text(tag, value, className = "") {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

function renderCountdown(deadline) {
  clearInterval(state.countdownTimer);
  const element = $("projection-countdown");
  const tick = () => {
    if (!deadline) {
      element.textContent = "由老師結束";
      element.removeAttribute("data-urgent");
      return;
    }
    const remaining = Math.max(0, Math.ceil((Date.parse(deadline) - Date.now()) / 1000));
    element.textContent = remaining > 0 ? `剩餘 ${remaining} 秒` : "已到截止時間";
    element.toggleAttribute("data-urgent", remaining <= 10);
  };
  tick();
  if (deadline) state.countdownTimer = setInterval(tick, 250);
}

function entryNode(card, entry, key) {
  const row = document.createElement("li");
  row.className = "projection-entry";
  row.dataset.group = String(entry.groupNumber);
  if (card.successGroup === entry.groupNumber) row.classList.add("is-winner");
  const head = document.createElement("p");
  head.className = "projection-entry-head";
  head.append(
    text("span", entry.rank === null ? "—" : `第 ${entry.rank} 名`, "projection-rank"),
    text("span", `第 ${entry.groupNumber} 組`, "projection-group"),
    text("span", STATUS_TEXT[entry.displayStatus] ?? "", `status-label ${STATUS_CLASS[entry.displayStatus] ?? "status-label--neutral"}`),
  );
  row.append(head);
  if (entry.answers.length) row.append(text("p", entry.answers.join("／"), "projection-answer"));
  if (card.replacedGroup === entry.groupNumber) row.classList.add("was-replaced");
  return row;
}

function cardNode(view, card) {
  const key = `${view.roundNumber}:${card.questionNumber}`;
  // 遞補標示依後端的 replacedGroup（004：剛被判錯而被替換的組，與學生頁同一個來源，FR-035）；
  // 過場只在這個畫面實際看到成功者改變時播放
  const before = state.winners.get(key);
  const changed = before !== undefined && before !== card.successGroup;
  state.winners.set(key, card.successGroup);

  const node = document.createElement("article");
  node.className = "projection-card";
  node.dataset.question = String(card.questionNumber);
  node.append(text("h2", `第 ${card.questionNumber} 題`));
  if (card.successGroup !== null && card.replacedGroup !== null) {
    node.append(
      text("p", `第 ${card.successGroup} 組遞補（第 ${card.replacedGroup} 組答錯）`, "projection-replacement"),
    );
    if (changed) node.classList.add("has-replacement");
  }
  if (card.successGroup === null) {
    node.append(text("p", "未成功", "status-label status-label--neutral projection-unsolved"));
  }
  const list = document.createElement("ol");
  list.className = "projection-entries";
  for (const entry of card.entries) list.append(entryNode(card, entry, key));
  node.append(list);
  return node;
}

function paginate() {
  clearInterval(state.rotateTimer);
  const container = $("projection-results");
  const cards = [...container.querySelectorAll(".projection-card")];
  for (const card of cards) card.hidden = false;
  if (cards.length === 0) return;
  // 放不下時分組輪播；每一頁都是完整卡片，所以每題的成功者一定會出現（FR-037）
  const available = window.innerHeight - container.getBoundingClientRect().top;
  if (container.scrollHeight <= available + 4) return;
  const pages = [];
  let current = [];
  let used = 0;
  for (const card of cards) {
    const height = card.getBoundingClientRect().height + 16;
    if (current.length && used + height > available) {
      pages.push(current);
      current = [];
      used = 0;
    }
    current.push(card);
    used += height;
  }
  if (current.length) pages.push(current);
  const show = () => {
    state.page %= pages.length;
    pages.forEach((group, index) => group.forEach((card) => { card.hidden = index !== state.page; }));
    container.dataset.page = `${state.page + 1}/${pages.length}`;
  };
  show();
  state.rotateTimer = setInterval(() => {
    state.page += 1;
    show();
  }, ROTATE_MS);
}

function renderResults(view) {
  const container = $("projection-results");
  if (view.mode !== "results" || !view.results) {
    container.hidden = true;
    container.replaceChildren();
    clearInterval(state.rotateTimer);
    return;
  }
  const seen = state.versions.get(view.roundNumber) ?? 0;
  if (view.resultVersion < seen) return; // 舊版本晚到：不覆蓋（FR-034）
  state.versions.set(view.roundNumber, view.resultVersion);
  container.hidden = false;
  container.replaceChildren(...view.results.map((card) => cardNode(view, card)));
  paginate();
}

function render(snapshot) {
  const view = toProjectionView(snapshot, Boolean(getTeacherToken(state.code)));
  document.body.dataset.mode = view.mode;
  if (view.mode === "unavailable") return;
  if (state.roundNumber !== view.roundNumber && view.roundNumber !== undefined) {
    state.roundNumber = view.roundNumber ?? null;
  }
  $("projection-code").textContent = view.code;
  $("projection-stage").textContent = view.final ? "結果已定案" : view.stageLabel;
  const hint = {
    lobby: "用手機打開學生頁，輸入活動代碼與組號加入",
    round: "",
    results: view.final ? "" : "老師確認中，結果可能更新",
    ended: view.unsolved?.length
      ? `活動已結束。未成功題：${view.unsolved.map((n) => `第 ${n} 題`).join("、")}`
      : "活動已結束。所有題目都已有搶答成功者",
    cancelled: "活動已取消",
  }[view.mode];
  $("projection-hint").textContent = hint ?? "";
  const round = view.mode === "round" || view.mode === "results";
  $("projection-round").hidden = !round;
  if (round) {
    const mode = view.fairMode ? "公平模式" : "速度模式";
    const questions = view.questionNumbers.map((n) => `第 ${n} 題`).join("、");
    $("projection-questions").textContent = `第 ${view.roundNumber} 輪・${mode}${questions ? `・${questions}` : ""}`;
  }
  if (view.mode === "round") renderCountdown(view.deadline);
  else {
    clearInterval(state.countdownTimer);
    $("projection-countdown").textContent = "";
  }
  renderResults(view);
}

function start() {
  const token = state.code ? getTeacherToken(state.code) : null;
  if (!token) {
    document.body.dataset.mode = "unavailable";
    $("projection-hint").textContent = "請從老師頁開啟投影畫面（需要同一個瀏覽器的老師身分）。";
    $("projection-stage").textContent = "";
    return;
  }
  $("projection-code").textContent = state.code;
  // 測試與除錯用的渲染入口：只接受快照、只經過白名單（contracts/projection-view.md「版本處理」）
  window.__projectionRender = render;
  connectSync(state.code, token, {
    onSnapshot: render,
    onGone: () => {
      $("projection-hint").textContent = "活動已失效，請重新建立活動";
      $("projection-results").hidden = true;
    },
    onUnauthorized: () => {
      $("projection-hint").textContent = "請從老師頁開啟投影畫面（需要同一個瀏覽器的老師身分）。";
    },
  });
  window.addEventListener("resize", paginate);
}

start();
