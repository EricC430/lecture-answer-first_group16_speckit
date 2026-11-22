// 001 老師頁：建立活動、恢復老師身分、同步顯示活動狀態。
// 所有不可信文字（組名等）一律用 textContent 輸出（原則 V）。

import { apiRequest, showError } from "./api.js";
import { getTeacherToken, normalizeCode, setTeacherToken } from "./identity.js";
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
  const result = await apiRequest("POST", "/api/activities", { body: {} });
  button.disabled = false;
  showError($("activity-error"), result.ok ? null : result.error);
  if (!result.ok) return;
  const { code, teacherToken } = result.data;
  setTeacherToken(code, teacherToken);
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  start(code, teacherToken);
}

function init() {
  $("create-activity").addEventListener("click", createActivity);
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
