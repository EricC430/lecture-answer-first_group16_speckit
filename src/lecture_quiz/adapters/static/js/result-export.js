// 005 老師頁：寫回預覽、確認寫回。
// 所有後端與試算表來的文字（答案、原儲存格內容、組號、工作表標題）一律以 textContent 輸出
// （憲章原則 V、FR-032）；token 只在記憶體，不輸出到畫面或 console。

import { apiRequest, showError } from "./api.js";
import { onTeacherReset, onTeacherSnapshot } from "./teacher.js";

const $ = (id) => document.getElementById(id);

const IMPACT_LABELS = {
  EMPTY: "目標是空的",
  REPLACE: "將取代原有內容",
  SAME: "內容相同",
};

// 002 的 import.js 會在收到第一份快照後刪除網址上的 auth 參數；這裡在模組載入時就同步讀取
// 並記住（早於任何快照事件），授權完成（auth=ok）後自動重新預覽（FR-010）。
const initialAuth = new URLSearchParams(window.location.search).get("auth");

const AUTH_PROBLEMS = new Set(["NOT_AUTHORIZED", "AUTH_EXPIRED", "PERMISSION_DENIED"]);

const STATUS_LABELS = {
  IN_PROGRESS: "寫入中…",
  SUCCESS: "寫回成功",
  FAILED: "明確失敗（確認沒有任何儲存格被改動）",
  PENDING: "結果待確認（無法證實是否已寫入）",
};

const ui = {
  code: null,
  token: null,
  preview: null,
  attempt: null,
  summaryKey: null,
  busy: false,
  autoPreviewDone: false,
};

function call(method, path, body) {
  return apiRequest(
    method,
    `/api/activities/${encodeURIComponent(ui.code)}/export${path}`,
    { token: ui.token, body },
  );
}

function cell(text, className = "") {
  const td = document.createElement("td");
  if (className) td.className = className;
  td.textContent = text === null || text === undefined ? "" : String(text);
  return td;
}

function answerCell(text) {
  const td = document.createElement("td");
  const pre = document.createElement("pre");
  pre.className = "export-answer";
  pre.textContent = text;
  td.append(pre);
  return td;
}

function impactCell(item) {
  const label = IMPACT_LABELS[item.impact] ?? item.impact;
  const td = cell(item.impact === "REPLACE" ? `${label}：${item.currentDisplay ?? ""}` : label);
  if (item.impact === "REPLACE") td.className = "export-impact-replace";
  return td;
}

function renderStructure(structure) {
  const list = $("export-structure-list");
  list.replaceChildren();
  $("export-structure").hidden = structure.ok;
  if (structure.ok) return;
  for (const diff of structure.differences) {
    const item = document.createElement("li");
    const where = diff.row === null ? "" : `（第 ${diff.row} 列、${diff.col} 欄）`;
    item.textContent = `${diff.detail}${where}`;
    list.append(item);
  }
  if (structure.moreDifferences > 0) {
    const more = document.createElement("li");
    more.textContent = `另有 ${structure.moreDifferences} 項差異未列出`;
    list.append(more);
  }
}

function renderPreview(preview) {
  ui.preview = preview;
  renderStructure(preview.structure);
  $("export-preview").hidden = false;
  $("export-preview-summary").textContent =
    `工作表：${preview.sheetTitle}；共 ${preview.items.length} 個子空格會寫入。`;
  const body = $("export-preview-body");
  body.replaceChildren();
  for (const item of preview.items) {
    const row = document.createElement("tr");
    row.append(
      cell(`第 ${item.questionNumber} 題`),
      cell(item.subIndex === null ? "" : item.subIndex),
      cell(`第 ${item.groupNumber} 組`),
      answerCell(item.answer),
      cell(item.target),
      impactCell(item),
    );
    body.append(row);
  }
  $("export-unwritten").textContent = preview.unwrittenQuestions.length
    ? `不會寫入的題目：${preview.unwrittenQuestions.map((n) => `第 ${n} 題`).join("、")}`
    : "";
  updateControls();
}

