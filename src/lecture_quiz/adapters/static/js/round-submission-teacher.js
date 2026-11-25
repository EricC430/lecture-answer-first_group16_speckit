// 003 老師頁：搶答中即時看板（US4）與已公開輪次（US5）。依快照的 submissions 畫出每題 × 每組的提交。
// 活動還沒有格數資料時快照不帶 003 欄位，此區塊保持隱藏。

import { onTeacherReset, onTeacherSnapshot } from "./teacher.js";
import { renderBoard, renderPublished } from "./submission.js";

const $ = (id) => document.getElementById(id);

onTeacherSnapshot((snapshot) => {
  const section = $("round-submission-section");
  const submissions = snapshot.submissions;
  const history = $("published-section");
  section.hidden = !submissions;
  // 004 已顯示結果的輪次（含答案與判錯狀態）不在這裡重複列出答案（FR-035）；
  // 判錯標記以 004 的 ranking 為準，不使用 003 的佔位 judgedWrong。
  const ranked = new Set((snapshot.ranking?.rounds ?? []).map((r) => r.roundNumber));
  const unranked = (submissions?.published ?? []).filter((r) => !ranked.has(r.roundNumber));
  history.hidden = unranked.length === 0;
  if (!submissions) return;
  renderBoard($("submission-board"), submissions.current, snapshot.groups ?? [], snapshot.questionShapes ?? {});
  // US5：已關輪的輪次（含本輪關輪後到定案前）
  if (!history.hidden) renderPublished($("published-list"), unranked);
});

onTeacherReset(() => {
  $("submission-board").replaceChildren();
  $("published-list").replaceChildren();
});
