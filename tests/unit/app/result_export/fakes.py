"""005 服務層測試替身（不是真實實作；不連 Google）。

`FakeSheetsWriter` 與 002 的 `FakeSheetsReader` **共用同一份試算表狀態**：寫入成功時
替換讀取器內的 `SheetSnapshot`，所以寫入後的再讀取與再辨識看得到新內容。
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from lecture_quiz.app.guided_notes_import.models import (
    ImportRecord,
    ImportRejection,
    Result,
    SourceRef,
)
from lecture_quiz.app.result_export.ports import WriteResult
from lecture_quiz.core.guided_notes_import.models import CellRef, CellValue
from lecture_quiz.core.result_export.models import CellKind, CurrentCell, OutcomeStatus
from tests.unit.app.guided_notes_import.fakes import FakeSheetsReader


@dataclass
class FakeSheetsWriter:
    """記憶體版的寫入器：共用 `FakeSheetsReader.snapshots` 的格子內容。"""

    reader: FakeSheetsReader
    next_result: WriteResult = field(
        default_factory=lambda: WriteResult(OutcomeStatus.SUCCESS, None)
    )
    apply_on_pending: bool = False
    read_failure: ImportRejection | None = None
    write_calls: list[tuple[tuple[CellRef, str], ...]] = field(default_factory=list)
    read_calls: int = 0
    before_write: Callable[[], None] | None = None
    # 以 (試算表, 工作表) 紀錄使用者輸入（區分文字與其他型別）
    other_cells: dict[tuple[str, int, CellRef], CurrentCell] = field(
        default_factory=dict
    )

    def _key(self, source: SourceRef) -> tuple[str, int]:
        return (source.spreadsheet_id, source.sheet_id)

    async def read_cells(
        self, code: str, source: SourceRef, targets: Sequence[CellRef]
    ) -> Result[Mapping[CellRef, CurrentCell]]:
        """讀取目標格目前內容。"""
        self.read_calls += 1
        if self.read_failure is not None:
            return Result.failure(self.read_failure)
        snapshot = self.reader.snapshots[self._key(source)]
        out: dict[CellRef, CurrentCell] = {}
        for ref in targets:
            other = self.other_cells.get((*self._key(source), ref))
            if other is not None:
                out[ref] = other
                continue
            value = snapshot.cells.get(ref)
            if value is None:
                out[ref] = CurrentCell(CellKind.EMPTY, None, "")
            elif value.text is not None:
                out[ref] = CurrentCell(CellKind.TEXT, value.text, value.text)
            else:
                out[ref] = CurrentCell(CellKind.OTHER, None, value.display)
        return Result.success(out)

    async def write_text_cells(
        self, code: str, source: SourceRef, cells: Sequence[tuple[CellRef, str]]
    ) -> WriteResult:
        """記錄寫入；依 `next_result` 回傳結果，成功（或待確認且已套用）時更新格子。"""
        self.write_calls.append(tuple(cells))
        if self.before_write is not None:
            self.before_write()
        result = self.next_result
        applied = result.outcome is OutcomeStatus.SUCCESS or (
            result.outcome is OutcomeStatus.PENDING and self.apply_on_pending
        )
        if applied:
            self.apply(source, cells)
        return result

    def apply(self, source: SourceRef, cells: Sequence[tuple[CellRef, str]]) -> None:
        """把文字寫進共用的試算表狀態（只改目標格）。"""
        key = self._key(source)
        snapshot = self.reader.snapshots[key]
        new_cells = dict(snapshot.cells)
        for ref, text in cells:
            new_cells[ref] = CellValue(number=None, text=text, display=text)
            self.other_cells.pop((*key, ref), None)
        self.reader.snapshots[key] = replace(snapshot, cells=new_cells)


@dataclass
class FakeImportRecords:
    """`ImportRecords`：回傳預先設定的 `ImportRecord`。"""

    records: dict[str, ImportRecord] = field(default_factory=dict)

    def get_import_record(self, code: str) -> ImportRecord | None:
        """唯讀回傳匯入記錄。"""
        return self.records.get(code)


@dataclass
class FakeRankingReader:
    """004 的唯讀介面替身。"""

    rounds: tuple = ()
    calls: int = 0

    def finalized_rounds(self, code: str) -> tuple:
        """已定案輪次。"""
        self.calls += 1
        return self.rounds


@dataclass
class FakeSubmissionReader:
    """003 的唯讀介面替身；可含未定案輪次的提交（用來證明被過濾）。"""

    submissions: tuple = ()

    def all_submissions(self, code: str) -> tuple:
        """全部輪次的有效提交。"""
        return self.submissions


class RecordingPublisher:
    """記錄推送次數與呼叫當下 005 的鎖是否被持有。"""

    def __init__(self) -> None:
        """建立替身。"""
        self.published: list[str] = []
        self.lock_held: list[bool] = []
        self.lock_probe: Callable[[], bool] | None = None

    async def publish(self, activity) -> None:
        """記錄一次推送。"""
        self.published.append(activity.code)
        if self.lock_probe is not None:
            self.lock_held.append(self.lock_probe())
