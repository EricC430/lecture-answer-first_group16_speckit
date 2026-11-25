// 004 老師頁與學生頁共用：狀態與理由的顯示文字、與 003 答案的合併、結果版本守衛。
// 所有不可信文字（組號、答案）由呼叫端以 textContent 輸出（原則 V）。

export const STATUS_LABELS = {
  SUCCESS: "搶答成功",
  CORRECT: "搶答正確",
  WRONG: "答錯",
  FAILED: "搶答失敗",
};

export const REASON_LABELS = {
  SOLE_CANDIDATE: "唯一候選",
  EARLIER_SUBMISSION: "提交較早",
  FEWER_SUCCESSES: "成功次數較少",
  BACKEND_ORDER: "以後端接收先後決定",
};

/** 某組在某輪某題的答案原文（以換行連接各格）；003 沒有資料時回傳空字串。 */
export function answerOf(snapshot, roundNumber, questionNumber, groupNumber) {
  const rounds = snapshot.submissions?.published ?? [];
  const round = rounds.find((r) => r.roundNumber === roundNumber);
  const question = round?.questions?.find((q) => q.questionNumber === questionNumber);
  const entry = question?.entries?.find((e) => e.groupNumber === groupNumber);
  return entry ? entry.answers.join("\n") : "";
}

const seenVersions = new Map();

/**
 * 結果版本守衛（FR-016）：同一輪收到較小的 resultVersion 時回傳 false，表示這份快照
 * 對 004 區塊是舊的，不要用它覆蓋較新的畫面；其他區塊照常更新。
 */
export function acceptRankingVersion(roundNumber, resultVersion) {
  const previous = seenVersions.get(roundNumber) ?? 0;
  if (resultVersion < previous) return false;
  seenVersions.set(roundNumber, resultVersion);
  return true;
}

/** 換活動時清掉已看過的版本，否則新活動的輪次會被舊活動的版本號擋下。 */
export function resetRankingVersions() {
  seenVersions.clear();
}

/** 快照的所有輪次是否都不比已看過的版本舊。 */
export function acceptRankingRounds(rounds) {
  let ok = true;
  for (const round of rounds) {
    if (!acceptRankingVersion(round.roundNumber, round.resultVersion)) ok = false;
  }
  return ok;
}
