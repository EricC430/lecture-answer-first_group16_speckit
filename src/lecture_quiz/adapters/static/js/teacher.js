// 001 老師頁：建立活動、恢復老師身分、同步顯示活動狀態。
// 所有不可信文字（組名等）一律用 textContent 輸出（原則 V）。

import { apiRequest, showError } from "./api.js";
import {
  clearLastTeacherCode,
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
  JOINING: "開放加入",
  ROUND_OPEN: "搶答中",
  RESULT_PENDING: "結果未定案",
  RESULT_FINAL: "結果已定案",
  ENDED: "已結束",
  CANCELLED: "已取消",
};

const $ = (id) => document.getElementById(id);

const state = { code: null, token: null, snapshot: null, sync: null };
const renderers = [];
const resetters = [];

/** 註冊「換活動時清掉舊畫面」的函式（建立新活動、活動失效回到建立畫面時呼叫）。 */
export function onTeacherReset(reset) {
  resetters.push(reset);
}

/** 讓後續 Story 的畫面元件註冊快照渲染函式。 */
export function onTeacherSnapshot(render) {
  renderers.push(render);
  if (state.snapshot) render(state.snapshot, state);
}

/** 以目前老師身分呼叫 API；失敗時在活動區塊顯示錯誤。 */
let actionInFlight = false;

/**
 * 以目前老師身分呼叫 API；失敗時在活動區塊顯示錯誤。
 * 送出期間停用活動區塊的所有按鈕並忽略新的操作，避免連按時第二次請求回 409、
 * 把成功後的畫面蓋成錯誤（PR #15 第二次審查問題 3）。
 */
