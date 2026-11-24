"""US5：關輪後公開本輪提交，歷史可查但不洩漏新輪（研究 R11）。"""

import json
from datetime import timedelta

from lecture_quiz.core.activity.commands import CloseRound, Finalize, OpenRound
from lecture_quiz.core.activity.models import Activity, Stage
from lecture_quiz.core.activity.state_machine import ActivityStateMachine
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


def _apply(activity: Activity, command, offset_s: int = 0) -> Activity:
    transition = ActivityStateMachine.apply(
        activity, command, NOW + timedelta(seconds=offset_s)
    )
    assert transition.ok and transition.activity is not None, transition
    return transition.activity


def _round1_closed() -> Activity:
    """題 1～4、第 1～3 組；第 1 輪開放題 1、2 後關輪（結果未定案）。"""
    base = with_groups(with_questions(joining_activity(), 1, 2, 3, 4), 1, 2, 3)
    opened = _apply(base, OpenRound(TEACHER, (1, 2), False, None))
    return _apply(opened, CloseRound(TEACHER), 60)


def _round2_open() -> Activity:
    finalized = _apply(_round1_closed(), Finalize(TEACHER), 61)
    return _apply(finalized, OpenRound(TEACHER, (1, 2), False, None), 62)


def _round1_ledger() -> SubmissionLedger:
    subs = (
        make_submission(group_number=2, answers=("乙1", "乙2"), offset_ms=10),
        make_submission(
            group_number=1, answers=("甲1", "甲2"), offset_ms=20, sequence=2
        ),
    )
    return SubmissionLedger(subs, next_sequence=3)


def _with_round2(ledger: SubmissionLedger) -> SubmissionLedger:
    for sub in (
        make_submission(
            round_number=2,
            group_number=1,
            answers=("甲新1", "甲新2"),
            offset_ms=70_000,
            sequence=3,
        ),
        make_submission(
            round_number=2,
            group_number=2,
            answers=("乙新1", "乙新2"),
            offset_ms=70_010,
            sequence=4,
        ),
    ):
        ledger = ledger.with_added(sub)
    return ledger


def _expected_round1(judged_wrong: bool = True) -> dict[str, object]:
    def entry(group: int, answers: list[str], ms: int, order: int) -> dict:
        item: dict[str, object] = {
            "groupNumber": group,
            "answers": answers,
            "receivedAt": f"2026-11-21T09:00:00.0{ms}+08:00",
            "order": order,
        }
        if judged_wrong:
            item["judgedWrong"] = False
        return item

    return {
        "roundNumber": 1,
        "questions": [
            {
                "questionNumber": 1,
                "noSubmission": False,
                "entries": [
                    entry(2, ["乙1", "乙2"], 10, 1),
                    entry(1, ["甲1", "甲2"], 20, 2),
                ],
            },
            {"questionNumber": 2, "noSubmission": True, "entries": []},
        ],
    }


def test_closed_round_is_published_to_every_group():
    """Scenario: US5-AS1、US5-AS2（OpenSpec「結果公布與後續輪次」）。

    關輪後各組都看得到全部組的提交與先後；無人提交的題 `noSubmission: true`。
    """
    activity = _round1_closed()
    assert activity.stage is Stage.RESULT_PENDING
    for group in (1, 3):
        fields = SubmissionView.for_group(_round1_ledger(), activity, group)
        assert fields["submissions"] == {
            "current": None,
            "published": [_expected_round1()],
        }
    teacher = SubmissionView.for_teacher(_round1_ledger(), activity)
    assert teacher["submissions"] == {
        "current": None,
        "published": [_expected_round1()],
    }


def test_judged_wrong_field_follows_constant():
    """Scenario: US5-AS5（Q-26）：每筆都有 `judgedWrong`，003 一律為 false。

    `STUDENT_SEES_JUDGED_WRONG` 為假時學生版不含此欄位，老師版仍有。
    """
    activity = _round1_closed()
    hidden = SubmissionView.for_group(
        _round1_ledger(), activity, 1, student_sees_judged_wrong=False
    )
    assert hidden["submissions"]["published"] == [_expected_round1(False)]
    assert "judgedWrong" not in json.dumps(hidden)
    teacher = SubmissionView.for_teacher(_round1_ledger(), activity)
    assert "judgedWrong" in json.dumps(teacher)


def test_history_visible_but_new_round_stays_private():
    """Scenario: US5-AS3：第 2 輪開放中，甲組有第 1 輪公開資料，current 只有自己。"""
    activity = _round2_open()
    ledger = _with_round2(_round1_ledger())
    fields = SubmissionView.for_group(ledger, activity, 1)
    assert fields["submissions"]["published"] == [_expected_round1()]
    current = fields["submissions"]["current"]
    assert current["roundNumber"] == 2
    assert [s["answers"] for s in current["own"]] == [["甲新1", "甲新2"]]
    assert "乙新" not in json.dumps(fields, ensure_ascii=False)
    teacher = SubmissionView.for_teacher(ledger, activity)
    assert teacher["submissions"]["published"] == [_expected_round1()]
    q1 = teacher["submissions"]["current"]["questions"][0]
    assert [e["groupNumber"] for e in q1["entries"]] == [1, 2]


def test_published_rounds_are_in_ascending_order():
    """多個已公開輪次依輪次遞增；只列出該輪開放的題。"""
    finalized = _apply(_round2_open(), CloseRound(TEACHER), 120)
    ledger = _with_round2(_round1_ledger())
    published = SubmissionView.for_group(ledger, finalized, 3)["submissions"][
        "published"
    ]
    assert [r["roundNumber"] for r in published] == [1, 2]
    assert [q["questionNumber"] for q in published[1]["questions"]] == [1, 2]
    assert [e["groupNumber"] for e in published[1]["questions"][0]["entries"]] == [
        1,
        2,
    ]
