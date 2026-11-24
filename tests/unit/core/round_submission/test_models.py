"""003 核心資料結構：`SubmissionLedger` 與不可變性（data-model.md）。"""

import dataclasses

import pytest

from lecture_quiz.core.round_submission.models import (
    RoundContext,
    SubmissionLedger,
)
from tests.unit.core.round_submission.helpers import (
    make_attempt,
    make_context,
    make_submission,
)


def test_empty_ledger_starts_at_sequence_one():
    ledger = SubmissionLedger()
    assert ledger.submissions == ()
    assert ledger.next_sequence == 1


def test_with_added_returns_new_ledger_and_advances_sequence():
    ledger = SubmissionLedger()
    sub = make_submission(sequence=1)
    added = ledger.with_added(sub)
    assert added is not ledger
    assert ledger.submissions == () and ledger.next_sequence == 1
    assert added.submissions == (sub,)
    assert added.next_sequence == 2


def test_find_by_round_question_group():
    sub = make_submission(round_number=1, question_number=2, group_number=3)
    ledger = SubmissionLedger().with_added(sub)
    assert ledger.find(1, 2, 3) == sub
    assert ledger.find(2, 2, 3) is None
    assert ledger.find(1, 1, 3) is None
    assert ledger.find(1, 2, 1) is None


def test_for_round_returns_only_that_round():
    first = make_submission(round_number=1, sequence=1)
    second = make_submission(round_number=2, sequence=2)
    ledger = SubmissionLedger().with_added(first).with_added(second)
    assert ledger.for_round(1) == (first,)
    assert ledger.for_round(2) == (second,)
    assert ledger.for_round(3) == ()


def test_types_are_frozen():
    for value, attr in (
        (make_submission(), "answers"),
        (SubmissionLedger(), "next_sequence"),
        (make_context(), "accepting"),
        (make_attempt(), "answers_raw"),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(value, attr, None)


def test_round_context_freezes_blanks():
    blanks = {1: 2}
    context = RoundContext(1, 1, (1,), True, blanks)
    blanks[1] = 5
    assert context.blanks_per_question[1] == 2
    with pytest.raises(TypeError):
        context.blanks_per_question[1] = 3  # type: ignore[index]
