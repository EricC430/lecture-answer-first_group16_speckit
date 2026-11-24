"""002 應用層的連接埠（contracts/service-interfaces.md）。

由外層轉接層實作；所有跨出應用層的 I/O 為 `async`。`Clock` 與 `ActivityGateway`
沿用 001（`lecture_quiz.app.activity.ports`），不在這裡重複定義：
`stage`、`is_teacher` 是同步方法，只有 `replace_questions` 是 `async`。
"""

from typing import Protocol

from lecture_quiz.app.activity.ports import Requester
from lecture_quiz.app.guided_notes_import.models import (
    CallbackResult,
    PickerConfig,
    Result,
    SourceRef,
    SpreadsheetInfo,
)
from lecture_quiz.core.guided_notes_import.models import SheetSnapshot


class AuthGateway(Protocol):
    """Google 授權（授權碼流程；token 只存在記憶體）。"""

    def is_configured(self) -> bool:
        """Google 連線設定是否齊備（空字串視為未設定）。

        Returns:
            齊備為 True；否則匯入相關入口一律回 `GOOGLE_NOT_CONFIGURED`。
        """
        ...

    async def start_authorization(self, code: str, requester: Requester) -> Result[str]:
        """產生一次性且有期限的 `state`，回傳 Google 授權網址。

        Args:
            code: 活動代碼。
            requester: 已通過老師檢查的請求者。

        Returns:
            成功時為授權網址；沒有設定 Google 連線時為 `GOOGLE_NOT_CONFIGURED`。
        """
        ...

    async def complete_authorization(
        self, state: str | None, auth_code: str | None, error: str | None
    ) -> CallbackResult:
        """處理 Google 導回：驗證 `state`、交換 token 並存入記憶體。

        Args:
            state: 導回帶的 `state`。
            auth_code: 授權碼。
            error: Google 回報的錯誤（使用者取消或拒絕時有值）。

        Returns:
            活動代碼與結果（`ok`、`denied`、`error`）。
        """
        ...

    def is_authorized(self, code: str) -> bool:
        """該活動的老師是否有有效授權。

        Args:
            code: 活動代碼。

        Returns:
            已授權為 True。
        """
        ...

    async def picker_credentials(self, code: str) -> Result[PickerConfig]:
        """取得 Picker 用的短效憑證。

        Args:
            code: 活動代碼。

        Returns:
            成功時為 `PickerConfig`；未授權或已失效時為對應拒絕。
        """
        ...


class SheetsReader(Protocol):
    """Google Sheets／Drive 的唯讀存取。"""

    async def inspect(self, code: str, spreadsheet_id: str) -> Result[SpreadsheetInfo]:
        """先確認是 Google 試算表，再取得工作表清單（含隱藏旗標）。

        Args:
            code: 活動代碼（授權依活動保存）。
            spreadsheet_id: 試算表識別。

        Returns:
            成功時為檢視結果；失敗時為拒絕（`NOT_A_SPREADSHEET` 等）。
        """
        ...

    async def read(self, code: str, source: SourceRef) -> Result[SheetSnapshot]:
        """以欄位遮罩讀取一張工作表並轉成核心的 `SheetSnapshot`（唯讀）。

        Args:
            code: 活動代碼。
            source: 來源識別。

        Returns:
            成功時為快照；失敗時為拒絕。
        """
        ...
