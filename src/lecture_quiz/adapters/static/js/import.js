// 002 老師頁：Google 授權、Picker 選檔、選工作表、匯入預覽與錯誤清單。
// 所有後端與試算表來的文字一律以 textContent 輸出（原則 V、FR-022）；
// token 只在後端，這裡只拿得到短效的 Picker access token，且不輸出到畫面或 console。
// 單一工作表是否自動選用由後端決定（inspect 回傳 autoSelectSheetId），前端不自己數工作表。

import { apiRequest, showError } from "./api.js";
import { onTeacherSnapshot } from "./teacher.js";

const $ = (id) => document.getElementById(id);
const PICKER_SCRIPT = "https://apis.google.com/js/api.js";
const SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet";

const KIND_LABELS = {
  MISSING_HEADER_NUMBER: "找不到「題號」表頭",
  MISSING_HEADER_ANSWER: "找不到「作答」表頭",
  AMBIGUOUS_HEADER: "表頭有多組或不在同一列",
  NON_NUMERIC_NUMBER: "題號不是正整數",
  NUMBER_GAP: "題號跳號或不是從 1 開始",
  NON_ADJACENT_DUPLICATE: "同一題號出現在不相鄰的位置",
  SUB_INDEX_MISSING: "子編號缺漏",
  SUB_INDEX_DUPLICATE: "子編號重複",
  ORPHAN_SUB_BLANK: "子空格沒有所屬題號",
  MISSING_ANSWER_CELL: "找不到作答格",
  TARGET_OVERLAP: "兩個空格指向同一格",
};

const ui = { code: null, token: null, locked: false, busy: false, authResult: null };

function base() {
  return `/api/activities/${encodeURIComponent(ui.code)}/import`;
}

function call(method, path, body) {
  return apiRequest(method, `${base()}${path}`, { token: ui.token, body });
}

function setStatus(text) {
  $("import-status").textContent = text;
}

// 只收起錯誤清單；上一次成功的預覽維持顯示（驗證失敗時既有結果完全不變，FR-016）。
function clearResults() {
  $("import-issues").hidden = true;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text === null || text === undefined ? "" : String(text);
  return td;
}

function renderPreview(result) {
  $("import-summary").textContent = `${result.totalQuestions} 題、${result.totalBlanks} 格` +
    (result.sheetTitle ? `（工作表：${result.sheetTitle}）` : "");
  const body = $("import-preview-body");
  body.replaceChildren();
  for (const number of result.questionNumbers) {
    const row = document.createElement("tr");
    row.append(cell(`第 ${number} 題`), cell(result.blanksPerQuestion[String(number)]));
    body.append(row);
  }
  $("import-preview").hidden = false;
}

function renderIssues(issues) {
  const body = $("import-issues-body");
  body.replaceChildren();
  for (const issue of issues) {
    const row = document.createElement("tr");
    row.append(
      cell(issue.row === null ? "—" : issue.row),
      cell(issue.col === null ? "—" : issue.col),
      cell(KIND_LABELS[issue.kind] ?? issue.kind),
      cell(issue.quoted ?? ""),
      cell(issue.hint),
    );
    body.append(row);
  }
  $("import-issues").hidden = false;
}

function updateControls() {
  const disabled = ui.locked || ui.busy;
  for (const id of ["import-start", "import-reauth", "import-run"]) $(id).disabled = disabled;
  for (const button of $("import-sheet-list").querySelectorAll("button")) button.disabled = disabled;
}

function showFailure(result) {
  showError($("import-error"), result.error);
  const code = result.error?.code;
  $("import-reauth").hidden = !(code === "NOT_AUTHORIZED" || code === "AUTH_EXPIRED");
  if (code === "VALIDATION_FAILED" && Array.isArray(result.data?.error?.issues)) {
    renderIssues(result.data.error.issues);
  }
}

async function guarded(task) {
  if (ui.busy) return;
  ui.busy = true;
  updateControls();
  showError($("import-error"), null);
  try {
    await task();
  } finally {
    ui.busy = false;
    updateControls();
  }
}

// ── 授權 ──

async function startAuthorization() {
  const result = await call("POST", "/auth/start", {});
  if (!result.ok) return showFailure(result);
  setStatus("正在前往 Google 授權…");
  window.location.assign(result.data.authUrl); // 離開本頁；授權完成後導回 ?auth=ok|denied|error
}

function showAuthResult(value) {
  const messages = {
    ok: "已授權。請按「匯入學習單」選擇試算表。",
    denied: "尚未授權、未匯入任何題目。需要匯入時請重新授權。",
    error: "授權沒有成功，未匯入任何題目。請重新授權。",
  };
  setStatus(messages[value] ?? "");
  $("import-reauth").hidden = value === "ok" || !(value in messages);
}

