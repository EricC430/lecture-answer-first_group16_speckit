// 001 學生頁：以本分頁保存的裝置身分恢復並同步顯示活動狀態。
// 加入表單待 US2（組號＋組數上限）實作；所有不可信文字一律用 textContent（原則 V）。

import { showError } from "./api.js";
import { clearIdentity, getDeviceToken, normalizeCode } from "./identity.js";
import { startCountdown } from "./countdown.js";
import { connectSync } from "./sync.js";

const STAGE_LABELS = {
  PREPARING: "準備中",
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

function render(snapshot) {
  $("student-join-pending").hidden = true;
  $("student-info").hidden = false;
  $("student-code").textContent = snapshot.code;
  $("student-group").textContent = snapshot.ownGroup ? snapshot.ownGroup.name : "";
  $("student-success").textContent = snapshot.ownGroup ? String(snapshot.ownGroup.successCount) : "";
  $("student-stage").textContent = STAGE_LABELS[snapshot.stage] ?? snapshot.stage;
  $("student-round").textContent = snapshot.roundNumber ? `第 ${snapshot.roundNumber} 輪` : "";
  const open = snapshot.stage === "ROUND_OPEN";
  $("student-open").hidden = !open;
  $("student-open-questions").textContent = snapshot.openQuestions.map((q) => `第 ${q} 題`).join("、");
  countdown.set(open ? snapshot.deadline : null);
  for (const fn of renderers) fn(snapshot);
}

function init() {
  const code = normalizeCode(new URLSearchParams(location.search).get("code"));
  if (!code) return;
  const token = getDeviceToken(code);
  if (!token) return;
  connectSync(code, token, {
    onSnapshot: render,
    onGone: () => {
      $("student-info").hidden = true;
      $("student-join-pending").hidden = false;
    },
    onUnauthorized: (reason) => {
      clearIdentity(code);
      $("student-info").hidden = true;
      $("student-join-pending").hidden = false;
      showError($("student-error"), { message: UNAUTHORIZED_MESSAGES[reason] ?? UNAUTHORIZED_MESSAGES.INVALID_TOKEN });
    },
  });
}

init();
