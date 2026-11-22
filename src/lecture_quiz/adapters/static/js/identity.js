// 前端身分保存（研究 R5）。
// - 老師 token：localStorage["teacher:{code}"]，同一瀏覽器的各分頁共用（⚠ 提案相依 Q-04）。
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
