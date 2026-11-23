// HTTP 呼叫的共用包裝（contracts/http-api.md「共通規則」）。
// - 自動帶 Authorization: Bearer <token>。
// - 每次使用者操作（POST／DELETE 等）自動產生 Idempotency-Key；網路失敗重試時沿用同一個 key。
// - 錯誤一律整理成 { code, message }，畫面用 showError 以 textContent 顯示（原則 V）。

const RETRY_DELAYS_MS = [500, 1000, 2000];

/** 產生一個新的 Idempotency-Key（UUID）。 */
export function newIdempotencyKey() {
  return crypto.randomUUID();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 呼叫後端 API。
 * @param {string} method HTTP 方法。
 * @param {string} path 以 /api 開頭的路徑。
 * @param {{token?: string|null, body?: unknown, idempotencyKey?: string}} [options]
 * @returns {Promise<{ok: boolean, status: number, data: any, error: {code: string, message: string}|null}>}
 */
export async function apiRequest(method, path, options = {}) {
  const { token = null, body = undefined, idempotencyKey = undefined } = options;
  const headers = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json; charset=utf-8";
  if (method !== "GET" && method !== "HEAD") {
    headers["Idempotency-Key"] = idempotencyKey ?? newIdempotencyKey();
  }
  const init = {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  };

  for (let attempt = 0; ; attempt += 1) {
    let response;
    try {
      response = await fetch(path, init);
    } catch (networkError) {
      if (attempt < RETRY_DELAYS_MS.length) {
        await sleep(RETRY_DELAYS_MS[attempt]);
        continue; // 同一個 init，因此沿用同一個 Idempotency-Key
      }
      return {
        ok: false,
        status: 0,
        data: null,
        error: { code: "NETWORK_ERROR", message: "無法連線到伺服器，請確認後端仍在執行。" },
      };
    }
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (response.ok) return { ok: true, status: response.status, data, error: null };
    const error = data && data.error
      ? { code: String(data.error.code), message: String(data.error.message) }
      : { code: `HTTP_${response.status}`, message: "請求失敗，請稍後再試。" };
    return { ok: false, status: response.status, data, error };
  }
}

/**
 * 在指定元素顯示錯誤訊息（textContent，不解析 HTML）；error 為 null 時清除。
 * @param {HTMLElement|null} element
 * @param {{message: string}|null} error
 */
export function showError(element, error) {
  if (!element) return;
  element.textContent = error ? error.message : "";
  element.hidden = !error;
}
