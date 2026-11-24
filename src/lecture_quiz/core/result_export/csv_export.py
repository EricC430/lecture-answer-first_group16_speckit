"""CSV 資料列與文字（純函式；FR-023～FR-028）。

只處理傳入的已定案輪次資料；順位、搶答成功者與答錯標記以 004 的定案結果為準，這裡
不重新計算。標準函式庫 `csv` 負責逗號、雙引號與換行的跳脫。
"""

import csv
import io
from collections.abc import Sequence

from lecture_quiz.core.result_export.models import (
    BlankTarget,
    ExportRow,
    FinalizedEntry,
    SubmissionFact,
)

HEADER = (
    "輪次",
    "題號",
    "子空格",
    "組別",
    "答案",
    "送出時間",
    "順位",
    "是否成功",
    "是否被判錯",
)
"""欄位順序（spec FR-024）。"""

FORMULA_LEADS = ("=", "+", "-", "@", "\t", "\r")
"""會被試算表軟體解讀為公式的開頭字元。"""

PROTECT_PREFIX = "'"
"""文字保護前綴。"""


def protect_text(value: str) -> str:
    """以公式字元開頭的文字前面加保護前綴，避免試算表軟體執行它。

    Args:
        value: 不可信文字（組別、答案）。

    Returns:
        需要保護時為前綴加原文，否則原樣。
    """
    if value.startswith(FORMULA_LEADS):
        return PROTECT_PREFIX + value
    return value


def build_rows(
    entries: Sequence[FinalizedEntry],
    submissions: Sequence[SubmissionFact],
    blanks: Sequence[BlankTarget],
) -> tuple[ExportRow, ...]:
    """把已定案候選展開成 CSV 資料列（每個提交子空格一列）。

    Args:
        entries: 已定案輪次的全部候選（含搶答失敗與答錯）。
        submissions: 已接受提交；多出的（沒有對應候選的）不會產生列。
        blanks: 002 的來源映射，用來決定每題的子空格。

    Returns:
        依（輪次, 題號, 被判錯者排後, 順位, 接收時間, 組號, 子編號）排序的資料列。

    Raises:
        ValueError: 候選找不到對應提交、題號沒有來源映射或答案數與格數不符。
    """
    by_submission = {
        (s.round_number, s.question_number, s.group_number): s for s in submissions
    }
    by_question: dict[int, list[BlankTarget]] = {}
    for blank in blanks:
        by_question.setdefault(blank.question_number, []).append(blank)
    for group in by_question.values():
        group.sort(key=lambda b: b.sub_index or 0)
    rows: list[ExportRow] = []
    for e in entries:
        fact = by_submission.get((e.round_number, e.question_number, e.group_number))
        if fact is None:
            raise ValueError("找不到候選對應的提交")
        targets = by_question.get(e.question_number)
        if not targets or len(fact.answers) != len(targets):
            raise ValueError("答案數與格數不符")
        for blank, answer in zip(targets, fact.answers, strict=True):
            rows.append(
                ExportRow(
                    e.round_number,
                    e.question_number,
                    blank.sub_index,
                    e.group_number,
                    answer,
                    fact.received_at,
                    e.rank,
                    e.rank == 1 and not e.judged_wrong,
                    e.judged_wrong,
                )
            )
    rows.sort(
        key=lambda r: (
            r.round_number,
            r.question_number,
            r.rank is None,
            r.rank or 0,
            r.received_at,
            r.group_number,
            r.sub_index or 0,
        )
    )
    return tuple(rows)


def _yes_no(value: bool) -> str:
    return "是" if value else "否"


def render_csv(rows: Sequence[ExportRow]) -> str:
    """產生 CSV 文字（CRLF 行結尾；BOM 與編碼由轉接層處理）。

    只有「組別」與「答案」套用文字保護；系統產生的欄位不加前綴。

    Args:
        rows: 資料列。

    Returns:
        含表頭的 CSV 文字。
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(HEADER)
    for r in rows:
        writer.writerow(
            [
                str(r.round_number),
                str(r.question_number),
                "" if r.sub_index is None else str(r.sub_index),
                protect_text(str(r.group_number)),
                protect_text(r.answer),
                r.received_at.isoformat(timespec="milliseconds"),
                "" if r.rank is None else str(r.rank),
                _yes_no(r.succeeded),
                _yes_no(r.judged_wrong),
            ]
        )
    return buffer.getvalue()
