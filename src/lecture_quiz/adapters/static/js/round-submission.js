// 003 學生頁：本輪開放題的作答表單與送出（US1）。
// 依快照的 openQuestions 與 questionShapes（每題格數）畫出表單；只有收到成功回應才顯示「已送出」（FR-032）。

import { apiRequest } from "./api.js";
import { currentIdentity, onStudentSnapshot } from "./student.js";
import { describeSubmitError, el, renderAnswerForm } from "./submission.js";

const $ = (id) => document.getElementById(id);
const forms = new Map(); // key：`${roundNumber}:${questionNumber}`，保留學生已輸入的內容
let currentRound = null;

async function submitAnswer(roundNumber, questionNumber, answers, form) {
  const { code, token } = currentIdentity();
  if (!code || !token) return;
  form.setBusy(true);
  const result = await apiRequest("POST", `/api/activities/${encodeURIComponent(code)}/submissions`, {
    token,
    body: { roundNumber, questionNumber, answers },
  });
  form.setBusy(false);
  if (result.ok && result.data && result.data.submission) {
    const already = result.data.result === "alreadySubmitted";
    form.showSubmitted(result.data.submission, already ? "本組已送出" : "已送出");
    return;
  }
  form.showError(describeSubmitError(result.error));
}

function render(snapshot) {
  const section = $("round-submission-section");
  const list = $("answer-forms");
  const open = snapshot.stage === "ROUND_OPEN";
  section.hidden = !open;
  if (!open) return;
  if (currentRound !== snapshot.roundNumber) {
    forms.clear();
    list.replaceChildren();
    currentRound = snapshot.roundNumber;
  }
  const shapes = snapshot.questionShapes ?? {};
  for (const questionNumber of snapshot.openQuestions) {
    const key = `${snapshot.roundNumber}:${questionNumber}`;
    if (forms.has(key)) continue;
    const blanks = Number(shapes[String(questionNumber)] ?? 0);
    if (!blanks) {
      list.append(el("p", `第 ${questionNumber} 題的格數尚未載入，請重新整理。`, "error-message"));
      continue;
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
}

onStudentSnapshot(render);
