// 004 學生頁：本組每題的結果狀態（US7 再依 FR-036 補上目前的搶答成功者與剛被判錯的前一組）。
// 所有文字一律 textContent（FR-028）。

import { onStudentSnapshot } from "./student.js";
import { el } from "./submission.js";
import { STATUS_LABELS, acceptRankingRounds } from "./ranking-common.js";

const $ = (id) => document.getElementById(id);

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
    wrapper.append(el("h3", `第 ${round.roundNumber} 輪`));
    const list = el("ul", "", "ranking-own");
    for (const question of round.questions) {
      const mine = question.entries.find((e) => e.groupNumber === own);
      if (mine) list.append(el("li", `第 ${question.questionNumber} 題：${STATUS_LABELS[mine.displayStatus]}`));
      else if (question.successGroup === null) list.append(el("li", `第 ${question.questionNumber} 題：未成功`));
    }
    wrapper.append(list);
    container.append(wrapper);
  }
}

onStudentSnapshot(render);