// 寫回狀態面板：三種結果與進行中；核對結果逐格列出預期與目前內容（純文字）。
function renderAttempt(attempt) {
  ui.attempt = attempt;
  $("export-status").hidden = attempt === null;
  if (attempt === null) return;
  // 006：只供樣式讀取的狀態屬性（contracts/ui-dom.md），不影響寫回流程
  $("export-status-text").dataset.status = attempt.status;
  $("export-status-text").textContent =
    `第 ${attempt.attemptId} 次${attempt.kind === "RETRY" ? "（重試）" : ""}：${STATUS_LABELS[attempt.status] ?? attempt.status}`;
  $("export-status-counts").textContent =
    `共 ${attempt.totalCells} 格；已確認寫入 ${attempt.confirmedCells}、確認未寫入 ${attempt.notWrittenCells}、待確認 ${attempt.pendingCells}`;
  $("export-status-reason").textContent = attempt.reasonText ?? "";
  const checks = attempt.cellChecks ?? [];
  $("export-checks").hidden = checks.length === 0;
  const body = $("export-checks-body");
  body.replaceChildren();
  for (const check of checks) {
    const row = document.createElement("tr");
    row.append(
      cell(`第 ${check.questionNumber} 題`),
      cell(check.subIndex === null ? "" : check.subIndex),
      answerCell(check.expected),
      answerCell(check.currentDisplay),
      cell(check.matches ? "相符" : "不符"),
    );
    body.append(row);
  }
  if (attempt.differences && attempt.differences.length) {
    renderStructure({ ok: false, differences: attempt.differences, moreDifferences: 0 });
  }
  updateControls();
}

// 老師快照的 export 摘要（所有老師分頁即時更新）；細節（原因說明、逐格核對）用 X5 取得。
async function onSummary(summary) {
  if (!summary) return;
  const key = `${summary.attemptId}:${summary.status}:${summary.confirmedCells}:${summary.pendingCells}`;
  if (key === ui.summaryKey) return;
  ui.summaryKey = key;
  if (ui.attempt && ui.attempt.attemptId === summary.attemptId && ui.attempt.status === summary.status) {
    return; // 這個分頁剛自己操作過，內容已是最新
  }
  const result = await call("GET", "/writes/latest");
  if (result.ok && result.data.attempt) renderAttempt(result.data.attempt);
}

function clearPreview() {
  ui.preview = null;
  $("export-structure").hidden = true;
  $("export-preview").hidden = true;
  $("export-preview-body").replaceChildren();
  updateControls();
}

function updateControls() {
  const running = ui.attempt !== null && ui.attempt.status === "IN_PROGRESS";
  $("export-preview-button").disabled = ui.busy;
  $("export-confirm-button").disabled =
    ui.busy || running || !(ui.preview && ui.preview.canConfirm);
  $("export-recheck-button").disabled = ui.busy || running || ui.attempt === null;
  $("export-retry-button").disabled = ui.busy || running || ui.attempt === null;
}

async function guarded(fn) {
  if (ui.busy) return;
  ui.busy = true;
  updateControls();
  try {
    await fn();
  } finally {
    ui.busy = false;
    updateControls();
  }
}

// 授權或權限問題時顯示「重新授權」；任何階段（除已取消）都可使用（FR-010）。
function showAuthProblem(code) {
  $("export-reauth-button").hidden = !AUTH_PROBLEMS.has(code);
}

async function runReauth() {
  const result = await call("POST", "/authorization", {});
  if (!result.ok) {
    showError($("export-error"), result.error);
    return;
  }
  window.location.assign(result.data.authUrl); // 授權完成後導回 ?auth=ok|denied|error
}

async function runPreview() {
  showError($("export-error"), null);
  $("export-reauth-button").hidden = true;
  const result = await call("POST", "/preview", {});
  if (!result.ok) {
    clearPreview();
    showError($("export-error"), result.error);
    showAuthProblem(result.error.code);
    return;
  }
  renderPreview(result.data);
}

