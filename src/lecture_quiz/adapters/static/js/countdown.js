// 倒數剩餘秒數顯示（依快照中開輪時固定的 deadline 計算；截止判定以後端為準）。

/**
 * @param {() => HTMLElement|null} getElement 顯示倒數的元素。
 * @returns {{set: (deadline: string|null) => void}}
 */
export function startCountdown(getElement) {
  let deadline = null;
  let timer = null;

  function tick() {
    const element = getElement();
    if (!element) return;
    if (!deadline) {
      element.textContent = "";
      return;
    }
    const remaining = Math.max(0, Math.ceil((Date.parse(deadline) - Date.now()) / 1000));
    element.textContent = remaining > 0 ? `剩餘 ${remaining} 秒` : "已到截止時間";
  }

  return {
    set(value) {
      deadline = value;
      clearInterval(timer);
      timer = deadline ? setInterval(tick, 250) : null;
      tick();
    },
  };
}
