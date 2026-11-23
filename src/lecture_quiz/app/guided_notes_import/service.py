"""匯入服務：授權、檢視、選定來源與原子匯入（research R6）。

流程順序固定為「階段與身分 → 讀取 → 解析 → 001 `replace_questions` → 才保存」：
001 接受之前 002 不保存任何東西，所以任何失敗（授權、讀取、驗證、001 拒絕）都不改動
既有的 `selections` 與 `records`（FR-016、FR-027）。服務不拋業務錯誤。

「準備中」＝第一輪開始前的兩個階段（001 的 `PREPARING` 與 `JOINING`）。
"""

from collections.abc import Mapping

from lecture_quiz.app.activity.ports import ActivityGateway, Clock, Requester
from lecture_quiz.app.guided_notes_import.models import (
    ImportOutcome,
    ImportPreview,
    ImportRecord,
    ImportRejection,
    PickerConfig,
    Result,
    SourceRef,
    SourceSelection,
    SpreadsheetInfo,
)
from lecture_quiz.app.guided_notes_import.ports import AuthGateway, SheetsReader
from lecture_quiz.app.guided_notes_import.store import ImportStore
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.guided_notes_import.models import Blank
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser

_ALLOWED_STAGES = frozenset({Stage.PREPARING, Stage.JOINING})
_STARTED_STAGES = frozenset(
    {Stage.ROUND_OPEN, Stage.RESULT_PENDING, Stage.RESULT_FINAL, Stage.ENDED}
)


def build_preview(
    question_numbers: tuple[int, ...], blanks: tuple[Blank, ...]
) -> ImportPreview:
    """由題號與空格算出預覽：題組只算一題，總格數累計子空格。

    Args:
        question_numbers: 題號清單。
        blanks: 每個空格的來源映射。

    Returns:
        匯入預覽。
    """
    per_question: Mapping[int, int] = {
        number: sum(1 for b in blanks if b.question_number == number)
        for number in question_numbers
    }
    return ImportPreview(
        question_numbers=question_numbers,
        blanks_per_question=per_question,
        total_questions=len(question_numbers),
        total_blanks=len(blanks),
    )


