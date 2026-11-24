"""核心型別（共用基礎，Scenario 不適用）。"""

import dataclasses

import pytest

from lecture_quiz.core.guided_notes_import.models import CellRef
from lecture_quiz.core.result_export.models import (
    BlankTarget,
    CellCheck,
    CellKind,
    CurrentCell,
    DiffKind,
    ExportRow,
    FinalizedEntry,
    FinalizedQuestion,
    OutcomeStatus,
    OverwriteImpact,
    Reconciliation,
    ResultSnapshot,
    StructureCheck,
    StructureDifference,
    SubmissionFact,
    WritePlanItem,
)
from tests.unit.core.result_export.helpers import T0


def _instances():
    item = WritePlanItem(
        1, 1, None, 1, "答", CellRef(0, 0), OverwriteImpact.EMPTY, None
    )
    return [
        FinalizedEntry(1, 1, 1, 1, False),
        FinalizedQuestion(1, 1, 1),
        SubmissionFact(1, 1, 1, ("a",), T0),
        BlankTarget(1, None, CellRef(0, 0)),
        CurrentCell(CellKind.EMPTY, None, ""),
        item,
        ResultSnapshot("1", (item,), (2,)),
        StructureDifference(DiffKind.IDENTITY, None, "x"),
        StructureCheck(True, ()),
        CellCheck(1, None, "a", "a", True),
        Reconciliation(OutcomeStatus.SUCCESS, ()),
        ExportRow(1, 1, None, 1, "a", T0, 1, True, False),
    ]


def test_all_core_types_are_frozen():
    for obj in _instances():
        field = dataclasses.fields(obj)[0].name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, field, "changed")


def test_enum_members_match_data_model():
    assert {m.name for m in OverwriteImpact} == {"EMPTY", "REPLACE", "SAME"}
    assert {m.name for m in CellKind} == {"EMPTY", "TEXT", "OTHER"}
    assert {m.name for m in OutcomeStatus} == {"SUCCESS", "FAILED", "PENDING"}
    assert {m.name for m in DiffKind} == {
        "IDENTITY",
        "UNRECOGNIZED",
        "HEADER_POSITION",
        "QUESTION_NUMBER",
        "SUB_BLANK",
        "ANSWER_CELL",
        "MERGE_RANGE",
    }


def test_snapshot_collections_are_tuples():
    snapshot = _instances()[6]
    assert isinstance(snapshot.items, tuple)
    assert isinstance(snapshot.unwritten_questions, tuple)
