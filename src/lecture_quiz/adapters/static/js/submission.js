// 003 多題搶答：作答表單與提交顯示的共用函式（老師頁與學生頁共用）。
// 所有不可信文字（答案、錯誤訊息）一律用 textContent／createElement，不以 HTML 字串插入（原則 V、FR-031）。

export const MAX_ANSWER_CHARS = 500; // 只是提示；後端才是準（Q-20）

/** 建立元素並設定純文字內容。 */
export function el(tag, text = "", className = "") {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

/** 把 ISO 時間轉成「時:分:秒.毫秒」顯示。 */
export function formatTime(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${pad(date.getMilliseconds(), 3)}`;
}

/** 送出失敗時給學生的訊息；網路錯誤一律視為「結果未確認」（FR-032）。 */
export function describeSubmitError(error) {
  if (!error || error.code === "NETWORK_ERROR" || error.code.startsWith("HTTP_")) {
    return "送出結果未確認，請重試。";
  }
  return error.message;
}

/** 以清單顯示各格答案（純文字，保留換行）。 */
export function renderAnswers(answers) {
  const list = el("ol", "", "answer-list");
  for (const answer of answers) list.append(el("li", answer, "answer-text"));
  return list;
}

/**
 * 建立一題的作答表單（每格一個 textarea）。
 * @param {{questionNumber: number, blanks: number, onSubmit: (answers: string[]) => void}} options
 */
export function renderAnswerForm({ questionNumber, blanks, onSubmit }) {
  const form = el("form", "", "answer-form");
  form.noValidate = true;
  form.append(el("h4", blanks > 1 ? `第 ${questionNumber} 題（${blanks} 格）` : `第 ${questionNumber} 題`));
  const inputs = [];
  for (let i = 1; i <= blanks; i += 1) {
    const label = el("label", blanks > 1 ? `第 ${i} 格：` : "答案：");
    const input = el("textarea");
    input.rows = 2;
    input.maxLength = MAX_ANSWER_CHARS;
    label.append(input);
    form.append(label);
    inputs.push(input);
  }
  const button = el("button", "送出這一題");
  button.type = "submit";
  const status = el("p", "", "submit-status");
  status.setAttribute("role", "status");
  const result = el("div", "", "submit-result");
  form.append(button, status, result);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (button.disabled) return;
    onSubmit(inputs.map((input) => input.value));
  });

  // 已送出或被停用（截止、關輪）後為真；送出中結束時不能把按鈕重新啟用（PR #16 審查第 4 項）
  let locked = false;

  function lock() {
    locked = true;
    for (const input of inputs) input.disabled = true;
    button.hidden = true;
  }

  return {
    element: form,
    setBusy(busy) {
      button.disabled = busy || locked;
      if (busy) {
        status.textContent = "送出中…";
        status.className = "submit-status";
      }
    },
    setDisabled(disabled) {
      locked = disabled;
      button.disabled = disabled;
      for (const input of inputs) input.disabled = disabled;
    },
    showError(message, action = null) {
      status.textContent = message;
      status.className = "submit-status error-message";
      if (action) {
        const button = el("button", action.label, "secondary");
        button.type = "button";
        button.addEventListener("click", action.onClick);
        status.append(" ", button);
      }
    },
    showSubmitted(submission, message = "已送出") {
      lock();
      status.textContent = `${message}（${formatTime(submission.receivedAt)}）`;
      status.className = "submit-status";
      result.replaceChildren(renderAnswers(submission.answers));
    },
    get submitted() {
      return button.hidden;
    },
  };
}

/**
 * 老師看板：本輪每題 × 每組的提交（US4）。已送出顯示答案、接收時間與送出先後；
 * 未送出顯示「尚未送出」。`order` 是送出先後，不是順位（Q-21）。全部 textContent。
 * @param {HTMLElement} container
 * @param {{roundNumber: number, questions: Array<{questionNumber: number, entries: Array}>}|null} current
 * @param {Array<{number: number}>} groups 老師快照的 groups
 * @param {Object<string, number>} questionShapes
 */
export function renderBoard(container, current, groups, questionShapes) {
  if (!current) {
    container.replaceChildren(el("p", "目前沒有進行中的輪次。", "muted"));
    return;
  }
  const numbers = new Set(groups.map((g) => g.number));
  for (const q of current.questions) for (const e of q.entries) numbers.add(e.groupNumber);
  const columns = [...numbers].sort((a, b) => a - b);
  const table = el("table", "", "submission-board");
  const caption = el("caption", `第 ${current.roundNumber} 輪作答（依送出先後，不是順位）`);
  const head = el("tr");
  head.append(el("th", "題號"));
  for (const n of columns) head.append(el("th", `第 ${n} 組`));
  table.append(caption, head);
  for (const q of current.questions) {
    const row = el("tr");
    const blanks = questionShapes?.[String(q.questionNumber)];
    row.append(el("th", blanks > 1 ? `第 ${q.questionNumber} 題（${blanks} 格）` : `第 ${q.questionNumber} 題`));
    const byGroup = new Map(q.entries.map((e) => [e.groupNumber, e]));
    for (const n of columns) {
      const cell = el("td");
      const entry = byGroup.get(n);
      if (entry) {
        cell.append(
          el("p", `第 ${entry.order} 個送出・${formatTime(entry.receivedAt)}`, "muted"),
          renderAnswers(entry.answers),
        );
      } else {
        cell.append(el("p", "尚未送出", "muted"));
      }
      row.append(cell);
    }
    table.append(row);
  }
  container.replaceChildren(table);
}

/**
 * 已公開輪次（US5，研究 R11）：每輪每題列出各組答案與送出先後。
 * `noSubmission` 顯示「未成功」；`judgedWrong` 為真顯示「答錯」（Q-26，由 004 提供）。
 * 「搶答失敗」需要 004 的勝者資訊，004 完成前不顯示，未被判錯的候選只列出先後。
 * 全部 textContent。
 * @param {HTMLElement} container
 * @param {Array<{roundNumber: number, questions: Array<{questionNumber: number, noSubmission: boolean, entries: Array}>}>} published
 */
export function renderPublished(container, published) {
  if (!published || published.length === 0) {
    container.replaceChildren(el("p", "還沒有已公開的輪次。", "muted"));
    return;
  }
  const blocks = published.map((round) => {
    const block = el("section", "", "published-round");
    block.append(el("h3", `第 ${round.roundNumber} 輪（依送出先後，不是順位）`));
    const list = el("ul", "", "published-questions");
    for (const q of round.questions) {
      const item = el("li");
      item.append(el("strong", `第 ${q.questionNumber} 題`));
      if (q.noSubmission) {
        item.append(el("p", "未成功（沒有組別送出）", "muted"));
      } else {
        const entries = el("ol", "", "published-entries");
        for (const entry of q.entries) {
          const row = el("li");
          const label = `第 ${entry.groupNumber} 組・第 ${entry.order} 個送出・${formatTime(entry.receivedAt)}`;
          row.append(el("p", label, "muted"));
          if (entry.judgedWrong === true) row.append(el("p", "答錯", "error-message"));
          row.append(renderAnswers(entry.answers));
          entries.append(row);
        }
        item.append(entries);
      }
      list.append(item);
    }
    block.append(list);
    return block;
  });
  container.replaceChildren(...blocks);
}
