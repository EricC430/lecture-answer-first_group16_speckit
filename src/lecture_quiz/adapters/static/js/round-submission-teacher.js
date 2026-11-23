// 003 老師頁：搶答中即時看板（US4）。依快照的 submissions.current 畫出每題 × 每組的提交。
// 活動還沒有格數資料時快照不帶 003 欄位，此區塊保持隱藏。

import { onTeacherSnapshot } from "./teacher.js";
import { renderBoard } from "./submission.js";

const $ = (id) => document.getElementById(id);

onTeacherSnapshot((snapshot) => {
  const section = $("round-submission-section");
  const submissions = snapshot.submissions;
  section.hidden = !submissions;
  if (!submissions) return;
  renderBoard($("submission-board"), submissions.current, snapshot.groups ?? [], snapshot.questionShapes ?? {});
});