class ImportService:
    """002 的應用服務；每個入口都先檢查活動、老師身分與階段。"""

    def __init__(
        self,
        auth: AuthGateway,
        reader: SheetsReader,
        activity: ActivityGateway,
        store: ImportStore,
        clock: Clock,
    ) -> None:
        """建立服務。

        Args:
            auth: Google 授權連接埠。
            reader: Sheets 讀取連接埠。
            activity: 001 提供的 `ActivityGateway`。
            store: 記憶體存放。
            clock: 時鐘（核心不使用，這裡只保留給需要時間的轉接層共用）。
        """
        self._auth = auth
        self._reader = reader
        self._activity = activity
        self._store = store
        self._clock = clock

    # ── 閘門 ────────────────────────────────────────────────

    def _gate(
        self, code: str, requester: Requester, *, require_preparing: bool = True
    ) -> ImportRejection | None:
        """依序檢查活動存在、老師身分、階段；通過回傳 `None`。"""
        stage = self._activity.stage(code)
        if stage is None:
            return ImportRejection.ACTIVITY_NOT_FOUND
        if not self._activity.is_teacher(code, requester):
            return ImportRejection.NOT_TEACHER
        if not require_preparing:
            return None
        if stage in _ALLOWED_STAGES:
            return None
        if stage is Stage.CANCELLED:
            return ImportRejection.ACTIVITY_CANCELLED
        if stage in _STARTED_STAGES:
            return ImportRejection.ROUND_STARTED
        return ImportRejection.STAGE_NOT_PREPARING

    def _configured(self) -> ImportRejection | None:
        """Google 連線沒有設定時回 `GOOGLE_NOT_CONFIGURED`（不退回離線路徑）。"""
        if self._auth.is_configured():
            return None
        return ImportRejection.GOOGLE_NOT_CONFIGURED

    # ── 授權與檢視 ──────────────────────────────────────────

    async def start_auth(self, code: str, requester: Requester) -> Result[str]:
        """開始授權：回傳 Google 授權網址。

        Args:
            code: 活動代碼。
            requester: 請求者。

        Returns:
            成功時為授權網址。
        """
        rejection = self._gate(code, requester) or self._configured()
        if rejection is not None:
            return Result.failure(rejection)
        return await self._auth.start_authorization(code, requester)

    def auth_status(self, code: str, requester: Requester) -> Result[bool]:
        """該活動老師是否已授權。

        Args:
            code: 活動代碼。
            requester: 請求者。

        Returns:
            成功時為是否已授權。
        """
        rejection = self._gate(code, requester, require_preparing=False)
        if rejection is not None:
            return Result.failure(rejection)
        return Result.success(self._auth.is_authorized(code))

    async def picker_config(
        self, code: str, requester: Requester
    ) -> Result[PickerConfig]:
        """取得 Picker 用的短效設定。

        Args:
            code: 活動代碼。
            requester: 請求者。

        Returns:
            成功時為 `PickerConfig`。
        """
        rejection = self._gate(code, requester) or self._configured()
        if rejection is not None:
            return Result.failure(rejection)
        return await self._auth.picker_credentials(code)

    async def inspect_spreadsheet(
        self, code: str, requester: Requester, spreadsheet_id: str
    ) -> Result[SpreadsheetInfo]:
        """列出試算表的可見工作表，並由後端決定是否自動選用（不改任何狀態）。

        Args:
            code: 活動代碼。
            requester: 請求者。
            spreadsheet_id: 試算表識別。

        Returns:
            成功時為檢視結果；隱藏的工作表不列入也不計張數，沒有可見工作表為
            `SHEET_NOT_FOUND`。
        """
        rejection = self._gate(code, requester) or self._configured()
        if rejection is not None:
            return Result.failure(rejection)
        if not self._auth.is_authorized(code):
            return Result.failure(ImportRejection.NOT_AUTHORIZED)
        inspected = await self._reader.inspect(code, spreadsheet_id)
        if not inspected.ok or inspected.value is None:
            return Result.failure(inspected.rejection or ImportRejection.READ_FAILED)
        info = inspected.value
        visible = tuple(s for s in info.sheets if not s.hidden)
        if not visible:
            return Result.failure(ImportRejection.SHEET_NOT_FOUND)
        auto = visible[0].sheet_id if len(visible) == 1 else None
        return Result.success(
            SpreadsheetInfo(info.spreadsheet_id, info.title, visible, auto)
        )

    async def select_source(
        self, code: str, requester: Requester, source: SourceRef
    ) -> Result[SourceSelection]:
        """驗證工作表屬於該試算表且可見後，才保存選定的來源。

        Args:
            code: 活動代碼。
            requester: 請求者。
            source: 老師選定的來源。

        Returns:
            成功時為已保存的選擇；失敗時舊的選擇不變。
        """
        inspected = await self.inspect_spreadsheet(
            code, requester, source.spreadsheet_id
        )
        if not inspected.ok or inspected.value is None:
            return Result.failure(inspected.rejection or ImportRejection.READ_FAILED)
        match = next(
            (s for s in inspected.value.sheets if s.sheet_id == source.sheet_id), None
        )
        if match is None:
            return Result.failure(ImportRejection.SHEET_NOT_FOUND)
        selection = SourceSelection(source=source, sheet_title=match.title)
        self._store.selections[code] = selection
        return Result.success(selection)

    # ── 匯入 ────────────────────────────────────────────────

    async def import_sheet(
        self, code: str, requester: Requester, idempotency_key: str | None = None
    ) -> ImportOutcome:
        """原子匯入：整段持有該活動的匯入鎖，任何失敗都不保存。

        Args:
            code: 活動代碼。
            requester: 請求者。
            idempotency_key: 去重用的 key；同一個 key 重送回傳第一次的結果。

        Returns:
            成功時含預覽與 001 的新版本號；失敗時含拒絕原因（驗證失敗時含問題清單）。
        """
        async with self._store.lock_for(code):
            if idempotency_key is not None:
                cached = self._store.idempotent.get((code, idempotency_key))
                if cached is not None:
                    return cached
            outcome = await self._import_locked(code, requester)
            if idempotency_key is not None:
                self._store.remember_outcome(code, idempotency_key, outcome)
            return outcome

    async def _import_locked(self, code: str, requester: Requester) -> ImportOutcome:
        """持有匯入鎖時的匯入流程（順序見模組說明）。"""
        rejection = self._gate(code, requester) or self._configured()
        if rejection is not None:
            return ImportOutcome(ok=False, rejection=rejection)
        selection = self._store.selections.get(code)
        if selection is None:
            return ImportOutcome(
                ok=False, rejection=ImportRejection.SOURCE_NOT_SELECTED
            )
        if not self._auth.is_authorized(code):
            return ImportOutcome(ok=False, rejection=ImportRejection.NOT_AUTHORIZED)

        read = await self._reader.read(code, selection.source)
        if not read.ok or read.value is None:
            return ImportOutcome(
                ok=False, rejection=read.rejection or ImportRejection.READ_FAILED
            )

        parsed = GuidedNotesParser.parse(read.value)
        if not parsed.ok or parsed.structure is None:
            return ImportOutcome(
                ok=False,
                rejection=ImportRejection.VALIDATION_FAILED,
                issues=parsed.issues,
            )

        numbers = tuple(q.number for q in parsed.questions)
        accepted = await self._activity.replace_questions(code, requester, numbers)
        if not accepted.ok or accepted.value is None:
            return ImportOutcome(ok=False, rejection=ImportRejection.GATEWAY_REJECTED)

        record = ImportRecord(
            source=selection.source,
            sheet_title=selection.sheet_title,
            blanks=parsed.blanks,
            structure=parsed.structure,
            question_numbers=numbers,
            version=accepted.value,
        )
        self._store.records[code] = record
        return ImportOutcome(
            ok=True,
            preview=build_preview(numbers, parsed.blanks),
            version=accepted.value,
            sheet_title=selection.sheet_title,
        )

    # ── 讀取結果 ────────────────────────────────────────────

    async def get_import_summary(
        self, code: str, requester: Requester
    ) -> Result[ImportPreview | None]:
        """頁面重新整理後恢復預覽；沒有匯入過時值為 `None`。

        Args:
            code: 活動代碼。
            requester: 請求者。

        Returns:
            成功時為預覽或 `None`（第一輪開始後仍可查看）。
        """
        rejection = self._gate(code, requester, require_preparing=False)
        if rejection is not None:
            return Result.failure(rejection)
        record = self._store.records.get(code)
        if record is None:
            return Result.success(None)
        return Result.success(build_preview(record.question_numbers, record.blanks))

    async def get_import_result(
        self, code: str, requester: Requester
    ) -> Result[ImportOutcome | None]:
        """頁面重新整理後恢復完整的匯入結果（含標題與 001 版本）；沒有匯入過為 `None`。

        Args:
            code: 活動代碼。
            requester: 請求者。

        Returns:
            成功時為已成功的 `ImportOutcome` 或 `None`。
        """
        rejection = self._gate(code, requester, require_preparing=False)
        if rejection is not None:
            return Result.failure(rejection)
        record = self._store.records.get(code)
        if record is None:
            return Result.success(None)
        return Result.success(
            ImportOutcome(
                ok=True,
                preview=build_preview(record.question_numbers, record.blanks),
                version=record.version,
                sheet_title=record.sheet_title,
            )
        )

    def get_import_record(self, code: str) -> ImportRecord | None:
        """給 005 使用：唯讀回傳最後一次成功匯入的記錄。

        Args:
            code: 活動代碼。

        Returns:
            匯入記錄；沒有匯入過時為 `None`。
        """
        return self._store.records.get(code)
