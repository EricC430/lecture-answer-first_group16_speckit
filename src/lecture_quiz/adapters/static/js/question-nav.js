// 006 學生頁：作答區上方的固定資訊列與題號導覽（spec US2-AS2、US2-AS7；FR-008、FR-008a）。
// - 只觀察本頁已畫出的 DOM（001 的本組資訊、倒數，003 的本組作答卡片），不連線、不讀快照，
//   所以不可能出現他組資訊。
// - 資訊列是 001 元素文字的唯讀鏡像（原元素不動，contracts/ui-dom.md），對輔助技術隱藏以免重複朗讀。
// - 題號導覽只在本輪開放題數 ≥ 2 時出現；狀態取自卡片的 data-submit-state（submission.js）。

const $ = (id) => document.getElementById(id);

const STATE_TEXT = {
  idle: "未送出",
  error: "未送出",
  busy: "送出中",
  done: "已送出",
};

function text(id) {
  return ($(id)?.textContent ?? "").trim();
}

function renderStatus() {
  const group = $("answer-group");
  const stage = $("answer-stage");
  const countdown = $("answer-countdown");
  if (!group || !stage || !countdown) return;
  group.textContent = text("student-group");
  stage.textContent = text("student-stage");
  const source = $("student-countdown");
  const remaining = text("student-countdown");
  countdown.textContent = remaining || (text("round-deadline-note").includes("由老師結束") ? "由老師結束" : "");
  countdown.toggleAttribute("data-urgent", Boolean(source?.hasAttribute("data-urgent")));
}

function renderNav() {
  const nav = $("question-nav");
  const list = $("answer-forms");
  if (!nav || !list) return;
  const forms = [...list.querySelectorAll("form[data-question]")];
  nav.hidden = forms.length < 2;
  const links = forms.map((form) => {
    const number = form.dataset.question;
    const heading = form.querySelector("h4");
    if (heading && heading.id !== `q-heading-${number}`) {
      heading.id = `q-heading-${number}`;
      heading.tabIndex = -1;
    }
    const state = form.dataset.submitState ?? "idle";
    const link = document.createElement("a");
    link.href = `#q-heading-${number}`;
    link.dataset.question = number;
    link.dataset.state = state;
    link.textContent = `第 ${number} 題・${STATE_TEXT[state] ?? "未送出"}`;
    return link;
  });
  const signature = links.map((a) => a.textContent).join("|");
  if (nav.dataset.signature === signature) return;
  nav.dataset.signature = signature;
  nav.replaceChildren(...links);
}

function onNavClick(event) {
  const link = event.target.closest("a[data-question]");
  if (!link) return;
  event.preventDefault();
  const heading = $(`q-heading-${link.dataset.question}`);
  if (!heading) return;
  heading.scrollIntoView({ block: "start", behavior: "auto" });
  heading.focus({ preventScroll: true });
}

function start() {
  const forms = $("answer-forms");
  if (!forms || !$("question-nav")) return;
  $("question-nav").addEventListener("click", onNavClick);
  new MutationObserver(renderNav).observe(forms, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["data-submit-state", "data-question"],
  });
  const watched = ["student-group", "student-stage", "student-countdown", "round-deadline-note"]
    .map((id) => $(id))
    .filter(Boolean);
  const statusObserver = new MutationObserver(renderStatus);
  for (const element of watched) {
    statusObserver.observe(element, {
      childList: true,
      characterData: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["data-urgent"],
    });
  }
  renderNav();
  renderStatus();
}

start();
