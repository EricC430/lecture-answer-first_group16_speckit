"""US2：`ResultView` 的 JSON 形狀逐欄照 contracts/sync-websocket.md。"""

from lecture_quiz.core.ranking_review.models import RankingInput
from lecture_quiz.core.ranking_review.review import RoundReview
from lecture_quiz.core.ranking_review.view import ResultView, RoundView
from tests.unit.core.ranking_review.helpers import cand, inp


def _review(data: RankingInput) -> RoundReview:
    return RoundReview.initial(1, data)


def _data():
    return inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3)],
        questions=(1, 2),
        fair=True,
        baseline={1: 0, 2: 1},
    )


def _round(review, final=False):
    return RoundView(1, True, review, final)


def test_teacher_shape_has_all_fields():
    review = _review(_data())
    body = ResultView.for_teacher([_round(review)])
    assert list(body) == ["rounds"]
    first = body["rounds"][0]
    assert set(first) == {
        "roundNumber",
        "fairMode",
        "resultVersion",
        "final",
        "affectedQuestions",
        "questionOrder",
        "questions",
        "groupCounts",
    }
    assert first["roundNumber"] == 1 and first["fairMode"] is True
    assert first["resultVersion"] == 1 and first["final"] is False
    assert first["affectedQuestions"] == [] and first["questionOrder"] == [1, 2]
    q1, q2 = first["questions"]
    assert set(q1) == {
        "questionNumber",
        "successGroup",
        "replacedGroup",
        "actions",
        "entries",
    }
    assert q1["successGroup"] == 1 and q1["replacedGroup"] is None
    assert q1["actions"] == {"judgeGroup": 1, "undoGroup": None}
    assert q2 == {
        "questionNumber": 2,
        "successGroup": None,
        "replacedGroup": None,
        "actions": {"judgeGroup": None, "undoGroup": None},
        "entries": [],
    }
    entry = q1["entries"][0]
    assert set(entry) == {
        "groupNumber",
        "rank",
        "judgedWrong",
        "displayStatus",
        "countAtProcessing",
        "reason",
    }
    assert entry["displayStatus"] == "SUCCESS" and entry["rank"] == 1
    assert isinstance(first["groupCounts"], dict)
    assert all(isinstance(k, str) for k in first["groupCounts"])


def test_student_shape_has_no_reason_counts_or_actions():
    review = _review(_data())
    body = ResultView.for_student([_round(review)])
    first = body["rounds"][0]
    assert "groupCounts" not in first
    for question in first["questions"]:
        assert "actions" not in question
        for entry in question["entries"]:
            assert set(entry) == {"groupNumber", "rank", "judgedWrong", "displayStatus"}


def test_entries_list_ranked_first_then_wrong():
    data = inp(
        [cand(1, 1, 1, 1), cand(2, 1, 2, 2), cand(3, 1, 3, 3)],
        questions=(1,),
        wrong=[(1, 1)],
    )
    review = RoundReview.initial(1, inp(data.candidates, questions=(1,)))
    # 以含判錯的輸入直接計算結果（US4 的 mark 之前，用 initial 的輸入再加判錯）
    from lecture_quiz.core.ranking_review.ranking import RankingCalculator

    result = RankingCalculator.recompute(data, review.result.order)
    from dataclasses import replace

    judged = replace(review, wrong_marks=data.wrong_marks, result=result)
    entries = ResultView.for_student([_round(judged)])["rounds"][0]["questions"][0][
        "entries"
    ]
    assert [(e["groupNumber"], e["rank"], e["judgedWrong"]) for e in entries] == [
        (2, 1, False),
        (3, 2, False),
        (1, None, True),
    ]
    assert [e["displayStatus"] for e in entries] == ["SUCCESS", "FAILED", "WRONG"]


def test_final_turns_success_into_correct_and_clears_buttons():
    review = _review(_data())
    body = ResultView.for_teacher([_round(review, final=True)])
    first = body["rounds"][0]
    assert first["final"] is True and first["affectedQuestions"] == []
    q1 = first["questions"][0]
    assert q1["entries"][0]["displayStatus"] == "CORRECT"
    assert q1["actions"] == {"judgeGroup": None, "undoGroup": None}
    assert q1["replacedGroup"] is None
    student = ResultView.for_student([_round(review, final=True)])
    assert (
        student["rounds"][0]["questions"][0]["entries"][0]["displayStatus"] == "CORRECT"
    )
