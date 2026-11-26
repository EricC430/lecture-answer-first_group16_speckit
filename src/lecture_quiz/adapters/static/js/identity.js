// 前端身分保存（研究 R5）。
// - 老師 token：localStorage["teacher:{code}"]，同一瀏覽器的各分頁共用（alignment 2026-11-23 C6）。
// - 最後建立的活動代碼：localStorage["teacher:last"]，建立新活動時用來判定「一位老師一個活動」（C7），
//   也用來在網址沒有代碼時回到該活動（US1-AS2）；老師按「建立新活動」或活動失效時清除。
// - 學生身分（007）：由後端發的 HttpOnly cookie `lq_browser` 保存，同一個瀏覽器的所有分頁共用，
//   頁面程式碼讀不到（spec FR-008）；學生頁的請求與同步連線由瀏覽器自動帶上 cookie，
//   所以這裡沒有任何學生 token 的存取函式。
// token 只存在瀏覽器，不放在網址，也不輸出到畫面或 console。

function teacherKey(code) {
  return `teacher:${code}`;
}

/** 取得該活動的老師 token；沒有時回傳 null。 */
export function getTeacherToken(code) {
  return localStorage.getItem(teacherKey(code));
}

/** 保存該活動的老師 token。 */
export function setTeacherToken(code, token) {
  localStorage.setItem(teacherKey(code), token);
}

const LAST_TEACHER_KEY = "teacher:last";

/** 取得這個瀏覽器最後建立的活動代碼；沒有時回傳 null。 */
export function getLastTeacherCode() {
  return localStorage.getItem(LAST_TEACHER_KEY);
}

/** 記住這個瀏覽器最後建立的活動代碼。 */
export function setLastTeacherCode(code) {
  localStorage.setItem(LAST_TEACHER_KEY, code);
}

/**
 * 忘記「最後建立的活動」（老師按「建立新活動」或活動已失效時）：之後開不帶代碼的老師頁
 * 不再自動回到它。只清這個指標，老師 token 保留，帶 `?code=` 的網址仍可回到該活動。
 */
export function clearLastTeacherCode() {
  localStorage.removeItem(LAST_TEACHER_KEY);
}

/**
 * 活動已失效時清除該活動的老師 token。學生身分在 HttpOnly cookie，頁面讀不到也不需要清：
 * 後端重啟後它在任何活動都查不到，自然失效（007 research R7）。
 */
export function clearIdentity(code) {
  localStorage.removeItem(teacherKey(code));
}

/** 把使用者輸入的活動代碼正規化：去除首尾空白並轉成大寫（FR-001）。 */
export function normalizeCode(raw) {
  return String(raw ?? "").trim().toUpperCase();
}
