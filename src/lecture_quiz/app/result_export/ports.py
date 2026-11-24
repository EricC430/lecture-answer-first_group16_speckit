"""005 應用層的連接埠（contracts/service-interfaces.md）。

`SheetsWriter` 由外層轉接層實作；其餘是 001～004 已提供的唯讀介面，這裡只定義 005
用到的部分（結構性相符即可，不匯入它們的服務類別）。
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from lecture_quiz.app.activity.ports import Outcome, Requester, Viewer
from lecture_quiz.app.activity.service import ExportView
from lecture_quiz.app.guided_notes_import.models import ImportRecord, Result, SourceRef
from lecture_quiz.app.ranking_review.ports import FinalizedRound
from lecture_quiz.app.result_export.models import AttemptReason
from lecture_quiz.core.activity.models import Activity
from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import CurrentCell, OutcomeStatus
from lecture_quiz.core.round_submission.models import Submission


@dataclass(frozen=True)
class WriteResult:
    """一次寫入的外部結果。

    Attributes:
        outcome: 成功、明確失敗（確認沒有任何格被改）或待確認（無法證實）。
        reason: 失敗或待確認的原因類別；成功時為 `None`。
    """

    outcome: OutcomeStatus
    reason: AttemptReason | None = None


class SheetsWriter(Protocol):
    """Google Sheets 的讀取目標格與原子寫入（research R3、R4）。"""

    async def read_cells(
        self, code: str, source: SourceRef, targets: Sequence[CellRef]
    ) -> Result[Mapping[CellRef, CurrentCell]]:
        """讀取各目標格目前的內容（`userEnteredValue`）；唯讀。

        Args:
            code: 活動代碼（授權依活動保存）。
            source: 來源識別。
            targets: 目標位置。

        Returns:
            成功時為各目標格內容；失敗時為 002 的 `ImportRejection`。
        """
        ...

    async def write_text_cells(
        self, code: str, source: SourceRef, cells: Sequence[tuple[CellRef, str]]
    ) -> WriteResult:
        """以單一原子請求把文字值寫入全部目標格，不更動格式與合併。

        Args:
            code: 活動代碼。
            source: 來源識別。
            cells: （目標位置, 答案原文）。

        Returns:
            成功、明確失敗或待確認；不得拋 Google 的例外。
        """
        ...


class ExportActivityGateway(Protocol):
    """005 用到的 001 介面。"""

    def export_view(self, code: str, requester: Requester) -> Outcome[ExportView]:
        """只限老師；已取消一律拒絕。"""
        ...

    def get(self, code: str) -> Activity | None:
        """取得活動。"""
        ...

    def add_snapshot_extension(
        self, extension: Callable[[Activity, Viewer], Mapping[str, object]]
    ) -> None:
        """註冊快照擴充。"""
        ...


class ImportRecords(Protocol):
    """005 用到的 002 介面。"""

    def get_import_record(self, code: str) -> ImportRecord | None:
        """最後一次成功匯入的記錄（唯讀）。"""
        ...


class SubmissionsReader(Protocol):
    """005 用到的 003 介面。"""

    def all_submissions(self, code: str) -> tuple[Submission, ...]:
        """全部輪次的有效提交（含未定案輪次）。"""
        ...


class RankingsReader(Protocol):
    """005 用到的 004 介面。"""

    def finalized_rounds(self, code: str) -> tuple[FinalizedRound, ...]:
        """已定案輪次（唯讀）。"""
        ...
