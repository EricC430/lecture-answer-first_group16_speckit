// 004 老師頁：每輪每題的候選情況（名次、組號、答案、處理當下成功次數、理由、顯示狀態）。
// 答案與送出時間由 003 的 submissions.published 以（輪次、題號、組號）合併。
// 所有文字一律 textContent（FR-028）；活動階段顯示「結果未定案／結果已定案」（FR-031）。

import { onTeacherSnapshot, STAGE_LABELS } from "./teacher.js";
import { el } from "./submission.js";
import { REASON_LABELS, STATUS_LABELS, acceptRankingRounds, answerOf } from "./ranking-common.js";

const $ = (id) => document.getElementById(id);

function entryRow(snapshot, round, question, entry) {
  const row = el("li", "", `ranking-entry status-${entry.displayStatus.toLowerCase()}`);
  const rank = entry.rank === null ? "—" : `第 ${entry.rank} 名`;
  row.append(el("strong", `${rank}・第 ${entry.groupNumber} 組・${STATUS_LABELS[entry.displayStatus]}`));
  const answer = answerOf(snapshot, round.roundNumber, question.questionNumber, entry.groupNumber);
  if (answer) row.append(el("pre", answer, "ranking-answer"));
  if (round.fairMode && entry.countAtProcessing !== null) {
    row.append(el("span", `處理當下成功次數 ${entry.countAtProcessing}`, "muted"));
  }
  if (entry.reason) row.append(el("span", `理由：${REASON_LABELS[entry.reason]}`, "muted"));
  return row;
}

function questionBlock(snapshot, round, question) {
  const block = el("div", "", "ranking-question");
  block.append(el("h4", `第 ${question.questionNumber} 題`));
  if (question.successGroup === null) block.append(el("p", "未成功", "muted"));
  const list = el("ol", "", "ranking-entries");
  for (const entry of question.entries) list.append(entryRow(snapshot, round, question, entry));
  block.append(list);
  return block;
}

function render(snapshot) {
  const section = $("ranking-review-section");
  const rounds = snapshot.ranking?.rounds ?? [];
  section.hidden = rounds.length === 0;
  if (rounds.length === 0) return;
  if (!acceptRankingRounds(rounds)) return; // 舊版本不覆蓋新結果（FR-016）
  const container = $("ranking-review-list");
  container.replaceChildren();
  for (const round of [...rounds].reverse()) {
    const wrapper = el("div", "", "ranking-round");
    const stage = round.final ? STAGE_LABELS.RESULT_FINAL : STAGE_LABELS.RESULT_PENDING;
    wrapper.append(
      el("h3", `第 ${round.roundNumber} 輪（${round.fairMode ? "公平模式" : "速度模式"}）・${stage}・結果版本 ${round.resultVersion}`),
    );
    if (round.fairMode && round.groupCounts) {
      const counts = Object.entries(round.groupCounts)
        .map(([group, count]) => `第 ${group} 組 ${count} 次`)
        .join("、");
      wrapper.append(el("p", `處理完本輪後各組暫算成功次數：${counts}`, "muted"));
    }
    for (const question of round.questions) wrapper.append(questionBlock(snapshot, round, question));
    container.append(wrapper);
  }
}

onTeacherSnapshot(render);
