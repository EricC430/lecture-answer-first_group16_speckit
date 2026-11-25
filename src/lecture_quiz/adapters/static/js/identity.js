// 前端身分保存（研究 R5）。
// - 老師 token：localStorage["teacher:{code}"]，同一瀏覽器的各分頁共用（alignment 2026-11-23 C6）。
// - 最後建立的活動代碼：localStorage["teacher:last"]，建立新活動時用來判定「一位老師一個活動」（C7），
//   也用來在網址沒有代碼時回到該活動（US1-AS2）；老師按「建立新活動」或活動失效時清除。
// - 裝置 token：sessionStorage["device:{code}"]，每個分頁是一台獨立裝置。
// token 只存在瀏覽器，不放在網址，也不輸出到畫面或 console。

function teacherKey(code) {
  return `teacher:${code}`;
}

function deviceKey(code) {
  return `device:${code}`;
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

/** 取得該活動的裝置 token；沒有時回傳 null。 */
export function getDeviceToken(code) {
  return sessionStorage.getItem(deviceKey(code));
}

/** 保存該活動的裝置 token。 */
export function setDeviceToken(code, token) {
  sessionStorage.setItem(deviceKey(code), token);
}

/** 清除該活動在本機的所有身分（活動失效、離開本組或被刪除時使用）。 */
export function clearIdentity(code) {
  localStorage.removeItem(teacherKey(code));
  sessionStorage.removeItem(deviceKey(code));
}

/** 把使用者輸入的活動代碼正規化：去除首尾空白並轉成大寫（FR-001）。 */
export function normalizeCode(raw) {
  return String(raw ?? "").trim().toUpperCase();
}
