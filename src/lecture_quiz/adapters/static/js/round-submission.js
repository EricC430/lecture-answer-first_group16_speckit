// 003 學生頁：本輪開放題的作答表單與送出（US1、US2、US3）。
// 依快照的 openQuestions 與 questionShapes（每題格數）畫出表單；只有收到成功回應才顯示「已送出」（FR-032）。
// 快照的 submissions.current.own 有本組已送出的題目時（例如同組另一台裝置送的），該題改為唯讀並顯示答案（US2）。
// 已關輪輪次的結果由 004 的 ranking-review.js 顯示（只顯示本組、目前搶答成功者與剛被判錯者，FR-037）；
// 這裡不再列出各組答案。
// 倒數依快照的後端 deadline；歸零時停用未送出的表單，沒有截止時間時顯示「由老師結束」（US6）。
// 截止判定以後端為準：前端時鐘有誤差時，送出仍會被後端以「本輪已結束」拒絕。

import { apiRequest } from "./api.js";
import { currentIdentity, onStudentReset, onStudentSnapshot } from "./student.js";
import { describeSubmitError, el, renderAnswerForm } from "./submission.js";

const $ = (id) => document.getElementById(id);
const forms = new Map(); // key：`${roundNumber}:${questionNumber}`，保留學生已輸入的內容
const notices = new Map(); // 同一個 key：「格數尚未載入」提示，每題只顯示一則
let currentRound = null;
let deadlineTimer = null;
let scheduledDeadline;

async function submitAnswer(roundNumber, questionNumber, answers, form) {
  // 007：身分在 HttpOnly cookie，由瀏覽器自動帶上；這裡不附任何 token
  const { code, connected } = currentIdentity();
  if (!code || !connected) return;
  form.setBusy(true);
  const result = await apiRequest("POST", `/api/activities/${encodeURIComponent(code)}/submissions`, {
    body: { roundNumber, questionNumber, answers },
  });
  form.setBusy(false);
  if (result.ok && result.data && result.data.submission) {
    const already = result.data.result === "alreadySubmitted";
    form.showSubmitted(result.data.submission, already ? "本組已送出" : "已送出");
    return;
  }
  const errorCode = result.error?.code;
  if (errorCode === "STALE_ROUND") {
    // 舊頁面：提示並提供重新整理（US3-AS4）
    form.showError(result.error.message, { label: "重新整理", onClick: () => window.location.reload() });
    return;
  }
  if (errorCode === "ROUND_CLOSED") {
    // 已截止或已關輪：停用全部作答表單（US3-AS2、US3-AS3）
    for (const other of forms.values()) if (!other.submitted) other.setDisabled(true);
  }
  form.showError(describeSubmitError(result.error));
}

function lockAfterDeadline() {
  // 倒數歸零：停用所有還沒送出的作答表單（US6-AS2；FR-029）
  for (const form of forms.values()) if (!form.submitted) form.setDisabled(true);
  $("round-deadline-note").textContent = "已到截止時間，不能再送出。";
}

function scheduleDeadline(deadline) {
  if (deadline === scheduledDeadline) return;
  scheduledDeadline = deadline;
  clearTimeout(deadlineTimer);
  deadlineTimer = null;
  const note = $("round-deadline-note");
  if (!deadline) {
    note.textContent = "本輪沒有倒數，由老師結束。"; // US6-AS3；FR-030
    return;
  }
  note.textContent = "倒數結束後就不能再送出（時間以伺服器為準）。";
  const remaining = Date.parse(deadline) - Date.now();
  if (remaining <= 0) lockAfterDeadline();
  else deadlineTimer = setTimeout(lockAfterDeadline, remaining);
}

function render(snapshot) {
  const section = $("round-submission-section");
  const list = $("answer-forms");
  const open = snapshot.stage === "ROUND_OPEN";
  section.hidden = !open;
  if (!open) {
    scheduleDeadline(undefined);
    return;
  }
  if (currentRound !== snapshot.roundNumber) {
    forms.clear();
    notices.clear();
    list.replaceChildren();
    currentRound = snapshot.roundNumber;
  }
  const shapes = snapshot.questionShapes ?? {};
  for (const questionNumber of snapshot.openQuestions) {
    const key = `${snapshot.roundNumber}:${questionNumber}`;
    if (forms.has(key)) continue;
    const blanks = Number(shapes[String(questionNumber)] ?? 0);
    if (!blanks) {
      // 每次推送都會重畫：提示只建立一次，避免累加（PR #16 審查第 2 項）
      if (!notices.has(key)) {
        const notice = el("p", `第 ${questionNumber} 題的格數尚未載入，請稍後或重新整理。`, "error-message");
        notices.set(key, notice);
        list.append(notice);
      }
      continue;
    }
    if (notices.has(key)) {
      notices.get(key).remove();
      notices.delete(key);
    }
    const roundNumber = snapshot.roundNumber;
    const form = renderAnswerForm({
      questionNumber,
      blanks,
      onSubmit: (answers) => submitAnswer(roundNumber, questionNumber, answers, form),
    });
    forms.set(key, form);
    list.append(form.element);
  }
  markOwnSubmissions(snapshot);
  scheduleDeadline(snapshot.deadline ?? null);
}

function markOwnSubmissions(snapshot) {
  const current = snapshot.submissions?.current;
  if (!current || current.roundNumber !== snapshot.roundNumber) return;
  for (const submission of current.own ?? []) {
    const form = forms.get(`${current.roundNumber}:${submission.questionNumber}`);
    if (form && !form.submitted) form.showSubmitted(submission, "本組已送出");
  }
}

onStudentSnapshot(render);

// 換活動時丟掉上一個活動留下的作答表單與已輸入的答案（否則新活動同輪次同題號會沿用舊答案）
onStudentReset(() => {
  forms.clear();
  notices.clear();
  $("answer-forms").replaceChildren();
  currentRound = null;
  scheduleDeadline(undefined);
});
