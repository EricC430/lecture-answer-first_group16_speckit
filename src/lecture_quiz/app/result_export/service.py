"""ExportService：預覽、寫回、核對、重試、重新授權與 CSV（005）。

自己持有每活動一把鎖，只用來序列化「檢查有無進行中並建立嘗試」；Google I/O 與推送都在
鎖外（research R1）。日誌只記活動代碼、嘗試編號、快照識別、格數、結果與原因類別，不記
答案、原儲存格內容、試算表網址與標題、token、授權碼（FR-033）。005 對活動唯讀。
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace

from lecture_quiz.app.activity.ports import (
    Clock,
    Requester,
    SyncPublisher,
    TeacherViewer,
    Viewer,
)
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
from lecture_quiz.app.result_export.views import attempt_summary
from lecture_quiz.core.activity.models import Activity
from lecture_quiz.core.activity.results import RejectionReason
from lecture_quiz.core.guided_notes_import.models import CellRef, SheetSnapshot
from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from lecture_quiz.core.result_export.csv_export import build_rows, render_csv
from lecture_quiz.core.result_export.models import (
    BlankTarget,
    CurrentCell,
    ExportRow,
    FinalizedEntry,
    FinalizedQuestion,
    OutcomeStatus,
    StructureCheck,
    StructureDifference,
    SubmissionFact,
    WritePlanItem,
)
from lecture_quiz.core.result_export.reconcile import reconcile
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

    # ── 確認寫回與重試（US1、US2、US4）─────────────────────────

    def _prepare(
        self, code: str, requester: Requester
    ) -> Result[tuple[Collected, ImportRecord, SheetsWriter]]:
        """閘門、取已定案資料、匯入記錄與寫入器（沒有成果、沒有記錄、沒有寫入器都拒絕）。"""
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
        return Result.success((collected, record, self._writer))

    async def confirm_write(
        self, code: str, requester: Requester, snapshot_id: str
    ) -> Result[WriteAttempt]:
        """老師手動確認寫回；確認只對預覽時的成果快照有效。

        同一活動一次只有一個寫入：已有進行中的嘗試時，回覆那次嘗試（`already_in_progress`），
        不開始第二次寫入。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            snapshot_id: 預覽時拿到的成果快照識別。

        Returns:
            這次嘗試；沒有成果、陳舊快照、非老師、已取消等情況為對應拒絕。
        """
        prepared = self._prepare(code, requester)
        if not prepared.ok or prepared.value is None:
            return Result.failure(prepared.rejection or ExportRejection.NO_RESULTS)
        collected, record, writer = prepared.value
        if snapshot_id != snapshot_id_of(collected.round_numbers):
            return Result.failure(ExportRejection.STALE_SNAPSHOT)
        snapshot = build_snapshot(
            collected.questions,
            collected.submissions,
            self._blank_targets(record),
            collected.view.question_numbers,
            {},
            collected.round_numbers,
        )
        attempt, busy = await self._begin(
            code, AttemptKind.WRITE, snapshot.snapshot_id, snapshot.items
        )
        if busy:
            return Result.success(replace(attempt, already_in_progress=True))
        return Result.success(await self._run(code, record, writer, attempt))

    async def retry(
        self, code: str, requester: Requester, attempt_id: int
    ) -> Result[WriteAttempt]:
        """重試最新一次嘗試：同一份快照與答案，重新檢查結構後寫入（冪等）。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            attempt_id: 要重試的嘗試編號（必須是最新一次）。

        Returns:
            新的嘗試（`kind=RETRY`）；進行中、不是最新一次等為對應拒絕。
        """
        prepared = self._prepare(code, requester)
        if not prepared.ok or prepared.value is None:
            return Result.failure(prepared.rejection or ExportRejection.NO_RESULTS)
        _, record, writer = prepared.value
        target = self._latest_for(code, attempt_id)
        if not target.ok or target.value is None:
            return Result.failure(target.rejection or ExportRejection.ATTEMPT_NOT_FOUND)
        attempt, busy = await self._begin(
            code, AttemptKind.RETRY, target.value.snapshot_id, target.value.items
        )
        if busy:
            return Result.failure(ExportRejection.WRITE_IN_PROGRESS)
        return Result.success(await self._run(code, record, writer, attempt))

    def _latest_for(self, code: str, attempt_id: int) -> Result[WriteAttempt]:
        """只能對最新一次、且不在進行中的嘗試核對或重試。"""
        found = self._store.get(code, attempt_id)
        if found is None:
            return Result.failure(ExportRejection.ATTEMPT_NOT_FOUND)
        latest = self._store.latest(code)
        if latest is None or latest.attempt_id != attempt_id:
            return Result.failure(ExportRejection.NOT_LATEST_ATTEMPT)
        if latest.status is AttemptStatus.IN_PROGRESS:
            return Result.failure(ExportRejection.WRITE_IN_PROGRESS)
        return Result.success(latest)

    async def _begin(
        self,
        code: str,
        kind: AttemptKind,
        snapshot_id: str,
        items: tuple[WritePlanItem, ...],
    ) -> tuple[WriteAttempt, bool]:
        """在鎖內檢查有無進行中並建立進行中的嘗試（兩者之間沒有 `await`，research R1）。

        Returns:
            （嘗試, 是否已有進行中）。已有進行中時回傳那一次、不建立新的。
        """
        async with self._store.lock(code):
            latest = self._store.latest(code)
            if latest is not None and latest.status is AttemptStatus.IN_PROGRESS:
                return latest, True
            attempt = WriteAttempt(
                attempt_id=self._store.next_id(code),
                kind=kind,
                snapshot_id=snapshot_id,
                items=items,
                status=AttemptStatus.IN_PROGRESS,
                reason=None,
                started_at=self._clock.now(),
                pending_cells=len(items),
            )
            self._store.add_attempt(code, attempt)
        await self._publish(code)
        return attempt, False

    async def _run(
        self,
        code: str,
        record: ImportRecord,
        writer: SheetsWriter,
        attempt: WriteAttempt,
    ) -> WriteAttempt:
        """鎖外做 Google I/O（重新讀取、結構比對、寫入），再在鎖內記錄最終狀態。"""
        total = attempt.total_cells
        try:
            source = await self._check_source(code, record)
            if source.failure is not None or source.check is None:
                final = self._settle(
                    attempt, AttemptStatus.FAILED, _attempt_reason(source.failure)
                )
            elif not source.check.ok:
                final = self._settle(
                    attempt,
                    AttemptStatus.FAILED,
                    AttemptReason.STRUCTURE_CHANGED,
                    differences=source.check.differences,
                )
            else:
                cells = tuple((i.target, i.answer) for i in attempt.items)
                written = await writer.write_text_cells(code, record.source, cells)
                if written.outcome is OutcomeStatus.SUCCESS:
                    final = self._settle(attempt, AttemptStatus.SUCCESS, None)
                elif written.outcome is OutcomeStatus.FAILED:
                    final = self._settle(
                        attempt,
                        AttemptStatus.FAILED,
                        written.reason or AttemptReason.REJECTED,
                    )
                else:
                    final = self._settle(
                        attempt,
                        AttemptStatus.PENDING,
                        written.reason or AttemptReason.UNKNOWN,
                    )
        except Exception:
            # 程式錯誤照常往上拋；但嘗試不能永遠停在進行中（會擋住之後所有寫入）
            await self._store_final(
                code,
                self._settle(attempt, AttemptStatus.PENDING, AttemptReason.UNKNOWN),
            )
            raise
        await self._store_final(code, final)
        logger.info(
            "寫回 activity=%s attempt=%s snapshot=%s cells=%d status=%s reason=%s",
            code,
            final.attempt_id,
            final.snapshot_id,
            total,
            final.status.value,
            final.reason.value if final.reason else "-",
        )
        return final

    def _settle(
        self,
        attempt: WriteAttempt,
        status: AttemptStatus,
        reason: AttemptReason | None,
        differences: tuple[StructureDifference, ...] = (),
    ) -> WriteAttempt:
        """依結果填入三個格數（data-model「狀態與格數對照」）與結束時間。"""
        total = attempt.total_cells
        confirmed, not_written, pending = {
            AttemptStatus.SUCCESS: (total, 0, 0),
            AttemptStatus.FAILED: (0, total, 0),
        }.get(status, (0, 0, total))
        return replace(
            attempt,
            status=status,
            reason=reason,
            differences=differences,
            finished_at=self._clock.now(),
            confirmed_cells=confirmed,
            not_written_cells=not_written,
            pending_cells=pending,
        )

    async def _store_final(self, code: str, attempt: WriteAttempt) -> None:
        """在鎖內存入最終狀態，鎖外推送。"""
        async with self._store.lock(code):
            self._store.replace(code, attempt)
        await self._publish(code)

    # ── 重新讀取核對（US4）──────────────────────────────────

    async def recheck(
        self, code: str, requester: Requester, attempt_id: int
    ) -> Result[WriteAttempt]:
        """重新讀取核對：只讀取記錄的位置，不寫入、不做結構檢查（clarify Q2）。

        讀取失敗（授權失效、無權限、網路）時只回錯誤，不改變該嘗試的狀態與格數。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。
            attempt_id: 要核對的嘗試編號（必須是最新一次）。

        Returns:
            更新後的嘗試（含逐格的預期與目前內容）。
        """
        prepared = self._prepare(code, requester)
        if not prepared.ok or prepared.value is None:
            return Result.failure(prepared.rejection or ExportRejection.NO_RESULTS)
        _, record, writer = prepared.value
        target = self._latest_for(code, attempt_id)
        if not target.ok or target.value is None:
            return Result.failure(target.rejection or ExportRejection.ATTEMPT_NOT_FOUND)
        items = target.value.items
        cells = await writer.read_cells(code, record.source, [i.target for i in items])
        if not cells.ok or cells.value is None:
            return Result.failure(_import_rejection(cells.rejection))
        outcome = reconcile(
            [(i.question_number, i.sub_index, i.target, i.answer) for i in items],
            cells.value,
        )
        async with self._store.lock(code):
            latest = self._store.latest(code)
            if latest is None or latest.attempt_id != attempt_id:
                return Result.failure(ExportRejection.NOT_LATEST_ATTEMPT)
            if latest.status is AttemptStatus.IN_PROGRESS:
                return Result.failure(ExportRejection.WRITE_IN_PROGRESS)
            matched = sum(1 for c in outcome.checks if c.matches)
            total = latest.total_cells
            if outcome.status is OutcomeStatus.SUCCESS:
                status, reason, counts = AttemptStatus.SUCCESS, None, (total, 0, 0)
            elif outcome.status is OutcomeStatus.FAILED:
                status = AttemptStatus.FAILED
                reason = AttemptReason.NOT_WRITTEN
                counts = (0, total, 0)
            else:
                status, reason = AttemptStatus.PENDING, AttemptReason.UNKNOWN
                counts = (matched, 0, total - matched)
            updated = replace(
                latest,
                status=status,
                reason=reason,
                differences=(),
                cell_checks=outcome.checks,
                finished_at=self._clock.now(),
                confirmed_cells=counts[0],
                not_written_cells=counts[1],
                pending_cells=counts[2],
            )
            self._store.replace(code, updated)
        await self._publish(code)
        logger.info(
            "核對 activity=%s attempt=%s cells=%d status=%s",
            code,
            attempt_id,
            updated.total_cells,
            status.value,
        )
        return Result.success(updated)

    def latest_attempt(
        self, code: str, requester: Requester
    ) -> Result[WriteAttempt | None]:
        """最近一次寫回嘗試（頁面重新整理後恢復）；沒有時值為 `None`。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            最近一次嘗試或 `None`；非老師、已取消為對應拒絕。
        """
        gate = self._gate(code, requester)
        if not gate.ok:
            return Result.failure(gate.rejection or ExportRejection.NOT_TEACHER)
        return Result(ok=True, value=self._store.latest(code))

    # ── CSV（US5、US6）──────────────────────────────────────

    def download_csv(self, code: str, requester: Requester) -> Result[bytes]:
        """所有已定案輪次的完整紀錄 CSV（UTF-8 加 BOM）。

        不依賴 Google 授權、寫回狀態或來源結構，也不呼叫任何 Google 連接埠。沒有已定案
        資料時只含表頭，且不需要匯入記錄（準備中的活動可能還沒有）。

        Args:
            code: 活動代碼。
            requester: 已解析的身分。

        Returns:
            CSV 位元組；非老師、已取消為對應拒絕。
        """
        gate = self._gate(code, requester)
        if not gate.ok or gate.value is None:
            return Result.failure(gate.rejection or ExportRejection.NOT_TEACHER)
        collected = self._collect(code, gate.value)
        rows: tuple[ExportRow, ...] = ()
        if collected.entries:
            record = self._imports.get_import_record(code)
            if record is None:
                return Result.failure(ExportRejection.NO_IMPORT_RECORD)
            rows = build_rows(
                collected.entries, collected.submissions, self._blank_targets(record)
            )
        logger.info("下載 CSV activity=%s rows=%d", code, len(rows))
        return Result.success(("﻿" + render_csv(rows)).encode("utf-8"))

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
        """老師快照的 `export` 欄位；學生與沒有嘗試時為空。

        同步、無副作用的純讀取；摘要不含逐格答案、原內容、差異清單與網址。
        """
        if not isinstance(viewer, TeacherViewer):
            return {}
        latest = self._store.latest(activity.code)
        if latest is None:
            return {}
        return {"export": attempt_summary(latest)}

    async def _publish(self, code: str) -> None:
        """在鎖外推送最新快照。"""
        activity = self._activity.get(code)
        if activity is not None:
            await self._publisher.publish(activity)
