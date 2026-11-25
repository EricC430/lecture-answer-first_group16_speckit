// 004 學生頁（FR-036、FR-037）：每題只顯示 ① 本組的狀態 ② 目前的搶答成功者
// ③ 剛被判錯的前一組（有遞補者時一起顯示）。不逐組列出其他候選，不顯示理由與他組次數。
// 答案由 003 的 submissions.published 以（輪次、題號、組號）合併；所有文字用 textContent。

import { onStudentReset, onStudentSnapshot } from "./student.js";
import { el } from "./submission.js";
import { glyph } from "./glyph.js";
import { STATUS_LABELS, acceptRankingRounds, acceptRankingVersion, answerOf, resetRankingVersions } from "./ranking-common.js";

export { acceptRankingVersion };

const $ = (id) => document.getElementById(id);

function line(snapshot, round, question, entry, prefix) {
  const item = el("li", "", `ranking-line status-${entry.displayStatus.toLowerCase()}`);
  item.append(glyph(entry.groupNumber)); // 006：組別記號（展示用）
  item.append(el("strong", `${prefix}第 ${entry.groupNumber} 組：${STATUS_LABELS[entry.displayStatus]}`));
  const answer = answerOf(snapshot, round.roundNumber, question.questionNumber, entry.groupNumber);
  if (answer) item.append(el("pre", answer, "ranking-answer"));
  return item;
}

function questionBlock(snapshot, round, question, own) {
  const block = el("div", "", "ranking-question");
  const updated = round.affectedQuestions.includes(question.questionNumber) ? "（結果已更新）" : "";
  block.append(el("h4", `第 ${question.questionNumber} 題${updated}`));
  const byGroup = new Map(question.entries.map((e) => [e.groupNumber, e]));
  const list = el("ul", "", "ranking-own");
  const shown = new Set();
  const show = (group, prefix) => {
    const entry = byGroup.get(group);
    if (!entry || shown.has(group)) return;
    shown.add(group);
    // 本組剛好是搶答成功者或被判錯者時，標出「（本組）」，學生才知道哪一行是自己
    list.append(line(snapshot, round, question, entry, group === own ? `${prefix}（本組）` : prefix));
  };
  if (question.replacedGroup !== null) show(question.replacedGroup, "");
  if (question.successGroup !== null) show(question.successGroup, "目前搶答成功者：");
  else list.append(el("li", "未成功", "ranking-line"));
  show(own, "本組：");
  block.append(list);
  return block;
}

function render(snapshot) {
  const section = $("ranking-review-student-section");
  const rounds = snapshot.ranking?.rounds ?? [];
  section.hidden = rounds.length === 0;
  if (rounds.length === 0) return;
  if (!acceptRankingRounds(rounds)) return; // 舊版本不覆蓋新結果（FR-016）
  const own = snapshot.ownGroup?.number;
  const container = $("ranking-review-student-list");
  container.replaceChildren();
  for (const round of [...rounds].reverse()) {
    const wrapper = el("div", "", "ranking-round");
    wrapper.append(el("h3", `第 ${round.roundNumber} 輪${round.final ? "（結果已定案）" : "（結果未定案）"}`));
    // 每一題都要畫出來：沒有搶答成功者的題（沒人提交、或唯一的提交被判錯）顯示「未成功」，
    // 沒有提交的組也要看到（spec US7-AS9）。他組的資料由後端的學生版 JSON 限縮，這裡不過濾。
    for (const question of round.questions) {
      wrapper.append(questionBlock(snapshot, round, question, own));
    }
    container.append(wrapper);
  }
}

onStudentSnapshot(render);
onStudentReset(() => {
  resetRankingVersions();
  $("ranking-review-student-list").replaceChildren();
});
