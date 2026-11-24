"""結果依角色裁切成快照欄位 `ranking`（純函式；contracts/sync-websocket.md）。

老師版含處理當下的成功次數、勝出理由、各組暫算次數與每題的 `actions`（前端只照它
顯示按鈕）；學生版（所有學生同一份）不含這些。資料公開、畫面限縮：學生畫面只顯示
哪些組由前端依 `successGroup`、`replacedGroup` 決定（spec FR-036）。
"""

from collections.abc import Sequence
from dataclasses import dataclass

from lecture_quiz.core.activity.snapshot_view import JsonDict
from lecture_quiz.core.ranking_review.models import (
    QuestionRanking,
    RankEntry,
    as_final,
)
from lecture_quiz.core.ranking_review.review import RoundReview


@dataclass(frozen=True)
class RoundView:
    """要輸出的一輪。

    Attributes:
        round_number: 輪次編號。
        fair_mode: 該輪開輪時固定的模式。
        review: 該輪的審閱狀態。
        final: 該輪是否已定案（001 階段與輪次判定，由呼叫端傳入）。
    """

    round_number: int
    fair_mode: bool
    review: RoundReview
    final: bool


def _replaced_last(review: RoundReview, question_number: int) -> int | None:
    history = review.replaced.get(question_number, ())
    return history[-1] if history else None


def _entry_json(entry: RankEntry, teacher: bool) -> JsonDict:
    body: JsonDict = {
        "groupNumber": entry.group_number,
        "rank": entry.rank,
        "judgedWrong": entry.wrong,
        "displayStatus": entry.display_status.value,
    }
    if teacher:
        body["countAtProcessing"] = entry.count_at_processing
        body["reason"] = entry.reason.value if entry.reason else None
    return body


def _question_json(
    ranking: QuestionRanking, view: RoundView, teacher: bool
) -> JsonDict:
    replaced = (
        None if view.final else _replaced_last(view.review, ranking.question_number)
    )
    if not teacher and ranking.success_group is None:
        replaced = None
    body: JsonDict = {
        "questionNumber": ranking.question_number,
        "successGroup": ranking.success_group,
        "replacedGroup": replaced,
    }
    if teacher:
        body["actions"] = {
            "judgeGroup": None if view.final else ranking.success_group,
            "undoGroup": None
            if view.final
            else _replaced_last(view.review, ranking.question_number),
        }
    body["entries"] = [_entry_json(e, teacher) for e in ranking.entries]
    return body


def _round_json(view: RoundView, teacher: bool) -> JsonDict:
    review = view.review
    rankings = (
        as_final(review.result.rankings) if view.final else review.result.rankings
    )
    body: JsonDict = {
        "roundNumber": view.round_number,
        "fairMode": view.fair_mode,
        "resultVersion": review.version,
        "final": view.final,
        "affectedQuestions": [] if view.final else sorted(review.affected),
        "questionOrder": list(review.result.order),
        "questions": [_question_json(r, view, teacher) for r in rankings],
    }
    if teacher:
        body["groupCounts"] = {
            str(g): c for g, c in sorted(review.result.group_counts.items())
        }
    return body


class ResultView:
    """依角色輸出 `ranking` 欄位內容的純函式。"""

    @staticmethod
    def for_teacher(rounds: Sequence[RoundView]) -> JsonDict:
        """老師版：完整候選情況（成功次數、理由、各組暫算次數、`actions`）。

        Args:
            rounds: 已關輪的輪次，依輪次遞增。

        Returns:
            `{"rounds": [...]}`。
        """
        return {"rounds": [_round_json(v, True) for v in rounds]}

    @staticmethod
    def for_student(rounds: Sequence[RoundView]) -> JsonDict:
        """學生版（所有學生同一份）：不含勝出理由、處理當下次數、暫算次數與 `actions`。

        Args:
            rounds: 已關輪的輪次，依輪次遞增。

        Returns:
            `{"rounds": [...]}`。
        """
        return {"rounds": [_round_json(v, False) for v in rounds]}
