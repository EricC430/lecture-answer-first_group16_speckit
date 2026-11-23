"""提交資料依角色裁切成快照欄位（純函式；contracts/sync-websocket.md）。

可見性規則集中在本檔頂端，OpenSpec 組決議改變時只改這裡（alignment 2026-11-23）。
"""

from collections.abc import Iterable
from datetime import datetime

from lecture_quiz.core.activity.models import Activity, Stage
from lecture_quiz.core.round_submission.models import Submission, SubmissionLedger
from lecture_quiz.core.round_submission.rules import SubmissionRules

# Q-21：搶答中老師看板只顯示送出先後（order），不顯示暫估順位或暫定勝者。
TEACHER_SEES_PROVISIONAL_RANKING_DURING_ROUND = False
# Q-22（修正 B）：搶答中學生看得到本組成功次數（沿用 001 的 ownGroup.successCount）。
STUDENT_SEES_OWN_SUCCESS_DURING_ROUND = True
# Q-26：關輪公開後學生看得到判錯標記（judgedWrong，由 004 提供）。
STUDENT_SEES_JUDGED_WRONG = True

JsonDict = dict[str, object]


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds")


def _open_round_number(activity: Activity) -> int | None:
    """本輪開放中時回傳輪次編號，否則 `None`。"""
    current = activity.current_round
    if activity.stage is Stage.ROUND_OPEN and current is not None:
        return current.number
    return None


def _question_entries(submissions: Iterable[Submission]) -> list[JsonDict]:
    ordered = SubmissionRules.order(submissions)
    return [
        {
            "groupNumber": s.group_number,
            "answers": list(s.answers),
            "receivedAt": _iso(s.received_at),
            "order": index,
        }
        for index, s in enumerate(ordered, start=1)
    ]


class SubmissionView:
    """把提交紀錄轉成老師版或學生版的快照欄位（`submissions`）。"""

    @staticmethod
    def for_teacher(ledger: SubmissionLedger, activity: Activity) -> JsonDict:
        """老師版：本輪開放中時列出每題每組的提交與送出先後。

        `order` 是依（接收時間, 接收序號）的送出先後，不是順位（Q-21）。

        Args:
            ledger: 活動的提交紀錄。
            activity: 活動。

        Returns:
            `{"submissions": {"current": ..., "published": [...]}}`。
        """
        round_number = _open_round_number(activity)
        current: JsonDict | None = None
        if round_number is not None:
            current_round = activity.current_round
            assert current_round is not None
            in_round = ledger.for_round(round_number)
            questions: list[JsonDict] = []
            for question in current_round.rules.question_numbers:
                entries = _question_entries(
                    s for s in in_round if s.question_number == question
                )
                questions.append(
                    {
                        "questionNumber": question,
                        "noSubmission": not entries,
                        "entries": entries,
                    }
                )
            current = {
                "roundNumber": round_number,
                "open": True,
                "questions": questions,
            }
        return {"submissions": {"current": current, "published": []}}

    @staticmethod
    def for_group(
        ledger: SubmissionLedger,
        activity: Activity,
        group_number: int,
        *,
        student_sees_own_success: bool = STUDENT_SEES_OWN_SUCCESS_DURING_ROUND,
    ) -> JsonDict:
        """學生版：本輪開放中時只有本組的提交（FR-021）。

        不含他組的答案、狀態、時間、數量或先後。

        Args:
            ledger: 活動的提交紀錄。
            activity: 活動。
            group_number: 請求者所屬的組號。
            student_sees_own_success: 搶答中是否顯示本組成功次數（Q-22）；
                為假時覆寫 `ownGroup.successCount` 為 `None`。

        Returns:
            要併入學生快照的欄位。
        """
        round_number = _open_round_number(activity)
        current: JsonDict | None = None
        if round_number is not None:
            own = sorted(
                (
                    s
                    for s in ledger.for_round(round_number)
                    if s.group_number == group_number
                ),
                key=lambda s: s.question_number,
            )
            current = {
                "roundNumber": round_number,
                "open": True,
                "own": [
                    {
                        "questionNumber": s.question_number,
                        "answers": list(s.answers),
                        "receivedAt": _iso(s.received_at),
                    }
                    for s in own
                ],
            }
        fields: JsonDict = {"submissions": {"current": current, "published": []}}
        group = activity.groups.get(group_number)
        if round_number is not None and not student_sees_own_success and group:
            fields["ownGroup"] = {
                "number": group.number,
                "credential": group.join_credential,
                "successCount": None,
            }
        return fields
