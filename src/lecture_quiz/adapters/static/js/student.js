// 001 學生頁：以組號加入組別、恢復身分，並同步顯示活動狀態。
// 007：學生身分是同一瀏覽器共用的 HttpOnly cookie（頁面讀不到），請求與同步連線都由瀏覽器
// 自動帶上；頁面只記得「目前顯示哪個活動、是否已同步成功」。載入時先確保瀏覽器有金鑰
// （POST /api/browser-session），完成前不能按加入。加入成功後以 BroadcastChannel 通知同一
// 瀏覽器的其他分頁（只傳活動代碼）。
// 所有不可信文字一律用 textContent（原則 V）。

import { apiRequest, showError } from "./api.js";
import { normalizeCode } from "./identity.js";
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
const NOT_FOUND_MESSAGE = "找不到這個活動代碼，請確認後再輸入。";
const SESSION_FAILED_MESSAGE = "無法建立瀏覽器身分，請重新整理頁面。";
const UNAUTHORIZED_MESSAGES = {
  GROUP_DELETED: "此組已被老師刪除，請重新加入。",
  LEFT_GROUP: "已離開本組，請重新加入。",
  INVALID_TOKEN: "身分已失效，請重新加入。",
};

const $ = (id) => document.getElementById(id);
const countdown = startCountdown(() => $("student-countdown"));
const renderers = [];
let lastSnapshot = null;

/**
 * 讓後續 Story 的畫面元件註冊快照渲染函式。
 * 各子功能的腳本是在 student.js 之後才載入；若第一份快照已經到了，要立刻補畫一次，
 * 否則要等到下一次狀態變更才看得到（與老師頁 onTeacherSnapshot 一致）。
 */
export function onStudentSnapshot(render) {
  renderers.push(render);
  if (lastSnapshot) render(lastSnapshot);
}


const resetters = [];

/** 註冊「換活動或回到加入畫面時清掉舊畫面與狀態」的函式。 */
export function onStudentReset(reset) {
  resetters.push(reset);
}

/** 清掉上一個活動留在畫面與模組裡的內容（作答表單、結果區塊、舊快照）。 */
function resetStudentPage() {
  lastSnapshot = null;
  for (const section of document.querySelectorAll("section[data-feature]")) {
    if (section.id !== "activity-section") section.hidden = true;
  }
  for (const reset of resetters) reset();
}

function showJoinForm() {
  resetStudentPage();
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
  lastSnapshot = snapshot;
  for (const fn of renderers) fn(snapshot);
}

// synced：這次同步是否已收到過快照。第一次連線就被拒（本來就沒有身分、代碼打錯）與
// 同步成功後才失去身分（離開、被刪除、後端重啟）要給不同提示（007 research R4、R7）。
const state = { code: null, sync: null, synced: false };

/** 讓後續 Story 取得目前活動代碼，以及是否已用 cookie 身分同步成功。 */
export function currentIdentity() {
  return { code: state.code, connected: state.synced };
}

function stopSync() {
  if (state.sync) state.sync.close();
  state.sync = null;
  state.synced = false;
}

function hideGoneBanner() {
  document.body.classList.remove("sync-broken");
  const banner = $("sync-banner");
  if (banner) banner.hidden = true;
}

/** 以這個瀏覽器的 cookie 身分開始同步；沒有或失去身分時回到加入畫面。 */
export function startSync(code) {
  if (state.code !== null && state.code !== code) resetStudentPage();
  state.code = code;
  stopSync();
  state.sync = connectSync(code, null, {
    onSnapshot: (snapshot) => {
      state.synced = true;
      render(snapshot);
    },
    onGone: () => {
      const neverSynced = !state.synced;
      stopSync();
      showJoinForm();
      if (neverSynced) {
        // 網址的代碼不存在（例如貼錯連結）：不是「活動已失效」
        hideGoneBanner();
        showError($("student-error"), { message: NOT_FOUND_MESSAGE });
      }
    },
    onUnauthorized: (reason) => {
      const neverSynced = !state.synced;
      stopSync();
      showJoinForm();
      // 第一次連線就沒有身分：這個瀏覽器本來就沒加入這個活動，安靜地顯示加入畫面
      if (neverSynced && reason === "INVALID_TOKEN") return;
      showError($("student-error"), {
        message: UNAUTHORIZED_MESSAGES[reason] ?? UNAUTHORIZED_MESSAGES.INVALID_TOKEN,
      });
    },
  });
}

