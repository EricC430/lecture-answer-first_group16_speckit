"""ExportService：預覽、寫回、核對、重試、重新授權與 CSV（005）。

自己持有每活動一把鎖，只用來序列化「檢查有無進行中並建立嘗試」；Google I/O 與推送都在
鎖外（research R1）。日誌只記活動代碼、嘗試編號、快照識別、格數、結果與原因類別，不記
答案、原儲存格內容、試算表網址與標題、token、授權碼（FR-033）。005 對活動唯讀。
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from lecture_quiz.app.activity.ports import Clock, Requester, SyncPublisher, Viewer
from lecture_quiz.app.activity.service import ExportView
from lecture_quiz.app.guided_notes_import.models import ImportRecord, ImportRejection
from lecture_quiz.app.guided_notes_import.ports import AuthGateway, SheetsReader
from lecture_quiz.app.ranking_review.ports import FinalizedRound
from lecture_quiz.app.result_export.models import (
    AttemptKind,
    AttemptReason,
    AttemptStatus,
    ExportRejection,
    PreviewView,
    Result,
    WriteAttempt,
)
from lecture_quiz.app.result_export.ports import (
    ExportActivityGateway,
    ImportRecords,
    RankingsReader,
    SheetsWriter,
    SubmissionsReader,
)
from lecture_quiz.app.result_export.store import ExportStore
from lecture_quiz.core.activity.models import Activity
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.guided_notes_import.models import CellRef, SheetSnapshot
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from lecture_quiz.core.result_export.models import (
    BlankTarget,
    CurrentCell,
    FinalizedEntry,
    FinalizedQuestion,
    OutcomeStatus,
    ResultSnapshot,
    StructureCheck,
    StructureDifference,
    SubmissionFact,
)
from lecture_quiz.core.result_export.snapshot import build_snapshot, snapshot_id_of
from lecture_quiz.core.result_export.structure import (
    compare_structure,
    identity_difference,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Collected:
    """從 001～004 唯讀取得並轉成核心輸入的資料（只含已定案輪次）。"""

    view: ExportView
    round_numbers: tuple[int, ...]
    questions: tuple[FinalizedQuestion, ...]
    entries: tuple[FinalizedEntry, ...]
    submissions: tuple[SubmissionFact, ...]

    @property
    def has_winners(self) -> bool:
        """是否至少有一題有搶答成功者。"""
        return any(q.success_group is not None for q in self.questions)


def _import_rejection(rejection: ImportRejection | None) -> ExportRejection:
    """002 的讀取失敗對應成 005 的拒絕原因。"""
    mapping = {
        ImportRejection.NOT_AUTHORIZED: ExportRejection.NOT_AUTHORIZED,
        ImportRejection.AUTH_EXPIRED: ExportRejection.AUTH_EXPIRED,
        ImportRejection.PERMISSION_DENIED: ExportRejection.PERMISSION_DENIED,
        ImportRejection.GOOGLE_NOT_CONFIGURED: ExportRejection.GOOGLE_NOT_CONFIGURED,
    }
    return (
        mapping.get(rejection, ExportRejection.READ_FAILED)
        if rejection
        else ExportRejection.READ_FAILED
    )


def _attempt_reason(rejection: ImportRejection | None) -> AttemptReason:
    """002 的讀取失敗對應成寫回嘗試的原因類別。"""
    mapping = {
        ImportRejection.NOT_AUTHORIZED: AttemptReason.NOT_AUTHORIZED,
        ImportRejection.AUTH_EXPIRED: AttemptReason.AUTH_EXPIRED,
        ImportRejection.PERMISSION_DENIED: AttemptReason.PERMISSION_DENIED,
        ImportRejection.GOOGLE_NOT_CONFIGURED: AttemptReason.NOT_CONFIGURED,
    }
    return (
        mapping.get(rejection, AttemptReason.READ_FAILED)
        if rejection
        else AttemptReason.READ_FAILED
    )


@dataclass(frozen=True)
class SourceCheck:
    """重新讀取來源並比對結構的結果。

    Attributes:
        snapshot: 目前的工作表快照；讀不到時為 `None`。
        check: 結構比對結論；因讀取失敗而無法比對時為 `None`。
        failure: 讀取失敗的原因（授權、權限、網路等）；工作表不存在不算（算身分差異）。
    """

    snapshot: SheetSnapshot | None
    check: StructureCheck | None
    failure: ImportRejection | None


class ExportService:
    """005 的應用服務；建立時向 001 註冊快照擴充。"""

    def __init__(
        self,
        activity: ExportActivityGateway,
        imports: ImportRecords,
        auth: AuthGateway,
        reader: SheetsReader,
        writer: SheetsWriter | None,
        submissions: SubmissionsReader,
        ranking: RankingsReader,
        store: ExportStore,
        publisher: SyncPublisher,
        clock: Clock,
    ) -> None:
        """建立服務並註冊快照擴充。

        Args:
            activity: 001 的活動服務（匯出檢視、快照擴充）。
            imports: 002 的匯入記錄。
            auth: 002 的 Google 授權連接埠（重新授權入口直接使用）。
            reader: 002 的 Sheets 讀取連接埠（重新讀取來源）。
            writer: 005 的寫入連接埠；沒有時（尚未組裝）需要寫入器的操作回明確錯誤。
            submissions: 003 的提交唯讀介面。
            ranking: 004 的定案結果唯讀介面。
            store: 005 的記憶體存放區。
            publisher: 001 的推送。
            clock: 時鐘（只用於嘗試的開始與結束時間）。
        """
        self._activity = activity
        self._imports = imports
        self._auth = auth
        self._reader = reader
        self._writer = writer
        self._submissions = submissions
        self._ranking = ranking
        self._store = store
        self._publisher = publisher
        self._clock = clock
        activity.add_snapshot_extension(self.snapshot_extension)

    # ── 閘門與資料蒐集 ──────────────────────────────────────

    def _gate(self, code: str, requester: Requester) -> Result[ExportView]:
        """活動存在、老師身分、非已取消（沿用 001 的匯出檢視）。"""
        outcome = self._activity.export_view(code, requester)
        if outcome.ok and outcome.value is not None:
            return Result.success(outcome.value)
        mapping = {
            RejectionReason.ACTIVITY_GONE: ExportRejection.ACTIVITY_NOT_FOUND,
            RejectionReason.NOT_TEACHER: ExportRejection.NOT_TEACHER,
            RejectionReason.STAGE_NOT_ALLOWED: ExportRejection.ACTIVITY_CANCELLED,
        }
        return Result.failure(
            mapping.get(outcome.rejection, ExportRejection.NOT_TEACHER)  # type: ignore[arg-type]
        )

    def _collect(self, code: str, view: ExportView) -> Collected:
        """取 004 已定案輪次與 003 提交（只留已定案輪次），轉成核心輸入。"""
        rounds: tuple[FinalizedRound, ...] = self._ranking.finalized_rounds(code)
        numbers = tuple(r.round_number for r in rounds)
        questions: list[FinalizedQuestion] = []
        entries: list[FinalizedEntry] = []
        for fr in rounds:
            for ranking in fr.result.rankings:
                questions.append(
                    FinalizedQuestion(
                        fr.round_number, ranking.question_number, ranking.success_group
                    )
                )
                for e in ranking.entries:
                    entries.append(
                        FinalizedEntry(
                            fr.round_number,
                            ranking.question_number,
                            e.group_number,
                            e.rank,
                            e.wrong,
                        )
                    )
        finalized = set(numbers)
        facts = tuple(
            SubmissionFact(
                s.round_number,
                s.question_number,
                s.group_number,
                s.answers,
                s.received_at,
            )
            for s in self._submissions.all_submissions(code)
            if s.round_number in finalized
        )
        return Collected(view, numbers, tuple(questions), tuple(entries), facts)

    @staticmethod
    def _blank_targets(record: ImportRecord) -> tuple[BlankTarget, ...]:
        """002 的來源映射轉成核心輸入。"""
        return tuple(
            BlankTarget(b.question_number, b.sub_index, b.target) for b in record.blanks
        )

    async def _check_source(self, code: str, record: ImportRecord) -> SourceCheck:
        """重新讀取來源，以匯入時相同的規則重新辨識並逐項比對結構（FR-007）。"""
        read = await self._reader.read(code, record.source)
        if not read.ok or read.value is None:
            if read.rejection is ImportRejection.SHEET_NOT_FOUND:
                check = StructureCheck(False, (identity_difference(),))
                return SourceCheck(None, check, None)
            return SourceCheck(
                None, None, read.rejection or ImportRejection.READ_FAILED
            )
        reparsed = GuidedNotesParser.parse(read.value)
        return SourceCheck(
            read.value, compare_structure(record.structure, reparsed), None
        )

    # ── 預覽（US1）──────────────────────────────────────────

    async def preview(self, code: str, requester: Requester) -> Result[PreviewView]:
        """預覽：只讀取、不改任何狀態、不寫 Google。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            預覽；沒有可寫回的結果、非老師或已取消等情況為對應拒絕。
        """
        gate = self._gate(code, requester)
        if not gate.ok or gate.value is None:
            return Result.failure(gate.rejection or ExportRejection.NOT_TEACHER)
        collected = self._collect(code, gate.value)
        if not collected.has_winners:
            return Result.failure(ExportRejection.NO_RESULTS)
        record = self._imports.get_import_record(code)
        if record is None:
            return Result.failure(ExportRejection.NO_IMPORT_RECORD)
        if self._writer is None:
            return Result.failure(ExportRejection.GOOGLE_NOT_CONFIGURED)
        source = await self._check_source(code, record)
        if source.failure is not None or source.check is None:
            return Result.failure(_import_rejection(source.failure))
        winners = {
            q.question_number
            for q in collected.questions
            if q.success_group is not None
        }
        targets = [b.target for b in record.blanks if b.question_number in winners]
        current: Mapping[CellRef, CurrentCell] = {}
        if source.snapshot is not None:
            cells = await self._writer.read_cells(code, record.source, targets)
            if not cells.ok or cells.value is None:
                return Result.failure(_import_rejection(cells.rejection))
            current = cells.value
        snapshot = build_snapshot(
            collected.questions,
            collected.submissions,
            self._blank_targets(record),
            collected.view.question_numbers,
            current,
            collected.round_numbers,
        )
        title = source.snapshot.sheet_name if source.snapshot else record.sheet_title
        return Result.success(PreviewView(snapshot, source.check, title))

    # ── 確認寫回（US1：閘門與快照；結構檢查與狀態分類在 US2、US4）──

    async def confirm_write(
        self, code: str, requester: Requester, snapshot_id: str
    ) -> Result[WriteAttempt]:
        """老師手動確認寫回；確認只對預覽時的成果快照有效。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            snapshot_id: 預覽時拿到的成果快照識別。

        Returns:
            這次嘗試；沒有成果、陳舊快照、非老師、已取消等情況為對應拒絕。
        """
        gate = self._gate(code, requester)
        if not gate.ok or gate.value is None:
            return Result.failure(gate.rejection or ExportRejection.NOT_TEACHER)
        collected = self._collect(code, gate.value)
        if not collected.has_winners:
            return Result.failure(ExportRejection.NO_RESULTS)
        if snapshot_id != snapshot_id_of(collected.round_numbers):
            return Result.failure(ExportRejection.STALE_SNAPSHOT)
        record = self._imports.get_import_record(code)
        if record is None:
            return Result.failure(ExportRejection.NO_IMPORT_RECORD)
        if self._writer is None:
            return Result.failure(ExportRejection.GOOGLE_NOT_CONFIGURED)
        snapshot = build_snapshot(
            collected.questions,
            collected.submissions,
            self._blank_targets(record),
            collected.view.question_numbers,
            {},
            collected.round_numbers,
        )
        started = self._clock.now()
        source = await self._check_source(code, record)
        if source.failure is not None or source.check is None:
            return Result.success(
                self._failed(
                    code, snapshot, started, _attempt_reason(source.failure), ()
                )
            )
        if not source.check.ok:
            return Result.success(
                self._failed(
                    code,
                    snapshot,
                    started,
                    AttemptReason.STRUCTURE_CHANGED,
                    source.check.differences,
                )
            )
        cells = tuple((i.target, i.answer) for i in snapshot.items)
        written = await self._writer.write_text_cells(code, record.source, cells)
        total = len(cells)
        ok = written.outcome is OutcomeStatus.SUCCESS
        attempt = WriteAttempt(
            attempt_id=self._store.next_id(code),
            kind=AttemptKind.WRITE,
            snapshot_id=snapshot.snapshot_id,
            items=snapshot.items,
            status=AttemptStatus.SUCCESS if ok else AttemptStatus.FAILED,
            reason=None if ok else written.reason,
            started_at=started,
            finished_at=self._clock.now(),
            confirmed_cells=total if ok else 0,
            not_written_cells=0 if ok else total,
        )
        self._store.add_attempt(code, attempt)
        logger.info(
            "寫回 activity=%s attempt=%s snapshot=%s cells=%d status=%s",
            code,
            attempt.attempt_id,
            attempt.snapshot_id,
            total,
            attempt.status.value,
        )
        return Result.success(attempt)

    def _failed(
        self,
        code: str,
        snapshot: ResultSnapshot,
        started: datetime,
        reason: AttemptReason,
        differences: tuple[StructureDifference, ...],
    ) -> WriteAttempt:
        """記錄一次「寫入之前就停止」的明確失敗（零寫入）。"""
        total = len(snapshot.items)
        attempt = WriteAttempt(
            attempt_id=self._store.next_id(code),
            kind=AttemptKind.WRITE,
            snapshot_id=snapshot.snapshot_id,
            items=snapshot.items,
            status=AttemptStatus.FAILED,
            reason=reason,
            started_at=started,
            differences=differences,
            finished_at=self._clock.now(),
            not_written_cells=total,
        )
        self._store.add_attempt(code, attempt)
        logger.info(
            "寫回 activity=%s attempt=%s snapshot=%s cells=%d status=FAILED reason=%s",
            code,
            attempt.attempt_id,
            attempt.snapshot_id,
            total,
            reason.value,
        )
        return attempt

    # ── 重新授權（US2）──────────────────────────────────────

    async def start_authorization(self, code: str, requester: Requester) -> Result[str]:
        """重新授權入口：除已取消外任何階段都可使用，直接用 002 的授權連接埠。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            Google 授權網址（不寫入日誌）；非老師、已取消或未設定為對應拒絕。
        """
        gate = self._gate(code, requester)
        if not gate.ok:
            return Result.failure(gate.rejection or ExportRejection.NOT_TEACHER)
        if not self._auth.is_configured():
            return Result.failure(ExportRejection.GOOGLE_NOT_CONFIGURED)
        started = await self._auth.start_authorization(code, requester)
        if not started.ok or started.value is None:
            return Result.failure(_import_rejection(started.rejection))
        logger.info("重新授權開始 activity=%s", code)
        return Result.success(started.value)

    # ── 快照擴充 ────────────────────────────────────────────

    def snapshot_extension(
        self, activity: Activity, viewer: Viewer
    ) -> Mapping[str, object]:
        """老師快照的 `export` 欄位；學生與沒有嘗試時為空（US4 完成）。"""
        return {}

    async def _publish(self, code: str) -> None:
        """在鎖外推送最新快照。"""
        activity = self._activity.get(code)
        if activity is not None:
            await self._publisher.publish(activity)
