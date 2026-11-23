"""提交判定（純函式，003 研究 R10、data-model.md「判定順序」）。"""

from collections.abc import Iterable
from datetime import datetime

from lecture_quiz.core.round_submission.answer_rules import (
    MAX_ANSWER_CHARS,
    AnswerRules,
    InvalidAnswerError,
)
from lecture_quiz.core.round_submission.models import (
    DecisionKind,
    RoundContext,
    Submission,
    SubmissionAttempt,
    SubmissionDecision,
    SubmissionLedger,
    SubmissionRejection,
)

__all__ = [
    "DecisionKind",
    "SubmissionDecision",
    "SubmissionRejection",
    "SubmissionRules",
]


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _reject(
    rejection: SubmissionRejection,
    blank_numbers: tuple[int, ...] = (),
    expected_blanks: int | None = None,
) -> SubmissionDecision:
    return SubmissionDecision(
        DecisionKind.REJECTED,
        rejection=rejection,
        blank_numbers=blank_numbers,
        expected_blanks=expected_blanks,
    )


class SubmissionRules:
    """提交判定（純函式）；時間由呼叫端傳入，序號取自 ledger。"""

    @staticmethod
    def decide(
        ledger: SubmissionLedger,
        context: RoundContext,
        code: str,
        attempt: SubmissionAttempt,
        now: datetime,
    ) -> SubmissionDecision:
        """依固定順序判定一筆提交（研究 R10）。

        順序：輪次 → 是否接受 → 題號 → 本組已送出 → 答案 → 接受。

        Args:
            ledger: 目前的提交紀錄。
            context: 本輪資訊。
            code: 活動代碼。
            attempt: 學生送出的原始內容。
            now: 後端接收時間。

        Returns:
            判定結果；接受時 `submission.sequence == ledger.next_sequence`。
        """
        # 步驟 1：還沒有任何輪次 → 本輪尚未開始；輪次識別不是目前輪次 → 舊頁面
        if context.round_number is None:
            return _reject(SubmissionRejection.ROUND_CLOSED)
        if (
            not _is_int(attempt.round_number_raw)
            or attempt.round_number_raw != context.round_number
        ):
            return _reject(SubmissionRejection.STALE_ROUND)
        # 步驟 2：不在搶答中、已截止（now >= deadline）或已關輪（FR-014）
        if not context.accepting:
            return _reject(SubmissionRejection.ROUND_CLOSED)
        question = attempt.question_number_raw
        if (
            not _is_int(question)
            or question not in context.open_questions
            or question not in context.blanks_per_question
        ):
            return _reject(SubmissionRejection.QUESTION_NOT_OPEN)
        assert isinstance(question, int)
        # 步驟 4：本組本輪本題已有提交時一律回本組已送出，不看內容（FR-007、FR-009）
        existing = ledger.find(context.round_number, question, context.group_number)
        if existing is not None:
            return SubmissionDecision(
                DecisionKind.ALREADY_SUBMITTED, submission=existing
            )
        try:
            answers = AnswerRules.check(
                attempt.answers_raw, context.blanks_per_question[question]
            )
        except InvalidAnswerError as error:
            return _reject(error.rejection, error.blank_numbers, error.expected_blanks)
        submission = Submission(
            activity_code=code,
            round_number=context.round_number,
            question_number=question,
            group_number=context.group_number,
            answers=answers,
            received_at=now,
            sequence=ledger.next_sequence,
        )
        return SubmissionDecision(DecisionKind.ACCEPTED, submission=submission)

    @staticmethod
    def order(submissions: Iterable[Submission]) -> tuple[Submission, ...]:
        """依（接收時間, 接收序號）遞增排序（FR-018）；同一時間以序號定先後。

        Args:
            submissions: 任意順序的提交。

        Returns:
            排序後的 tuple。
        """
        return tuple(sorted(submissions, key=lambda s: (s.received_at, s.sequence)))

    @staticmethod
    def describe(decision: SubmissionDecision, attempt: SubmissionAttempt) -> str:
        """拒絕或本組已送出時給學生的中文訊息；不含 token 或他組資料。

        Args:
            decision: 判定結果。
            attempt: 學生送出的原始內容（只用來帶入題號）。

        Returns:
            訊息；接受時為空字串。
        """
        if decision.kind is DecisionKind.ALREADY_SUBMITTED:
            return "本組已送出這一題，以下是本組已保存的答案。"
        reason = decision.rejection
        if reason is None:
            return ""
        cells = "、".join(str(n) for n in decision.blank_numbers)
        question = attempt.question_number_raw
        if reason is SubmissionRejection.QUESTION_NOT_OPEN:
            if _is_int(question):
                return f"第 {question} 題不在本輪開放範圍，請選擇本輪開放的題目。"
            return "這一題不在本輪開放範圍，請選擇本輪開放的題目。"
        if reason is SubmissionRejection.WRONG_BLANK_COUNT:
            return f"這題需要 {decision.expected_blanks} 格答案，請重新整理後再作答。"
        if reason is SubmissionRejection.BLANK_EMPTY:
            return f"第 {cells} 格尚未填寫，請填好每一格再送出。"
        if reason is SubmissionRejection.ANSWER_TOO_LONG:
            return f"第 {cells} 格超過 {MAX_ANSWER_CHARS} 字，請縮短後再送出。"
        return _MESSAGES[reason]


_MESSAGES = {
    SubmissionRejection.ACTIVITY_GONE: "活動已失效，請重新加入活動。",
    SubmissionRejection.NOT_IN_GROUP: "這台裝置還沒有加入組別，請先加入組別。",
    SubmissionRejection.STALE_ROUND: "輪次已更新，請重新整理後再作答。",
    SubmissionRejection.ROUND_CLOSED: "本輪已結束（或尚未開始），不能再送出。",
    SubmissionRejection.INVALID_ANSWER: "答案格式不正確，請重新整理後再作答。",
}