// ── 007：同一瀏覽器的分頁通知（research R6；只傳活動代碼，不含身分）──

const channel = typeof BroadcastChannel === "function" ? new BroadcastChannel("lq-identity") : null;

function announceJoined(code) {
  if (channel) channel.postMessage({ type: "joined", code });
}

function followOtherTab(event) {
  const message = event.data;
  if (!message || message.type !== "joined" || typeof message.code !== "string") return;
  const code = normalizeCode(message.code);
  if (code.length !== 6) return;
  // 已經同步成功（正在看某個活動）的分頁不受影響；還在連線、尚未收到快照的分頁
  // 則改用通知的代碼重新同步，避免錯過通知（verification P-10）
  if (state.synced) return;
  showError($("student-error"), null);
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  startSync(code);
}

if (channel) channel.addEventListener("message", followOtherTab);

/** 確保這個瀏覽器有瀏覽器金鑰；完成前停用加入按鈕（research R3）。 */
async function ensureBrowserSession() {
  const button = $("student-join").querySelector("button");
  button.disabled = true;
  const result = await apiRequest("POST", "/api/browser-session");
  button.disabled = !result.ok;
  if (!result.ok) showError($("student-error"), { message: SESSION_FAILED_MESSAGE });
  return result.ok;
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
  if (!result.ok && result.error?.code !== "ALREADY_IN_GROUP") return;
  // 加入成功，或這個瀏覽器本來就是該活動的組員（重新打開瀏覽器後輸入代碼）：
  // 以 cookie 身分切到本組畫面；已是組員時保留「已是第 N 組成員」的提示（spec US1-AS3、AS5）
  $("join-credential").value = "";
  history.replaceState(null, "", `?code=${encodeURIComponent(code)}`);
  startSync(code);
  if (result.ok) announceJoined(code);
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
  // 007：已結束或取消的活動不需要也不能離開本組，cookie 身分保留，只重設畫面
  stopSync();
  state.code = null;
  showError($("student-error"), null);
  showJoinForm();
  history.replaceState(null, "", location.pathname);
}

onStudentSnapshot(renderLeave);

async function leaveGroup() {
  const { code, connected } = currentIdentity();
  if (!code || !connected) return;
  const button = $("leave-group");
  if (button.disabled) return;
  button.disabled = true; // 送出期間停用，避免連按（PR #15 第二次審查問題 3）
  const result = await apiRequest("POST", `/api/activities/${encodeURIComponent(code)}/groups/leave`, {
    body: {},
  });
  button.disabled = false;
  // 成功時伺服端會對這個瀏覽器的所有連線送出 unauthorized（LEFT_GROUP），由同步處理回到
  // 加入畫面並顯示提示（同一瀏覽器的其他分頁也一起回去）；推送可能比 HTTP 回應先到，
  // 所以成功時不要清掉那則提示
  if (!result.ok) showError($("student-error"), result.error);
}

async function init() {
  $("student-join").addEventListener("submit", joinGroup);
  $("leave-group").addEventListener("click", leaveGroup);
  $("new-join").addEventListener("click", joinAnother);
  const code = normalizeCode(new URLSearchParams(location.search).get("code"));
  $("join-code").value = code;
  if (!(await ensureBrowserSession())) return;
  // 網址有代碼：直接以 cookie 同步；這個瀏覽器沒有身分時會安靜地回到加入畫面
  if (code && state.sync === null) startSync(code);
}

init();
