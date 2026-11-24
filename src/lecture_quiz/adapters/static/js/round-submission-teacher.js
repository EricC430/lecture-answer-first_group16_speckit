// 003 老師頁：搶答中即時看板（US4）與已公開輪次（US5）。依快照的 submissions 畫出每題 × 每組的提交。
// 活動還沒有格數資料時快照不帶 003 欄位，此區塊保持隱藏。

import { onTeacherSnapshot } from "./teacher.js";
import { renderBoard, renderPublished } from "./submission.js";

const $ = (id) => document.getElementById(id);

onTeacherSnapshot((snapshot) => {
  const section = $("round-submission-section");
  const submissions = snapshot.submissions;
  const history = $("published-section");
  section.hidden = !submissions;
  history.hidden = !submissions?.published?.length;
  if (!submissions) return;
  renderBoard($("submission-board"), submissions.current, snapshot.groups ?? [], snapshot.questionShapes ?? {});
  // US5：已關輪的輪次（含本輪關輪後到定案前）
  if (!history.hidden) renderPublished($("published-list"), submissions.published);
});
