// 006 學生頁：本組幾何記號、扇形倒數與階段軌（只讀快照，不改任何狀態）。
// 扇形只是輔助：剩餘比例以「第一次看到這個截止時間時的剩餘秒數」為分母；
// 確切秒數仍由 001 的倒數文字顯示，截止判定以後端為準。

import { onStudentReset, onStudentSnapshot } from "./student.js";
import { glyph, renderStageTrack } from "./glyph.js";

const $ = (id) => document.getElementById(id);

let deadline = null;
let total = 0;
let timer = null;

function tick() {
  const pie = $("student-pie");
  if (!pie) return;
  if (!deadline) {
    pie.hidden = true;
    return;
  }
  const remaining = Math.max(0, (Date.parse(deadline) - Date.now()) / 1000);
  const share = total > 0 ? Math.min(1, remaining / total) : 0;
  pie.hidden = false;
  pie.style.setProperty("--left", `${(share * 100).toFixed(1)}%`);
  $("student-pie-number").textContent = String(Math.ceil(remaining));
  pie.classList.toggle("ending", remaining <= 10);
}

function setDeadline(value) {
  if (value === deadline) return;
  deadline = value;
  total = value ? Math.max(1, (Date.parse(value) - Date.now()) / 1000) : 0;
  clearInterval(timer);
  timer = value ? setInterval(tick, 250) : null;
  tick();
}

function render(snapshot) {
  renderStageTrack($("stage-track"), snapshot.stage);
  const mark = $("student-glyph");
  if (snapshot.ownGroup) mark.replaceChildren(glyph(snapshot.ownGroup.number, "lg"));
  else mark.replaceChildren();
  setDeadline(snapshot.stage === "ROUND_OPEN" ? snapshot.deadline : null);
}

onStudentSnapshot(render);
onStudentReset(() => {
  renderStageTrack($("stage-track"), null);
  $("student-glyph").replaceChildren();
  setDeadline(null);
});