async function runConfirm() {
  if (!ui.preview) return;
  showError($("export-error"), null);
  const result = await call("POST", "/writes", { snapshotId: ui.preview.snapshotId });
  if (!result.ok) {
    if (result.error.code === "STALE_SNAPSHOT") clearPreview(); // 成果已更新，須重新預覽
    showError($("export-error"), result.error);
    showAuthProblem(result.error.code);
    return;
  }
  clearPreview(); // 確認只對這份預覽有效
  renderAttempt(result.data);
}

$("export-preview-button").addEventListener("click", () => guarded(runPreview));
$("export-confirm-button").addEventListener("click", () => guarded(runConfirm));
$("export-reauth-button").addEventListener("click", () => guarded(runReauth));

async function runAttemptAction(action) {
  if (!ui.attempt) return;
  showError($("export-error"), null);
  const result = await call("POST", `/writes/${ui.attempt.attemptId}/${action}`, {});
  if (!result.ok) {
    showError($("export-error"), result.error);
    showAuthProblem(result.error.code);
    return;
  }
  renderAttempt(result.data);
}

$("export-recheck-button").addEventListener("click", () => guarded(() => runAttemptAction("recheck")));
$("export-retry-button").addEventListener("click", () => guarded(() => runAttemptAction("retry")));

// CSV 下載需要 Authorization 標頭，所以用 fetch 取得 blob 再以暫時網址觸發下載；
// api.js 只處理 JSON，這裡不修改它。
async function runCsv() {
  showError($("export-error"), null);
  let response;
  try {
    response = await fetch(`/api/activities/${encodeURIComponent(ui.code)}/export/csv`, {
      headers: { Authorization: `Bearer ${ui.token}` },
    });
  } catch {
    showError($("export-error"), { message: "無法連線到伺服器，請確認後端仍在執行。" });
    return;
  }
  if (!response.ok) {
    let message = "下載失敗，請稍後再試。";
    try {
      message = String((await response.json()).error.message);
    } catch {
      // 保持通用訊息
    }
    showError($("export-error"), { message });
    return;
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `quiz-results-${ui.code}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

$("export-csv-button").addEventListener("click", () => guarded(runCsv));

let restored = false;
async function restoreLatest() {
  if (restored) return;
  restored = true; // 頁面重新整理後恢復最近一次寫回
  const result = await call("GET", "/writes/latest");
  if (result.ok && result.data.attempt) renderAttempt(result.data.attempt);
}

onTeacherSnapshot((snapshot, state) => {
  ui.code = state.code;
  ui.token = state.token;
  // 已取消的活動不提供寫回與 CSV（alignment 2026-11-23）
  $("export-section").hidden = snapshot.stage === "CANCELLED";
  if (snapshot.stage !== "CANCELLED") {
    restoreLatest();
    onSummary(snapshot.export);
  }
  updateControls();
  if (initialAuth === "ok" && !ui.autoPreviewDone && snapshot.stage !== "CANCELLED") {
    ui.autoPreviewDone = true; // 授權完成後自動回到預覽，不需要重新匯入
    guarded(runPreview);
  }
});

// 換活動時清掉上一個活動的預覽、寫回狀態與核對表（不能把舊活動的答案留在新活動畫面）
onTeacherReset(() => {
  restored = false;
  ui.code = null;
  ui.token = null;
  ui.preview = null;
  ui.attempt = null;
  ui.summaryKey = null;
  ui.busy = false;
  showError($("export-error"), null);
  for (const id of ["export-structure", "export-status", "export-checks", "export-preview", "export-reauth-button"]) {
    $(id).hidden = true;
  }
  for (const id of ["export-structure-list", "export-checks-body", "export-preview-body"]) {
    $(id).replaceChildren();
  }
  for (const id of ["export-preview-summary", "export-unwritten", "export-status-text", "export-status-counts", "export-status-reason"]) {
    $(id).textContent = "";
  }
  updateControls();
});
