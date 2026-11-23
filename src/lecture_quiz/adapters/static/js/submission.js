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

  function lock() {
    for (const input of inputs) input.disabled = true;
    button.hidden = true;
  }

  return {
    element: form,
    setBusy(busy) {
      button.disabled = busy;
      if (busy) {
        status.textContent = "送出中…";
        status.className = "submit-status";
      }
    },
    setDisabled(disabled) {
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
