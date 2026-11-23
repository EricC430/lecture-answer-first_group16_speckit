// 001 學生頁：以組號加入組別、以本分頁保存的裝置身分恢復，並同步顯示活動狀態。
// 所有不可信文字一律用 textContent（原則 V）。

import { apiRequest, showError } from "./api.js";
import { clearIdentity, getDeviceToken, normalizeCode, setDeviceToken } from "./identity.js";
import { startCountdown } from "./countdown.js";
import { connectSync } from "./sync.js";

const STAGE_LABELS = {
  PREPARING: "準備中",
  JOINING: "開放加入",
  ROUND_OPEN: "搶答中",
  RESULT_PENDING: "結果未定案",
  RESULT_FINAL: "結果已定案",
  ENDED: "已結束",
  CANCELLED: "已取消",
};
const UNAUTHORIZED_MESSAGES = {
  GROUP_DELETED: "此組已被老師刪除，請重新加入。",
  LEFT_GROUP: "已離開本組，請重新加入。",
  INVALID_TOKEN: "身分已失效，請重新加入。",
};

const $ = (id) => document.getElementById(id);
const countdown = startCountdown(() => $("student-countdown"));
const renderers = [];

/** 讓後續 Story 的畫面元件註冊快照渲染函式。 */
export function onStudentSnapshot(render) {
  renderers.push(render);
}

function showJoinForm() {
  $("student-info").hidden = true;
  $("student-join").hidden = false;
}

function render(snapshot) {
  $("student-join").hidden = true;
  $("student-info").hidden = false;
  $("student-code").textContent = snapshot.code;
  $("student-group").textContent = snapshot.ownGroup ? `第 ${snapshot.ownGroup.number} 組` : "";
  $("student-credential").textContent = snapshot.ownGroup ? snapshot.ownGroup.credential : "";
  $("student-success").textContent = snapshot.ownGroup ? String(snapshot.ownGroup.successCount) : "";
  $("student-stage").textContent = STAGE_LABELS[snapshot.stage] ?? snapshot.stage;
  $("student-round").textContent = snapshot.roundNumber ? `第 ${snapshot.roundNumber} 輪` : "";
  const open = snapshot.stage === "ROUND_OPEN";
  $("student-open").hidden = !open;
  $("student-open-questions").textContent = snapshot.openQuestions.map((q) => `第 ${q} 題`).join("、");
  countdown.set(open ? snapshot.deadline : null);
  $("student-ended").hidden = snapshot.stage !== "ENDED";
  $("student-unsolved").textContent = snapshot.unsolvedQuestions.length
    ? snapshot.unsolvedQuestions.map((q) => `第 ${q} 題`).join("、")
    : "無";
  $("student-cancelled").hidden = snapshot.stage !== "CANCELLED";
  for (const fn of renderers) fn(snapshot);
}

const state = { code: null, sync: null };

/** 讓後續 Story 取得目前活動代碼與裝置 token。 */
export function currentIdentity() {
  return { code: state.code, token: state.code ? getDeviceToken(state.code) : null };
}

/** 以本分頁的裝置身分開始同步；身分失效時回到加入畫面。 */
export function startSync(code, token) {
  state.code = code;
  if (state.sync) state.sync.close();
  state.sync = connectSync(code, token, {
    onSnapshot: render,
    onGone: () => {
      clearIdentity(code);
      showJoinForm();
    },
    onUnauthorized: (reason) => {
      clearIdentity(code);
      showJoinForm();
      showError($("student-error"), {
        message: UNAUTHORIZED_MESSAGES[reason] ?? UNAUTHORIZED_MESSAGES.INVALID_TOKEN,
      });
    },
  });
}

async function joinGroup(event) {
  event.preventDefault();
  const code = normalizeCode($("join-code").value);
  const credential = $("join-credential").value.trim();
  const button = $("student-join").querySelector("button");
  button.disabled = true;
  // 組號原樣送出，由後端正規化並回傳「組號須為 1～N 的整數」
  const result = await apiRequest("POST", `/api/activities/${encodeURIComponent(code)}/groups/join`, {
    body: { groupNumber: $("join-number").value, credential: credential || null },
  });
  button.disabled = false;
  showError($("student-error"), result.ok ? null : result.error);
  if (!result.ok) return;
  setDeviceToken(code, result.data.deviceToken);
  $("join-credential").value = "";
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  startSync(code, result.data.deviceToken);
}

// ── US7：離開本組（搶答中停用，alignment 2026-11-23 B4）──

function renderLeave(snapshot) {
  const roundOpen = snapshot.stage === "ROUND_OPEN";
  const terminal = snapshot.stage === "ENDED" || snapshot.stage === "CANCELLED";
  $("leave-group").hidden = terminal;
  $("leave-group").disabled = roundOpen;
  $("leave-hint").hidden = !roundOpen || terminal;
  // 已結束或已取消：維持在結果畫面，由學生按「加入其他活動」才回到加入畫面
  $("new-join").hidden = !terminal;
}

/** 離開已結束或已取消的活動，回到加入畫面。 */
function joinAnother() {
  const { code } = currentIdentity();
  if (state.sync) state.sync.close();
  state.sync = null;
  if (code) clearIdentity(code);
  state.code = null;
  showError($("student-error"), null);
  showJoinForm();
  history.replaceState(null, "", location.pathname);
}

onStudentSnapshot(renderLeave);

async function leaveGroup() {
  const { code, token } = currentIdentity();
  if (!code || !token) return;
  const button = $("leave-group");
  if (button.disabled) return;
  button.disabled = true; // 送出期間停用，避免連按（PR #15 第二次審查問題 3）
  const result = await apiRequest("POST", `/api/activities/${encodeURIComponent(code)}/groups/leave`, {
    token,
    body: {},
  });
  button.disabled = false;
  // 成功時伺服端會送出 unauthorized（LEFT_GROUP），由同步處理回到加入畫面並顯示提示；
  // 推送可能比 HTTP 回應先到，所以成功時不要清掉那則提示
  if (!result.ok) showError($("student-error"), result.error);
}

function init() {
  $("student-join").addEventListener("submit", joinGroup);
  $("leave-group").addEventListener("click", leaveGroup);
  $("new-join").addEventListener("click", joinAnother);
  const code = normalizeCode(new URLSearchParams(location.search).get("code"));
  $("join-code").value = code;
  if (!code) return;
  const token = getDeviceToken(code);
  if (!token) return;
  startSync(code, token);
}

init();
