// 006 投影檢視白名單（contracts/projection-view.md；research.md R5；FR-031、FR-032）。
//
// 純函式：不讀 DOM、時間、網路或全域狀態，相同輸入一定得到相同輸出。
// 投影畫面收到的是「老師快照」（搶答中含各組答案），只能經由這個函式「複製」允許的欄位成新物件；
// 渲染程式只讀這裡的輸出。新增欄位前，先改契約與 tests/browser/test_ui_projection.py。

import { STAGE_LABELS } from "./stage-labels.js";

const MODE_BY_STAGE = {
  PREPARING: "lobby",
  JOINING: "lobby",
  ROUND_OPEN: "round",
  RESULT_PENDING: "results",
  RESULT_FINAL: "results",
  ENDED: "ended",
  CANCELLED: "cancelled",
};

function numbers(list) {
  return Array.isArray(list) ? list.filter((n) => Number.isInteger(n)) : [];
}

/** 目前輪的結果卡片：只取 004 學生版也有的欄位，答案與送出先後取自 003 已公開的資料。 */
function resultCards(snapshot, roundNumber) {
  const ranking = (snapshot.ranking?.rounds ?? []).find((r) => r.roundNumber === roundNumber);
  if (!ranking) return null;
  const published = (snapshot.submissions?.published ?? []).find((r) => r.roundNumber === roundNumber);
  const publishedQuestions = new Map((published?.questions ?? []).map((q) => [q.questionNumber, q]));
  const cards = (ranking.questions ?? []).map((question) => {
    const submitted = new Map(
      (publishedQuestions.get(question.questionNumber)?.entries ?? []).map((e) => [e.groupNumber, e]),
    );
    const entries = (question.entries ?? []).map((entry) => {
      const source = submitted.get(entry.groupNumber);
      return {
        groupNumber: entry.groupNumber,
        rank: entry.rank ?? null,
        displayStatus: entry.displayStatus,
        judgedWrong: Boolean(entry.judgedWrong),
        order: source?.order ?? null,
        answers: Array.isArray(source?.answers) ? source.answers.map(String) : [],
      };
    });
    entries.sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity));
    return {
      questionNumber: question.questionNumber,
      successGroup: question.successGroup ?? null,
      replacedGroup: question.replacedGroup ?? null,
      entries,
    };
  });
  return {
    results: cards,
    resultVersion: Number(ranking.resultVersion ?? 0),
    final: Boolean(ranking.final),
  };
}

/**
 * 把老師快照轉成投影檢視。
 * @param {object|null} snapshot 老師快照（001 sync-websocket；含 003 submissions、004 ranking）。
 * @param {boolean} hasTeacherToken 這個瀏覽器是否有該活動的老師 token。
 * @returns {object} ProjectionView（欄位見 contracts/projection-view.md）。
 */
export function toProjectionView(snapshot, hasTeacherToken) {
  if (!hasTeacherToken || !snapshot || !MODE_BY_STAGE[snapshot.stage]) {
    return { mode: "unavailable" };
  }
  const mode = MODE_BY_STAGE[snapshot.stage];
  const view = {
    mode,
    code: String(snapshot.code ?? ""),
    stageLabel: STAGE_LABELS[snapshot.stage] ?? "",
  };
  if (mode === "round" || mode === "results") {
    // 搶答中：只有輪次規則（題號、模式、截止時間）；不讀 snapshot.submissions（FR-032）
    view.roundNumber = Number.isInteger(snapshot.roundNumber) ? snapshot.roundNumber : null;
    view.questionNumbers = numbers(snapshot.openQuestions);
    view.fairMode = Boolean(snapshot.fairMode);
  }
  if (mode === "round") {
    view.deadline = typeof snapshot.deadline === "string" ? snapshot.deadline : null;
  }
  if (mode === "results") {
    const cards = resultCards(snapshot, view.roundNumber);
    if (cards) Object.assign(view, cards);
  }
  if (mode === "ended") {
    view.unsolved = numbers(snapshot.unsolvedQuestions);
  }
  return view;
}