// ── Picker ──

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve();
    const script = document.createElement("script");
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("load"));
    document.head.append(script);
  });
}

async function loadPicker() {
  await loadScript(PICKER_SCRIPT);
  await new Promise((resolve) => window.gapi.load("picker", { callback: resolve }));
}

function pickSpreadsheet(config) {
  return new Promise((resolve) => {
    const view = new window.google.picker.DocsView(window.google.picker.ViewId.SPREADSHEETS)
      .setMimeTypes(SPREADSHEET_MIME);
    const picker = new window.google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(config.accessToken)
      .setDeveloperKey(config.apiKey)
      .setAppId(config.appId)
      .setCallback((data) => {
        const action = data[window.google.picker.Response.ACTION];
        if (action === window.google.picker.Action.PICKED) {
          resolve(data[window.google.picker.Response.DOCUMENTS][0].id);
        } else if (action === window.google.picker.Action.CANCEL) {
          resolve(null); // 取消選檔：維持原狀，不呼叫任何端點
        }
      })
      .build();
    picker.setVisible(true);
  });
}

async function chooseSource() {
  clearResults();
  const status = await call("GET", "/auth/status");
  if (!status.ok) return showFailure(status);
  if (!status.data.authorized) return startAuthorization();
  const config = await call("GET", "/picker-config");
  if (!config.ok) return showFailure(config);
  try {
    await loadPicker();
  } catch {
    return showFailure({ error: { code: "PICKER_FAILED", message: "無法載入 Google 選檔畫面，請檢查網路後再試。" } });
  }
  const spreadsheetId = await pickSpreadsheet(config.data);
  if (spreadsheetId === null) {
    setStatus("已取消選檔，維持原狀。");
    return;
  }
  const inspected = await call("POST", "/source/inspect", { spreadsheetId });
  if (!inspected.ok) return showFailure(inspected);
  const { sheets, autoSelectSheetId, title } = inspected.data;
  if (autoSelectSheetId !== null) {
    $("import-sheet-choice").hidden = true;
    const sheet = sheets.find((s) => s.sheetId === autoSelectSheetId);
    return selectSource(spreadsheetId, autoSelectSheetId, title, sheet ? sheet.title : "");
  }
  showSheetChoices(spreadsheetId, title, sheets);
}

function showSheetChoices(spreadsheetId, title, sheets) {
  $("import-source").hidden = true;
  $("import-run").hidden = true;
  const list = $("import-sheet-list");
  list.replaceChildren();
  for (const sheet of sheets) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = sheet.title;
    button.addEventListener("click", () =>
      guarded(() => selectSource(spreadsheetId, sheet.sheetId, title, sheet.title)));
    list.append(button);
  }
  $("import-sheet-choice").hidden = false;
  setStatus("請選擇要匯入的工作表。");
}

async function selectSource(spreadsheetId, sheetId, spreadsheetTitle) {
  const selected = await call("PUT", "/source", { spreadsheetId, sheetId });
  if (!selected.ok) return showFailure(selected);
  $("import-sheet-choice").hidden = true;
  $("import-source-name").textContent = `${spreadsheetTitle}／${selected.data.sheetTitle}`;
  $("import-source").hidden = false;
  $("import-run").hidden = false;
  setStatus("已選定來源，確認後按「確認匯入」。");
}

// ── 匯入與恢復 ──

async function runImport() {
  clearResults();
  const result = await call("POST", "", {});
  if (!result.ok) return showFailure(result);
  $("import-reauth").hidden = true;
  setStatus("匯入完成。");
  renderPreview(result.data);
}

async function restorePreview() {
  const result = await call("GET", "");
  if (result.ok && result.data.imported) renderPreview(result.data);
}

// ── 階段鎖定（001 快照）──

function applyStage(snapshot) {
  const open = snapshot.stage === "PREPARING" || snapshot.stage === "JOINING";
  ui.locked = !open;
  if (!open) {
    setStatus(snapshot.stage === "CANCELLED" ? "活動已取消。" : "搶答已開始，題目不可更動。");
  }
  updateControls();
}

let started = false;

onTeacherSnapshot((snapshot, state) => {
  ui.code = state.code;
  ui.token = state.token;
  $("import-section").hidden = false;
  applyStage(snapshot);
  if (started) return;
  started = true;
  const params = new URLSearchParams(window.location.search);
  const auth = params.get("auth");
  if (auth) {
    params.delete("auth");
    const query = params.toString();
    history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
    showAuthResult(auth);
  }
  restorePreview();
});

$("import-start").addEventListener("click", () => guarded(chooseSource));
$("import-reauth").addEventListener("click", () => guarded(startAuthorization));
$("import-run").addEventListener("click", () => guarded(runImport));
