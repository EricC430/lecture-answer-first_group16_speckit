// 活動階段的畫面文字（001）。006 從 teacher.js 搬出，讓投影畫面可以匯入而不觸發老師頁初始化；
// teacher.js 重新匯出同一個物件，名稱與內容不變（contracts/ui-dom.md）。

export const STAGE_LABELS = {
  PREPARING: "準備中",
  JOINING: "開放加入",
  ROUND_OPEN: "搶答中",
  RESULT_PENDING: "結果未定案",
  RESULT_FINAL: "結果已定案",
  ENDED: "已結束",
  CANCELLED: "已取消",
};
