// 003 學生頁：本輪開放題的作答表單與送出（US1、US2、US3）。
// 依快照的 openQuestions 與 questionShapes（每題格數）畫出表單；只有收到成功回應才顯示「已送出」（FR-032）。
// 快照的 submissions.current.own 有本組已送出的題目時（例如同組另一台裝置送的），該題改為唯讀並顯示答案（US2）。
// 已關輪的輪次（submissions.published）對所有組公開，顯示在「已公開的作答」（US5）。

import { apiRequest } from "./api.js";
import { currentIdentity, onStudentSnapshot } from "./student.js";
import { describeSubmitError, el, renderAnswerForm, renderPublished } from "./submission.js";

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
  const code = result.error?.code;
  if (code === "STALE_ROUND") {
    // 舊頁面：提示並提供重新整理（US3-AS4）
    form.showError(result.error.message, { label: "重新整理", onClick: () => window.location.reload() });
    return;
  }
  if (code === "ROUND_CLOSED") {
    // 已截止或已關輪：停用全部作答表單（US3-AS2、US3-AS3）
    for (const other of forms.values()) if (!other.submitted) other.setDisabled(true);
  }
  form.showError(describeSubmitError(result.error));
}

function renderHistory(snapshot) {
  // US5：已關輪的輪次對所有組公開；進行中的輪次不在 published 裡（研究 R11）
  const published = snapshot.submissions?.published ?? [];
  const history = $("published-section");
  history.hidden = published.length === 0;
  if (!history.hidden) renderPublished($("published-list"), published);
}

function render(snapshot) {
  renderHistory(snapshot);
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
  markOwnSubmissions(snapshot);
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
