// 001 老師頁：建立活動、恢復老師身分、同步顯示活動狀態。
// 所有不可信文字（組名等）一律用 textContent 輸出（原則 V）。

import { apiRequest, showError } from "./api.js";
import {
  getLastTeacherCode,
  getTeacherToken,
  normalizeCode,
  setLastTeacherCode,
  setTeacherToken,
} from "./identity.js";
import { startCountdown } from "./countdown.js";
import { connectSync } from "./sync.js";

export const STAGE_LABELS = {
  PREPARING: "準備中",
  ROUND_OPEN: "搶答中",
  RESULT_PENDING: "結果未定案",
  RESULT_FINAL: "結果已定案",
  ENDED: "已結束",
  CANCELLED: "已取消",
};

const $ = (id) => document.getElementById(id);

const state = { code: null, token: null, snapshot: null, sync: null };
const renderers = [];

/** 讓後續 Story 的畫面元件註冊快照渲染函式。 */
export function onTeacherSnapshot(render) {
  renderers.push(render);
  if (state.snapshot) render(state.snapshot, state);
}

/** 以目前老師身分呼叫 API；失敗時在活動區塊顯示錯誤。 */
export async function teacherAction(method, path, body) {
  const result = await apiRequest(method, `/api/activities/${encodeURIComponent(state.code)}${path}`, {
    token: state.token,
    body,
  });
  showError($("activity-error"), result.ok ? null : result.error);
  return result;
}

function render(snapshot) {
  state.snapshot = snapshot;
  $("activity-create").hidden = true;
  $("activity-info").hidden = false;
  $("activity-code").textContent = snapshot.code;
  $("activity-max-groups").textContent = String(snapshot.maxGroups);
  $("activity-stage").textContent = STAGE_LABELS[snapshot.stage] ?? snapshot.stage;
  $("activity-round").textContent = snapshot.roundNumber ? `第 ${snapshot.roundNumber} 輪` : "";
  for (const fn of renderers) fn(snapshot, state);
}

function start(code, token) {
  state.code = code;
  state.token = token;
  if (state.sync) state.sync.close();
  state.sync = connectSync(code, token, {
    onSnapshot: render,
    onGone: () => {
      $("activity-info").hidden = true;
      $("activity-create").hidden = false;
    },
    onUnauthorized: () => showError($("activity-error"), { message: "需要該活動的老師身分。" }),
  });
}

async function createActivity() {
  const button = $("create-activity");
  button.disabled = true;
  const rawMax = $("create-max-groups").value.trim();
  // 原樣送出，由後端驗證並回傳「組數上限須為 1～99 的整數」
  const maxGroups = rawMax === "" ? null : Number(rawMax);
  // C7：附上這個瀏覽器上一個活動的老師身分，仍存續時後端會拒絕
  const lastCode = getLastTeacherCode();
  const previousToken = lastCode ? getTeacherToken(lastCode) : null;
  const result = await apiRequest("POST", "/api/activities", {
    token: previousToken,
    body: { maxGroups },
  });
  button.disabled = false;
  showError($("activity-error"), result.ok ? null : result.error);
  if (!result.ok) return;
  const { code, teacherToken } = result.data;
  setTeacherToken(code, teacherToken);
  setLastTeacherCode(code);
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  start(code, teacherToken);
}

// ── US3：開輪面板與開發用假題目 ──

let lastQuestionKey = "";

