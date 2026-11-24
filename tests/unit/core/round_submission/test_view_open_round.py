"""US4：搶答中的可見性（`SubmissionView`，contracts/sync-websocket.md）。"""

import json

from lecture_quiz.core.activity.commands import OpenRound
from lecture_quiz.core.activity.models import Activity
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
from lecture_quiz.core.round_submission import view
from lecture_quiz.core.round_submission.models import SubmissionLedger
from lecture_quiz.core.round_submission.view import SubmissionView
from tests.unit.core.helpers import (
    NOW,
    TEACHER,
    joining_activity,
    with_groups,
    with_questions,
)
from tests.unit.core.round_submission.helpers import make_submission


def _open(questions=(1, 2, 3, 4), groups=(1, 2, 3)) -> Activity:
    base = with_groups(with_questions(joining_activity(), 1, 2, 3, 4), *groups)
    transition = ActivityStateMachine.apply(
        base, OpenRound(TEACHER, questions, False, None), NOW
    )
    assert transition.ok and transition.activity is not None
    return transition.activity


def _ledger():
    subs = (
        make_submission(
            group_number=2,
            question_number=1,
            answers=("乙1", "乙2"),
            offset_ms=10,
            sequence=1,
        ),
        make_submission(
            group_number=1,
            question_number=1,
            answers=("甲1", "甲2"),
            offset_ms=20,
            sequence=2,
        ),
        make_submission(
            group_number=1,
            question_number=3,
            answers=("甲3",),
            offset_ms=30,
            sequence=3,
        ),
    )
    return SubmissionLedger(subs, next_sequence=4)


def test_constants_are_centralised():
    """Q-21、Q-22、Q-26 的可見性規則集中在 view.py 頂端。"""
    assert view.TEACHER_SEES_PROVISIONAL_RANKING_DURING_ROUND is False
    assert view.STUDENT_SEES_OWN_SUCCESS_DURING_ROUND is True
    assert view.STUDENT_SEES_JUDGED_WRONG is True


def test_student_sees_only_own_group():
    """Scenario: US4-AS1、US4-AS3（OpenSpec「檢查學生資料回應」）。"""
    fields = SubmissionView.for_group(_ledger(), _open(), 1)
    current = fields["submissions"]["current"]
    assert current == {
        "roundNumber": 1,
        "open": True,
        "own": [
            {
                "questionNumber": 1,
                "answers": ["甲1", "甲2"],
                "receivedAt": "2026-11-21T09:00:00.020+08:00",
            },
            {
                "questionNumber": 3,
                "answers": ["甲3"],
                "receivedAt": "2026-11-21T09:00:00.030+08:00",
            },
        ],
    }
    assert fields["submissions"]["published"] == []
    text = json.dumps(fields, ensure_ascii=False)
    for leaked in ("乙1", "乙2", "09:00:00.010", "groupNumber", "order", "entries"):
        assert leaked not in text
    assert "ownGroup" not in fields  # Q-22：沿用 001 的 successCount


def test_student_success_count_can_be_hidden():
    """STUDENT_SEES_OWN_SUCCESS_DURING_ROUND 為假時把本組成功次數改為 null。"""
    fields = SubmissionView.for_group(
        _ledger(), _open(), 1, student_sees_own_success=False
    )
    assert fields["ownGroup"]["successCount"] is None
    assert fields["ownGroup"]["number"] == 1


def test_teacher_sees_all_groups_with_order_but_no_rank():
    """Scenario: US4-AS4、US4-AS5（老師看板：全部組、送出先後，沒有暫估順位）。"""
    fields = SubmissionView.for_teacher(_ledger(), _open())
    current = fields["submissions"]["current"]
    assert current["roundNumber"] == 1 and current["open"] is True
    questions = {q["questionNumber"]: q for q in current["questions"]}
    assert list(questions) == [1, 2, 3, 4]
    assert [(e["groupNumber"], e["order"]) for e in questions[1]["entries"]] == [
        (2, 1),
        (1, 2),
    ]
    assert questions[1]["entries"][0]["answers"] == ["乙1", "乙2"]
    assert questions[2] == {"questionNumber": 2, "noSubmission": True, "entries": []}
    assert questions[3]["noSubmission"] is False
    text = json.dumps(fields)
    assert "rank" not in text and "winner" not in text


def test_no_current_round_outside_round_open():
    """還沒開輪時沒有 current。"""
    activity = with_groups(joining_activity(), 1)
    for fields in (
        SubmissionView.for_teacher(SubmissionLedger(), activity),
        SubmissionView.for_group(SubmissionLedger(), activity, 1),
    ):
        assert fields["submissions"] == {"current": None, "published": []}
