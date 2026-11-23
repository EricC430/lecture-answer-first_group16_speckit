// WebSocket 同步的共用前端（contracts/sync-websocket.md「連線流程」「前端行為」）。
// - 連線後第一則訊息送 {"type":"auth","token":...}；token 不放在網址。
// - 重連依序等 0.5、1、2、4 秒，之後每次 4 秒。
// - 超過 25 秒沒收到任何訊息，視為中斷。
// - 丟棄版本較舊的快照；老師快照在同一 version 內再以 revision 排序。
// - gone：清除本機身分，顯示「活動已失效，請重新建立或加入活動」，不再重連。
// - unauthorized：交給頁面處理（例如學生回到加入畫面），不再重連。
// - 中斷期間顯示「同步中斷，正在重新連線」，並在 <body> 加上 sync-broken，
//   各子功能把「成功」提示加上 class="success-hint"，中斷時會自動隱藏（FR-028）。
// - 狀態列顯示 v{version} 與延遲（畫面更新完成的時間 − changedAt）。

import { clearIdentity } from "./identity.js";

const RECONNECT_DELAYS_MS = [500, 1000, 2000, 4000];
const SILENCE_LIMIT_MS = 25000;
const MSG_BROKEN = "同步中斷，正在重新連線";
const MSG_GONE = "活動已失效，請重新建立或加入活動";

function setBanner(text) {
  const banner = document.getElementById("sync-banner");
  if (!banner) return;
  banner.textContent = text ?? "";
  banner.hidden = !text;
}

function setBroken(broken) {
  document.body.classList.toggle("sync-broken", broken);
  setBanner(broken ? MSG_BROKEN : null);
}

function setStatus(version, latencyMs) {
  const status = document.getElementById("sync-status");
  if (!status) return;
  status.textContent = `v${version}｜延遲 ${Math.max(0, Math.round(latencyMs))} ms`;
}

/**
 * 連線到活動的同步通道。
 * @param {string} code 活動代碼。
 * @param {string} token 老師或裝置 token。
 * @param {{
 *   onSnapshot: (snapshot: any) => void,
 *   onGone?: () => void,
 *   onUnauthorized?: (reason: string) => void,
 * }} handlers onSnapshot 必須同步完成畫面更新，延遲才會準確。
 * @returns {{close: () => void, currentVersion: () => number}}
 */
export function connectSync(code, token, handlers) {
  let socket = null;
  let attempt = 0;
  let version = -1;
  let revision = -1; // 只有老師快照有；組別變更只改 revision（FR-030）
  let stopped = false;
  let silenceTimer = null;
  let reconnectTimer = null;

  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`
    + `/ws/activities/${encodeURIComponent(code)}`;

  function stop() {
    stopped = true;
    clearTimeout(silenceTimer);
    clearTimeout(reconnectTimer);
    if (socket) socket.close();
  }

  function resetSilenceTimer() {
    clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
      // 太久沒有訊息：主動斷線，交給 close 事件重連
      setBroken(true);
      if (socket) socket.close();
    }, SILENCE_LIMIT_MS);
  }

  function scheduleReconnect() {
    if (stopped) return;
    setBroken(true);
    const delay = RECONNECT_DELAYS_MS[Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)];
    attempt += 1;
    reconnectTimer = setTimeout(open, delay);
  }

  function handleMessage(event) {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    resetSilenceTimer();
    switch (message.type) {
      case "snapshot":
        attempt = 0;
        setBroken(false);
        if (typeof message.version !== "number" || message.version < version) return;
        if (
          message.version === version &&
          typeof message.revision === "number" &&
          message.revision < revision
        ) {
          return; // 同一版本內較舊的老師快照
        }
        version = message.version;
        if (typeof message.revision === "number") revision = message.revision;
        handlers.onSnapshot(message);
        setStatus(version, Date.now() - Date.parse(message.changedAt));
        break;
      case "gone":
        stop();
        clearIdentity(code);
        document.body.classList.add("sync-broken");
        setBanner(MSG_GONE);
        if (handlers.onGone) handlers.onGone();
        break;
      case "unauthorized":
        stop();
        setBanner(null);
        if (handlers.onUnauthorized) handlers.onUnauthorized(String(message.reason ?? ""));
        break;
      default:
        break; // ping 或未知訊息：只重設計時器
    }
  }

  function open() {
    if (stopped) return;
    socket = new WebSocket(url);
    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({ type: "auth", token }));
      resetSilenceTimer();
    });
    socket.addEventListener("message", handleMessage);
    socket.addEventListener("close", () => {
      clearTimeout(silenceTimer);
      scheduleReconnect();
    });
    socket.addEventListener("error", () => setBroken(true));
  }

  open();
  return { close: stop, currentVersion: () => version };
}
