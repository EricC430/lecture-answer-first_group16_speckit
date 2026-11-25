// 006 老師頁：本輪總覽構成與頁首階段軌（只讀快照，不呼叫 API、不改任何狀態）。
// 每題的狀態由 001 的 stage／openQuestions、003 的 submissions.current、004 的 ranking 推得；
// 「已成功」只認已定案輪次的搶答成功者，與開輪面板判斷未成功題的方式一致。
// 所有文字一律 textContent（原則 V）。

import { onTeacherReset, onTeacherSnapshot, STAGE_LABELS } from "./teacher.js";
import { el } from "./submission.js";
import { glyph, renderStageTrack } from "./glyph.js";
import { startCountdown } from "./countdown.js";

const $ = (id) => document.getElementById(id);
const countdown = startCountdown(() => $("overview-countdown"));

const STAGE_HINTS = {
  PREPARING: "匯入學習單後按「開放加入」",
  JOINING: "學生可以加入；勾選題目後開輪",
  ROUND_OPEN: "",
  RESULT_PENDING: "可判錯、可撤銷；確認後定案",
  RESULT_FINAL: "可開下一輪，或結束活動",
  ENDED: "活動已結束，可寫回學習單",
  CANCELLED: "活動已取消",
};

/**
 * 每題目前的狀態。
 * @returns {Map<number, {state: string, group: number|null, round: number|null, submitted: number}>}
 */
export function questionStates(snapshot) {
  const states = new Map();
  for (const q of snapshot.questionNumbers ?? []) {
    states.set(q, { state: "idle", group: null, round: null, submitted: 0 });
  }
  const rounds = [...(snapshot.ranking?.rounds ?? [])].sort((a, b) => a.roundNumber - b.roundNumber);
  for (const round of rounds) {
    for (const question of round.questions) {
      const current = states.get(question.questionNumber);
      if (!current || current.state === "solved") continue;
      if (round.final) {
        states.set(question.questionNumber, {
          state: question.successGroup !== null ? "solved" : "missed",
          group: question.successGroup,
          round: round.roundNumber,
          submitted: question.entries.length,
        });
      } else {
        states.set(question.questionNumber, {
          state: "pending",
          group: question.successGroup,
          round: round.roundNumber,
          submitted: question.entries.length,
        });
      }
    }
  }
  if (snapshot.stage === "ROUND_OPEN") {
    const current = snapshot.submissions?.current;
    for (const q of snapshot.openQuestions) {
      const entries = current?.questions?.find((item) => item.questionNumber === q)?.entries ?? [];
      states.set(q, { state: "open", group: null, round: snapshot.roundNumber, submitted: entries.length });
    }
  }
  return states;
}

function tileCaption(info, shapes, q) {
  const blanks = Number(shapes?.[String(q)] ?? 0);
  const size = blanks ? `${blanks} 格` : "";
  switch (info.state) {
    case "solved":
      return `第 ${info.group} 組・第 ${info.round} 輪`;
    case "pending":
      return info.group !== null ? `第 ${info.group} 組・待定案` : "無人成功・待定案";
    case "open":
      return `作答中・${info.submitted} 組送出`;
    case "missed":
      return `第 ${info.round} 輪未成功`;
    default:
      return size ? `${size}・未出題` : "未出題";
  }
}

function renderTiles(snapshot, states) {
  const tiles = [];
  for (const [q, info] of states) {
    const tile = el("li", "", `ov-tile ov-${info.state}`);
    tile.append(el("span", `Q${q}`, "ov-qn"));
    const foot = el("span", "", "ov-foot");
    foot.append(el("span", tileCaption(info, snapshot.questionShapes, q)));
    if (info.group !== null && (info.state === "solved" || info.state === "pending")) {
      foot.append(glyph(info.group, "md"));
    }
    tile.append(foot);
    tiles.push(tile);
  }
  if (tiles.length === 0) tiles.push(el("li", "尚未匯入學習單", "ov-tile ov-empty"));
  $("overview-questions").replaceChildren(...tiles);
  return states;
}

function renderGroups(snapshot) {
  const groups = snapshot.groups ?? [];
  const max = Math.max(1, ...groups.map((g) => g.successCount));
  const bars = groups.map((group) => {
    const item = el("li", "", "ov-bar");
    const bar = el("span", "", "ov-bar-fill");
    bar.style.height = `${Math.max(4, Math.round((group.successCount / max) * 72))}px`;
    item.append(
      el("span", String(group.successCount), "ov-bar-n"),
      bar,
      glyph(group.number, "sm"),
      el("span", `第 ${group.number} 組`, "ov-bar-label"),
    );
    return item;
  });
  if (bars.length === 0) bars.push(el("li", "尚未有組別加入", "ov-bar-empty"));
  $("overview-groups").replaceChildren(...bars);
}

function render(snapshot) {
  renderStageTrack($("stage-track"), snapshot.stage);
  $("overview-section").hidden = false;
  const round = snapshot.roundNumber;
  $("overview-round-number").textContent = round ? String(round) : "0";
  $("overview-round-label").textContent = round
    ? `第 ${round} 輪・${snapshot.fairMode ? "公平模式" : "速度模式"}`
    : "尚未開輪";
  $("overview-stage").textContent = STAGE_LABELS[snapshot.stage] ?? snapshot.stage;
  const open = snapshot.stage === "ROUND_OPEN";
  $("overview-stage-hint").textContent = open
    ? snapshot.deadline ? "" : "本輪沒有倒數，由老師關輪"
    : STAGE_HINTS[snapshot.stage] ?? "";
  countdown.set(open ? snapshot.deadline : null);
  const states = renderTiles(snapshot, questionStates(snapshot));
  const total = states.size;
  const solved = [...states.values()].filter((info) => info.state === "solved").length;
  $("overview-score").textContent = `${solved}／${total}`;
  $("overview-score-label").textContent = total ? "題已有搶答成功者（已定案）" : "尚未匯入學習單";
  renderGroups(snapshot);
}

onTeacherSnapshot(render);
onTeacherReset(() => {
  renderStageTrack($("stage-track"), null);
  countdown.set(null);
  $("overview-section").hidden = true;
  $("overview-questions").replaceChildren();
  $("overview-groups").replaceChildren();
});