export async function teacherAction(method, path, body) {
  if (actionInFlight) return { ok: false, skipped: true };
  actionInFlight = true;
  const disabled = [...$("activity-section").querySelectorAll("button:not(:disabled)")];
  for (const button of disabled) button.disabled = true;
  try {
    const result = await apiRequest(
      method,
      `/api/activities/${encodeURIComponent(state.code)}${path}`,
      { token: state.token, body },
    );
    showError($("activity-error"), result.ok ? null : result.error);
    return result;
  } finally {
    for (const button of disabled) button.disabled = false;
    actionInFlight = false;
  }
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
  if (state.code !== null && state.code !== code) resetPage();
  state.code = code;
  state.token = token;
  if (state.sync) state.sync.close();
  state.sync = connectSync(code, token, {
    onSnapshot: render,
    onGone: showCreateForm,
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
  if (!result.ok && result.error?.code === "TEACHER_HAS_ACTIVE_ACTIVITY" && previousToken) {
    // C7：這個瀏覽器已有存續中的活動（例如另一個分頁還停在建立畫面），直接回到該活動（US1-AS2）；
    // 訊息仍依 FR-037 告知代碼與「請先結束或取消它」
    openActivity(lastCode, previousToken);
    showError($("activity-error"), {
      message: `你已有一個進行中的活動（代碼 ${lastCode}），已回到該活動；要建立新活動請先結束或取消它。`,
    });
    return;
  }
  showError($("activity-error"), result.ok ? null : result.error);
  if (!result.ok) return;
  const { code, teacherToken } = result.data;
  setTeacherToken(code, teacherToken);
  setLastTeacherCode(code);
  openActivity(code, teacherToken);
}

/** 把活動代碼放回網址（重新整理時用得到）並連線同步。 */
function openActivity(code, token) {
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  start(code, token);
}

// ── US3：開輪面板與開發用假題目 ──

let lastQuestionKey = "";

function renderOpenRoundPanel(snapshot) {
  const canOpen = snapshot.stage === "JOINING" || snapshot.stage === "RESULT_FINAL";
  $("open-round-panel").hidden = !canOpen;
  $("activity-questions").textContent = snapshot.questionNumbers.length
    ? snapshot.questionNumbers.map((q) => `第 ${q} 題`).join("、")
    : "尚未匯入";
  // 預設只列未成功題；已搶答正確的題目不可再開輪。
  // 已定案輪次裡有搶答成功者的題就是已成功題（004 的 ranking；001 只在結束時才附 unsolvedQuestions）。
  const solved = new Set();
  for (const round of snapshot.ranking?.rounds ?? []) {
    if (!round.final) continue;
    for (const question of round.questions) {
      if (question.successGroup !== null) solved.add(question.questionNumber);
    }
  }
  const unsolved = snapshot.questionNumbers.filter((q) => !solved.has(q));
  // 題目清單或階段改變時才重畫，避免老師勾到一半被同步覆蓋
  const key = `${snapshot.code}|${snapshot.stage}|${snapshot.roundNumber}|${unsolved.join(",")}`;
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

onTeacherSnapshot(renderOpenRoundPanel);

// ── US4：關輪、定案與倒數 ──

const countdown = startCountdown(() => $("round-countdown"));

function renderRoundControls(snapshot) {
  const open = snapshot.stage === "ROUND_OPEN";
  $("round-status").hidden = !open;
  $("round-questions").textContent = snapshot.openQuestions.map((q) => `第 ${q} 題`).join("、");
  countdown.set(open ? snapshot.deadline : null);
  $("close-round").hidden = !open;
}

onTeacherSnapshot(renderRoundControls);

// ── US5：結束與取消 ──

function formatQuestions(numbers) {
  return numbers.length ? numbers.map((q) => `第 ${q} 題`).join("、") : "無";
}

function renderClosing(snapshot) {
  $("end-activity").hidden = snapshot.stage !== "RESULT_FINAL";
  // 開輪前（準備中、開放加入）都可以取消活動
  $("cancel-activity").hidden = !["PREPARING", "JOINING"].includes(snapshot.stage);
  // 準備中：老師匯入題目後按「開放加入」，學生才能加入
  $("open-joining").hidden = snapshot.stage !== "PREPARING";
  $("open-joining").disabled = snapshot.questionNumbers.length === 0;
  $("open-joining").title = snapshot.questionNumbers.length ? "" : "請先匯入題目";
  $("ended-summary").hidden = snapshot.stage !== "ENDED";
  $("ended-unsolved").textContent = formatQuestions(snapshot.unsolvedQuestions);
  $("cancelled-summary").hidden = snapshot.stage !== "CANCELLED";
  // 已結束或已取消：維持在結果畫面，由老師按「建立新活動」才回到建立畫面
  $("new-activity").hidden = !["ENDED", "CANCELLED"].includes(snapshot.stage);
}

/**
 * 清掉上一個活動留在畫面與模組裡的內容：開輪面板、各子功能區塊（先藏起來，
 * 新活動的第一份快照到了再由各自的渲染函式決定是否顯示），並通知各模組重設自己的狀態。
 */
function resetPage() {
  lastQuestionKey = "";
  $("open-round-questions").replaceChildren();
  $("open-round-panel").hidden = true;
  for (const section of document.querySelectorAll("section[data-feature]")) {
    if (section.id !== "activity-section") section.hidden = true;
  }
  for (const reset of resetters) reset();
}

/** 回到建立活動畫面（只在已結束或已取消後由老師按鈕觸發；與後端重啟後的 gone 畫面一致）。 */
function showCreateForm() {
  // 舊活動已結束、已取消或已失效：重新整理時要停在建立畫面，不再自動回到它（Issue #29）
  clearLastTeacherCode();
  resetPage();
  if (state.sync) state.sync.close();
  state.sync = null;
  state.snapshot = null;
  state.code = null;
  state.token = null;
  showError($("activity-error"), null);
  $("activity-info").hidden = true;
  $("activity-create").hidden = false;
  history.replaceState(null, "", location.pathname);
}

onTeacherSnapshot(renderClosing);

// ── US2：組別清單（各組憑證是同組裝置都失去身分時的備援，alignment 2026-11-23 B3）──

const groupActions = [];

/** 讓後續 Story 在每一列組別加上操作按鈕（例如 US7 的刪除）。 */
export function onGroupRow(addAction) {
  groupActions.push(addAction);
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function renderGroups(snapshot) {
  const groups = snapshot.groups ?? [];
  $("groups-empty").hidden = groups.length > 0;
  $("groups-table").hidden = groups.length === 0;
  const rows = groups.map((group) => {
    const tr = document.createElement("tr");
    tr.append(
      cell(`第 ${group.number} 組`),
      cell(group.credential),
      cell(String(group.deviceCount)),
      cell(String(group.successCount)),
      cell(group.hasSubmissions ? "有" : "無"),
    );
    const actions = document.createElement("td");
    for (const add of groupActions) add(actions, group, snapshot);
    tr.append(actions);
    return tr;
  });
  $("groups-body").replaceChildren(...rows);
}

onTeacherSnapshot(renderGroups);

// ── US7：刪除沒有作答紀錄的組別（alignment 2026-11-23 B5；開放加入與結果階段可刪，搶答中不可刪）──

onGroupRow((td, group, snapshot) => {
  const deletable = ["JOINING", "RESULT_PENDING", "RESULT_FINAL"].includes(snapshot.stage);
  if (group.hasSubmissions || !deletable) return;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "刪除";
  button.addEventListener("click", () => {
    if (!window.confirm(`確定要刪除第 ${group.number} 組嗎？該組 ${group.deviceCount} 台裝置會回到加入畫面，舊憑證失效。`)) return;
    teacherAction("DELETE", `/groups/${group.number}`);
  });
  td.append(button);
});

function init() {
  $("create-activity").addEventListener("click", createActivity);
  $("open-round-panel").addEventListener("submit", openRound);
  $("close-round").addEventListener("click", () => teacherAction("POST", "/rounds/current/close", {}));
  $("end-activity").addEventListener("click", () => teacherAction("POST", "/end", {}));
  $("open-joining").addEventListener("click", () => teacherAction("POST", "/open-joining", {}));
  $("cancel-activity").addEventListener("click", () => teacherAction("POST", "/cancel", {}));
  $("new-activity").addEventListener("click", showCreateForm);
  const code = normalizeCode(new URLSearchParams(location.search).get("code"));
  if (!code) {
    // 網址沒有代碼（新分頁或重新輸入網址）：回到這個瀏覽器最後建立的活動（US1-AS2、FR-003）。
    // 活動已失效（例如後端重啟）時，同步會回報 gone，畫面回到建立活動。
    const lastCode = getLastTeacherCode();
    const lastToken = lastCode ? getTeacherToken(lastCode) : null;
    if (lastCode && lastToken) openActivity(lastCode, lastToken);
    return;
  }
  const token = getTeacherToken(code);
  if (!token) {
    showError($("activity-error"), { message: "需要該活動的老師身分。請在建立活動的瀏覽器開啟，或建立新的活動。" });
    return;
  }
  start(code, token);
}

init();
