"""固定題目處理順序（FR-004、FR-005）。"""

from collections.abc import Iterable

from lecture_quiz.core.ranking_review.models import Candidate


class QuestionOrder:
    """題序計算的純函式。"""

    @staticmethod
    def compute(
        question_numbers: Iterable[int], candidates: Iterable[Candidate]
    ) -> tuple[int, ...]:
        """以每題最早已接受提交的（接收時間, 接收序號）固定本輪題序。

        每題取該題全部候選（不論之後是否被判錯）中最早的一筆作為依據，依據由早到晚
        排列；沒有任何已接受提交的題接在後面，依題號由小到大排列。題序只在關輪時決定
        一次，之後判錯與撤銷都不會移動它。

        Args:
            question_numbers: 本輪題號。
            candidates: 本輪全部已接受的提交。

        Returns:
            依處理順序排列的題號。
        """
        earliest: dict[int, tuple[object, int]] = {}
        for c in candidates:
            key = (c.received_at, c.sequence)
            current = earliest.get(c.question_number)
            if current is None or key < current:  # type: ignore[operator]
                earliest[c.question_number] = key  # type: ignore[assignment]
        with_submissions = sorted(
            (q for q in question_numbers if q in earliest),
            key=lambda q: earliest[q],  # type: ignore[arg-type,return-value]
        )
        without = sorted(q for q in question_numbers if q not in earliest)
        return (*with_submissions, *without)
