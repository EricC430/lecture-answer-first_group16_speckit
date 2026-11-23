"""測試替身（不是真實實作）：Fake 授權、Fake Sheets 讀取器、Fake 001 ActivityGateway。

`FakeActivityGateway` 的行為依 001 契約：`stage`、`is_teacher` 是同步方法；
`replace_questions` 是 async，只允許老師在 `PREPARING`／`JOINING`，成功回傳新 version，
被拒時題目完全不變。可注入「解析後、寫入前階段改變」。
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from lecture_quiz.app.activity.ports import Outcome, Requester
from lecture_quiz.app.guided_notes_import.models import (
    CallbackResult,
    ImportRejection,
    PickerConfig,
    Result,
    SheetInfo,
    SourceRef,
    SpreadsheetInfo,
)
from lecture_quiz.core.activity.commands import Anonymous, Teacher
from lecture_quiz.core.activity.models import Stage
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.guided_notes_import.models import SheetSnapshot

TEACHER = Teacher("teacher-hash")
OTHER_TEACHER = Teacher("other-teacher-hash")
STUDENT = Anonymous()


class FakeAuthGateway:
    """測試替身：可注入授權狀態與未設定 Google 連線。"""

    def __init__(self, authorized: bool = True, configured: bool = True) -> None:
        """建立替身。"""
        self.authorized_codes: set[str] = set()
        self.default_authorized = authorized
        self.configured = configured
        self.calls: list[str] = []
        self.callback_result = CallbackResult(code=None, status="error")

    def authorize(self, code: str) -> None:
        """把該活動標為已授權。"""
        self.authorized_codes.add(code)

    def revoke(self, code: str) -> None:
        """模擬授權在流程中途失效。"""
        self.authorized_codes.discard(code)
        self.default_authorized = False

    def is_configured(self) -> bool:
        """Google 連線設定是否齊備。"""
        return self.configured

    async def start_authorization(self, code: str, requester: Requester) -> Result[str]:
        """回傳假的授權網址。"""
        self.calls.append("start_authorization")
        if not self.configured:
            return Result.failure(ImportRejection.GOOGLE_NOT_CONFIGURED)
        return Result.success("https://accounts.example.test/auth?state=fake")

    async def complete_authorization(
        self, state: str | None, auth_code: str | None, error: str | None
    ) -> CallbackResult:
        """回傳預先設定的回呼結果；`calls` 記錄是否被呼叫。"""
        self.calls.append("complete_authorization")
        return self.callback_result

    def is_authorized(self, code: str) -> bool:
        """是否已授權。"""
        return code in self.authorized_codes or self.default_authorized

    async def picker_credentials(self, code: str) -> Result[PickerConfig]:
        """回傳假的 Picker 設定。"""
        if not self.configured:
            return Result.failure(ImportRejection.GOOGLE_NOT_CONFIGURED)
        if not self.is_authorized(code):
            return Result.failure(ImportRejection.NOT_AUTHORIZED)
        return Result.success(PickerConfig("fake-token", "fake-key", "fake-app"))


@dataclass
class FakeSheetsReader:
    """測試替身：可注入試算表、工作表快照與各種拒絕。"""

    spreadsheets: dict[str, tuple[str, list[SheetInfo]]] = field(default_factory=dict)
    snapshots: dict[tuple[str, int], SheetSnapshot] = field(default_factory=dict)
    inspect_failure: ImportRejection | None = None
    read_failure: ImportRejection | None = None
    calls: list[str] = field(default_factory=list)
    before_read: Callable[[], None] | None = None

    def add(
        self,
        spreadsheet_id: str,
        title: str,
        sheets: list[tuple[int, str, SheetSnapshot | None]],
        hidden: tuple[int, ...] = (),
    ) -> None:
        """登錄一份試算表與它的工作表。"""
        self.spreadsheets[spreadsheet_id] = (
            title,
            [SheetInfo(sid, name, sid in hidden) for sid, name, _ in sheets],
        )
        for sid, _, snapshot in sheets:
            if snapshot is not None:
                self.snapshots[(spreadsheet_id, sid)] = snapshot

    async def inspect(self, code: str, spreadsheet_id: str) -> Result[SpreadsheetInfo]:
        """回傳試算表資訊（含隱藏旗標，由服務濾除）。"""
        self.calls.append(f"inspect:{spreadsheet_id}")
        if self.inspect_failure is not None:
            return Result.failure(self.inspect_failure)
        entry = self.spreadsheets.get(spreadsheet_id)
        if entry is None:
            return Result.failure(ImportRejection.NOT_A_SPREADSHEET)
        title, sheets = entry
        return Result.success(SpreadsheetInfo(spreadsheet_id, title, tuple(sheets)))

    async def read(self, code: str, source: SourceRef) -> Result[SheetSnapshot]:
        """回傳工作表快照。"""
        self.calls.append(f"read:{source.spreadsheet_id}:{source.sheet_id}")
        if self.before_read is not None:
            self.before_read()
        if self.read_failure is not None:
            return Result.failure(self.read_failure)
        snapshot = self.snapshots.get((source.spreadsheet_id, source.sheet_id))
        if snapshot is None:
            return Result.failure(ImportRejection.SHEET_NOT_FOUND)
        return Result.success(snapshot)


class FakeActivityGateway:
    """測試替身：行為依 001 契約（stage、is_teacher 同步；replace_questions async）。"""

    def __init__(self) -> None:
        """建立沒有任何活動的替身。"""
        self.stages: dict[str, Stage] = {}
        self.teachers: dict[str, Requester] = {}
        self.questions: dict[str, tuple[int, ...]] = {}
        self.versions: dict[str, int] = {}
        self.replace_calls: list[tuple[str, tuple[int, ...]]] = []
        self.before_replace: Callable[[], None] | None = None

    def add_activity(
        self, code: str, stage: Stage = Stage.PREPARING, teacher: Requester = TEACHER
    ) -> None:
        """建立一個活動。"""
        self.stages[code] = stage
        self.teachers[code] = teacher
        self.questions[code] = ()
        self.versions[code] = 1

    def stage(self, code: str) -> Stage | None:
        """目前階段；不存在時為 `None`。"""
        return self.stages.get(code)

    def is_teacher(self, code: str, requester: Requester) -> bool:
        """是否為該活動老師。"""
        return code in self.teachers and self.teachers[code] == requester

    async def replace_questions(
        self, code: str, requester: Requester, question_numbers: tuple[int, ...]
    ) -> Outcome[int]:
        """整份取代題號；只允許老師在 PREPARING／JOINING。"""
        self.replace_calls.append((code, question_numbers))
        if self.before_replace is not None:
            self.before_replace()
        if code not in self.stages:
            return Outcome(ok=False, rejection=RejectionReason.ACTIVITY_GONE)
        if not self.is_teacher(code, requester):
            return Outcome(ok=False, rejection=RejectionReason.NOT_TEACHER)
        if self.stages[code] not in (Stage.PREPARING, Stage.JOINING):
            return Outcome(ok=False, rejection=RejectionReason.STAGE_NOT_ALLOWED)
        self.questions[code] = question_numbers
        self.versions[code] += 1
        return Outcome(ok=True, value=self.versions[code])
