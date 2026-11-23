"""50 題、數百列的學習單解析結果正確（SC-006 的前提）。

這只驗證核心解析在規模下結果正確與沒有退化；SC-006 的「確認工作表到看見預覽 10 秒」
包含網路讀取，要在真實路徑驗證（quickstart）記錄實際秒數，不用 mock 的耗時冒充。
"""

import time

from lecture_quiz.core.guided_notes_import.parser import GuidedNotesParser
from tests.fixtures.guided_notes_layouts import from_items


def build_items(count: int):
    items: list[tuple[str, int, int | None]] = []
    for number in range(1, count + 1):
        if number % 3 == 0:
            items.append(("single", number, None))
        else:
            items.extend([("sub", number, 1), ("sub", number, 2), ("sub", number, 3)])
        items.extend([("note", 0, None), ("blank", 0, None)])  # 每題後面夾間隔列
    return items


def test_fifty_questions_with_hundreds_of_rows():
    items = build_items(50)
    assert len(items) > 200  # 數百列
    snapshot, expected = from_items(items, repeated=False, merge_over_trailing=True)
    started = time.perf_counter()
    result = GuidedNotesParser.parse(snapshot)
    elapsed = time.perf_counter() - started
    assert result.ok, result.issues[:3]
    assert len(result.questions) == 50
    assert len(result.blanks) == expected.total_blanks
    assert tuple((q.number, q.blank_count, q.is_group) for q in result.questions) == (
        expected.questions
    )
    assert elapsed < 2.0, f"核心解析 {elapsed:.2f} 秒（只計算解析，不含網路）"


def test_fifty_questions_repeated_numbers_gives_same_result():
    items = build_items(50)
    merged, _ = from_items(items, repeated=False, merge_over_trailing=True)
    repeated, _ = from_items(items, repeated=True)
    a = GuidedNotesParser.parse(merged)
    b = GuidedNotesParser.parse(repeated)
    assert a.ok and b.ok
    assert a.questions == b.questions and a.blanks == b.blanks