function renderOpenRoundPanel(snapshot) {
  const canOpen = snapshot.stage === "PREPARING" || snapshot.stage === "RESULT_FINAL";
  $("open-round-panel").hidden = !canOpen;
  $("activity-questions").textContent = snapshot.questionNumbers.length
    ? snapshot.questionNumbers.map((q) => `第 ${q} 題`).join("、")
    : "尚未匯入";
  // 老師快照目前沒有「已成功題」欄位（001 的定案不標記成功題，由 004 補上），
  // 先列出全部題目；選到已成功題時由後端拒絕並說明。
  const unsolved = snapshot.questionNumbers;
  // 題目清單或階段改變時才重畫，避免老師勾到一半被同步覆蓋
  const key = `${snapshot.stage}|${snapshot.roundNumber}|${snapshot.questionNumbers.join(",")}`;
  if (!canOpen || key === lastQuestionKey) return;
  lastQuestionKey = key;
  const box = $("open-round-questions");
  box.replaceChildren();
  for (const q of unsolved) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = String(q);
    input.checked = true;
    label.append(input, ` 第 ${q} 題 `);
    box.append(label);
  }
}

async function openRound(event) {
  event.preventDefault();
  const questionNumbers = [...$("open-round-questions").querySelectorAll("input:checked")].map(
    (input) => Number(input.value),
  );
  const rawCountdown = $("open-round-countdown").value.trim();
  const body = {
    questionNumbers,
    fairMode: $("open-round-fair").checked,
    // 原樣送出，由後端驗證並回傳「倒數秒數須為 1～3600 的整數」
    countdownSeconds: rawCountdown === "" ? null : Number(rawCountdown),
  };
  await teacherAction("POST", "/rounds", body);
}

async function seedQuestions() {
  const result = await apiRequest(
    "POST",
    `/api/dev/activities/${encodeURIComponent(state.code)}/seed-questions`,
    { token: state.token, body: { count: 4 } },
  );
  showError($("activity-error"), result.ok ? null : result.error);
}

async function detectDevSeed() {
  const result = await apiRequest("GET", "/api/dev/status");
  $("dev-seed").hidden = !(result.ok && result.data?.enabled);
}

onTeacherSnapshot(renderOpenRoundPanel);

// ── US4：關輪、定案與倒數 ──

const countdown = startCountdown(() => $("round-countdown"));

function renderRoundControls(snapshot) {
  const open = snapshot.stage === "ROUND_OPEN";
  $("round-status").hidden = !open;
  $("round-questions").textContent = snapshot.openQuestions.map((q) => `第 ${q} 題`).join("、");
  countdown.set(open ? snapshot.deadline : null);
  $("close-round").hidden = !open;
  $("finalize-round").hidden = snapshot.stage !== "RESULT_PENDING";
}

onTeacherSnapshot(renderRoundControls);

// ── US5：結束與取消 ──

function formatQuestions(numbers) {
  return numbers.length ? numbers.map((q) => `第 ${q} 題`).join("、") : "無";
}

function renderClosing(snapshot) {
  $("end-activity").hidden = snapshot.stage !== "RESULT_FINAL";
  $("cancel-activity").hidden = snapshot.stage !== "PREPARING";
  $("ended-summary").hidden = snapshot.stage !== "ENDED";
  $("ended-unsolved").textContent = formatQuestions(snapshot.unsolvedQuestions);
  $("cancelled-summary").hidden = snapshot.stage !== "CANCELLED";
}

onTeacherSnapshot(renderClosing);

function init() {
  $("create-activity").addEventListener("click", createActivity);
  $("open-round-panel").addEventListener("submit", openRound);
  $("dev-seed").addEventListener("click", seedQuestions);
  $("close-round").addEventListener("click", () => teacherAction("POST", "/rounds/current/close", {}));
  $("finalize-round").addEventListener("click", () =>
    teacherAction("POST", "/rounds/current/finalize", {}),
  );
  $("end-activity").addEventListener("click", () => teacherAction("POST", "/end", {}));
  $("cancel-activity").addEventListener("click", () => teacherAction("POST", "/cancel", {}));
  detectDevSeed();
  const code = normalizeCode(new URLSearchParams(location.search).get("code"));
  if (!code) return;
  const token = getTeacherToken(code);
  if (!token) {
    showError($("activity-error"), { message: "需要該活動的老師身分。請在建立活動的瀏覽器開啟，或建立新的活動。" });
    return;
  }
  start(code, token);
}

init();
