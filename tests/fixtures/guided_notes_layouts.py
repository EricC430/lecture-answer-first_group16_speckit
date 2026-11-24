"""手寫、依 OpenSpec 與課程範本描述的學習單版面（核心解析測試用）。

**這不是真實 Google 回應**：全部由 `Sheet` 小工具逐格手寫，用來驗證解析規則。
真實 `spreadsheets.get` 回應 fixture 只在真實驗證（quickstart B 區）通過後才由
`scripts/capture_real_fixture.py` 擷取（plan「待真實驗證的假設」）；
擷取之前不得宣稱入口路徑已驗證。

座標都是 0 起算的絕對（列, 欄），已包含 `origin` 的平移。
"""

from dataclasses import dataclass, field

from lecture_quiz.core.guided_notes_import.models import IssueKind, SheetSnapshot
from tests.unit.core.guided_notes_import.helpers import Sheet

NUM_COL = 1
DESC_COL = 2
ANS_FIRST = 6
ANS_LAST = 7
HEADER_ROW = 3


@dataclass(frozen=True)
class Expected:
    """版面預期的解析結果。

    Attributes:
        questions: (題號, 空格數, 是否題組)。
        blanks: (題號, 子編號, (列, 欄))。
    """

    questions: tuple[tuple[int, int, bool], ...]
    blanks: tuple[tuple[int, int | None, tuple[int, int]], ...]

    @property
    def total_blanks(self) -> int:
        """總空格數。"""
        return len(self.blanks)


# ── 課程範本題組版（版面 A）──────────────────────────────────────


def layout_a(
    origin: tuple[int, int] = (0, 0), sheet_name: str = "學習單"
) -> tuple[SheetSnapshot, Expected]:
    """課程範本：前兩題各兩個子空格（題號縱向合併）、後兩題各一格 → 4 題 6 格。

    題號在 B 欄、作答表頭合併 G:H；子編號在 G 欄、作答格在 H 欄（編號右側）；
    單題的作答格是合併的 G:H，位置為左上角 G。
    """
    dr, dc = origin
    s = Sheet(10, 8)
    s.set(0, 0, "Week 3 學習單")
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, DESC_COL, "題目")
    s.set(HEADER_ROW, ANS_FIRST, "作答").merge(
        HEADER_ROW, ANS_FIRST, HEADER_ROW, ANS_LAST
    )
    s.set(4, NUM_COL, 1.0).merge(4, NUM_COL, 5, NUM_COL)
    s.set(4, DESC_COL, "敘述 1").set(5, DESC_COL, "敘述 1 續")
    s.set(4, ANS_FIRST, "(1)").set(5, ANS_FIRST, "(2)")
    s.set(6, NUM_COL, 2.0).merge(6, NUM_COL, 7, NUM_COL)
    s.set(6, ANS_FIRST, "（1）").set(7, ANS_FIRST, "(2)")
    s.set(8, NUM_COL, 3.0).merge(8, ANS_FIRST, 8, ANS_LAST)
    s.set(9, NUM_COL, 4.0).merge(9, ANS_FIRST, 9, ANS_LAST)
    expected = Expected(
        questions=((1, 2, True), (2, 2, True), (3, 1, False), (4, 1, False)),
        blanks=(
            (1, 1, (4 + dr, ANS_LAST + dc)),
            (1, 2, (5 + dr, ANS_LAST + dc)),
            (2, 1, (6 + dr, ANS_LAST + dc)),
            (2, 2, (7 + dr, ANS_LAST + dc)),
            (3, None, (8 + dr, ANS_FIRST + dc)),
            (4, None, (9 + dr, ANS_FIRST + dc)),
        ),
    )
    return s.snapshot(sheet_name, origin), expected


def layout_b() -> tuple[SheetSnapshot, Expected]:
    """版面 B：整體移位、工作表更名、數字用文字、題組逐列重複題號、單題與題組混合。

    4 題 7 格：題 1 單題、題 2 兩個子空格、題 3 三個子空格、題 4 單題。
    """
    dr, dc = 6, 3
    s = Sheet(9, 7)
    s.set(0, 0, "Week2 筆記")
    s.set(1, 0, "　題號　").set(1, 1, "內容")
    s.set(1, 4, " 作答 ").merge(1, 4, 1, 6)
    s.set(2, 0, "1").merge(2, 4, 2, 6)
    for row, number, sub in (
        (3, 2.0, "(1)"),
        (4, 2.0, "(2)"),
        (5, 3.0, "(1)"),
        (6, 3.0, "(2)"),
        (7, 3.0, "(3)"),
    ):
        s.set(row, 0, number).set(row, 4, sub)
    s.set(8, 0, " 4 ").merge(8, 4, 8, 6)
    expected = Expected(
        questions=((1, 1, False), (2, 2, True), (3, 3, True), (4, 1, False)),
        blanks=(
            (1, None, (2 + dr, 4 + dc)),
            (2, 1, (3 + dr, 5 + dc)),
            (2, 2, (4 + dr, 5 + dc)),
            (3, 1, (5 + dr, 5 + dc)),
            (3, 2, (6 + dr, 5 + dc)),
            (3, 3, (7 + dr, 5 + dc)),
            (4, None, (8 + dr, 4 + dc)),
        ),
    )
    return s.snapshot("Week2筆記", (dr, dc)), expected


def single_template(
    origin: tuple[int, int] = (2, 1), sheet_name: str = "單題"
) -> tuple[SheetSnapshot, Expected]:
    """單題範本：六題、作答格橫向合併 → 6 題 6 格，位置為合併範圍左上角。"""
    dr, dc = origin
    s = Sheet(9, 10)
    s.set(2, 1, "題號").set(2, 2, "題目")
    s.set(2, 4, "作答").merge(2, 4, 2, 8)
    for i in range(1, 7):
        row = 2 + i
        s.set(row, 1, float(i)).set(row, 2, f"題目 {i}").merge(row, 4, row, 8)
    expected = Expected(
        questions=tuple((i, 1, False) for i in range(1, 7)),
        blanks=tuple((i, None, (2 + i + dr, 4 + dc)) for i in range(1, 7)),
    )
    return s.snapshot(sheet_name, origin), expected


# ── 以項目清單組出的題組變體 ──────────────────────────────────────


def from_items(
    items: list[tuple[str, int, int | None]],
    *,
    repeated: bool = False,
    merge_over_trailing: bool = False,
    origin: tuple[int, int] = (0, 0),
    sheet_name: str = "變體",
) -> tuple[SheetSnapshot, Expected]:
    """依項目清單逐列組出學習單（版面同範本 A 的欄位配置）。

    項目：`("sub", 題號, 子編號)`、`("single", 題號, None)`、
    `("blank", 0, None)`（完全空白列）、
    `("note", 0, None)`（只有題目敘述、沒有題號也沒有子編號的間隔列）。

    Args:
        items: 由上而下的列。
        repeated: 為真時每個題目列都明寫題號（相鄰重複），否則題組用縱向合併。
        merge_over_trailing: 縱向合併時，是否把題目之後的空白列與間隔列一併包進範圍。
        origin: 整體平移。
        sheet_name: 工作表名稱。

    Returns:
        (快照, 預期結果)。
    """
    dr, dc = origin
    rows = HEADER_ROW + 1 + len(items) + 1
    s = Sheet(rows, 8)
    s.set(HEADER_ROW, NUM_COL, "題號").set(HEADER_ROW, DESC_COL, "題目")
    s.set(HEADER_ROW, ANS_FIRST, "作答").merge(
        HEADER_ROW, ANS_FIRST, HEADER_ROW, ANS_LAST
    )
    placed: list[tuple[int, str, int, int | None]] = []
    for offset, (kind, number, sub) in enumerate(items):
        placed.append((HEADER_ROW + 1 + offset, kind, number, sub))
    by_question: dict[int, list[int]] = {}
    blanks: list[tuple[int, int | None, tuple[int, int]]] = []
    for row, kind, number, sub in placed:
        if kind in ("sub", "single"):
            by_question.setdefault(number, []).append(row)
            if kind == "sub":
                s.set(row, ANS_FIRST, f"({sub})")
                blanks.append((number, sub, (row + dr, ANS_LAST + dc)))
            else:
                s.merge(row, ANS_FIRST, row, ANS_LAST)
                blanks.append((number, None, (row + dr, ANS_FIRST + dc)))
            if repeated:
                s.set(row, NUM_COL, float(number))
        elif kind == "note":
            s.set(row, DESC_COL, "（說明文字）")
    if not repeated:
        for number, qrows in by_question.items():
            first, last = qrows[0], qrows[-1]
            if merge_over_trailing:
                nxt = last + 1
                while nxt < rows and any(
                    r == nxt and k in ("blank", "note") for r, k, _, _ in placed
                ):
                    nxt += 1
                last = nxt - 1
            s.set(first, NUM_COL, float(number))
            if last > first:
                s.merge(first, NUM_COL, last, NUM_COL)
    questions = tuple(
        (number, len(qrows), any(k == "sub" for _, k, n, _ in placed if n == number))
        for number, qrows in by_question.items()
    )
    return s.snapshot(sheet_name, origin), Expected(questions, tuple(blanks))


STANDARD_ITEMS: list[tuple[str, int, int | None]] = [
    ("sub", 1, 1),
    ("sub", 1, 2),
    ("sub", 2, 1),
    ("sub", 2, 2),
    ("single", 3, None),
    ("single", 4, None),
]


# ── 缺陷學習單（每種拒絕條件至少一份）─────────────────────────────


@dataclass(frozen=True)
class DefectCase:
    """一份有缺陷的學習單與它預期被回報的問題種類。"""

    snapshot: SheetSnapshot
    kinds: frozenset[IssueKind]
    cells: tuple[tuple[int, int], ...] = field(default_factory=tuple)


def _base() -> Sheet:
    """合法的版面 A（原點 0,0），給缺陷版本修改。"""
    snap, _ = layout_a()
    s = Sheet(snap.row_count, snap.col_count)
    for ref, value in snap.cells.items():
        s.matrix[ref.row][ref.col] = (
            value.number if value.number is not None else value.text
        )
    s.merges = [(m.first_row, m.first_col, m.last_row, m.last_col) for m in snap.merges]
    return s


def defect_cases() -> dict[str, DefectCase]:
    """所有缺陷案例；鍵是案例名稱。"""
    cases: dict[str, DefectCase] = {}

    s = _base()
    s.matrix[HEADER_ROW][NUM_COL] = None
    cases["missing_number_header"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.MISSING_HEADER_NUMBER})
    )

    s = _base()
    s.matrix[HEADER_ROW][ANS_FIRST] = None
    cases["missing_answer_header"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.MISSING_HEADER_ANSWER})
    )

    s = _base()
    s.matrix[HEADER_ROW][NUM_COL] = None
    s.matrix[HEADER_ROW][ANS_FIRST] = None
    cases["missing_both_headers"] = DefectCase(
        s.snapshot(),
        frozenset({IssueKind.MISSING_HEADER_NUMBER, IssueKind.MISSING_HEADER_ANSWER}),
    )

    cases["empty_sheet"] = DefectCase(
        Sheet(5, 5).snapshot(),
        frozenset({IssueKind.MISSING_HEADER_NUMBER, IssueKind.MISSING_HEADER_ANSWER}),
    )

    # 表頭歧義：兩個表頭區塊
    snap, _ = layout_a()
    s = Sheet(snap.row_count + 6, snap.col_count)
    for ref, value in snap.cells.items():
        s.matrix[ref.row][ref.col] = (
            value.number if value.number is not None else value.text
        )
    s.merges = [(m.first_row, m.first_col, m.last_row, m.last_col) for m in snap.merges]
    s.set(12, NUM_COL, "題號").set(12, ANS_FIRST, "作答")
    cases["two_header_blocks"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.AMBIGUOUS_HEADER})
    )

    s = _base()
    s.set(HEADER_ROW, 4, "題號")
    cases["duplicate_header_same_row"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.AMBIGUOUS_HEADER})
    )

    s = _base()
    s.matrix[HEADER_ROW][ANS_FIRST] = None
    s.merges = [m for m in s.merges if m[0] != HEADER_ROW]
    s.set(HEADER_ROW - 1, ANS_FIRST, "作答")
    cases["headers_not_same_row"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.AMBIGUOUS_HEADER})
    )

    # 題號跳號：1,2,4,5（單題範本改）
    snap, _ = single_template((0, 0))
    s = Sheet(snap.row_count, snap.col_count)
    for ref, value in snap.cells.items():
        s.matrix[ref.row][ref.col] = (
            value.number if value.number is not None else value.text
        )
    s.merges = [(m.first_row, m.first_col, m.last_row, m.last_col) for m in snap.merges]
    s.matrix[5][1] = 4.0
    s.matrix[6][1] = 5.0
    s.matrix[7][1] = 6.0
    s.matrix[8][1] = 7.0
    cases["number_gap"] = DefectCase(s.snapshot(), frozenset({IssueKind.NUMBER_GAP}))

    # 近似錯誤對照：表頭、合併、格式都對，只有題號跳號（內容有缺陷）
    s = _base()
    s.matrix[9][NUM_COL] = 5.0
    cases["near_miss_valid_format_but_gap"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.NUMBER_GAP})
    )

    # 非相鄰重複題號：1,2,1
    s = _base()
    s.matrix[9][NUM_COL] = 1.0
    cases["non_adjacent_duplicate"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.NON_ADJACENT_DUPLICATE})
    )

    # 非數字題號
    for name, bad in (
        ("non_numeric_Q1", "Q1"),
        ("non_numeric_ordinal", "第1題"),
        ("non_numeric_trailing_dot", "1."),
        ("non_numeric_zero", 0.0),
        ("non_numeric_negative", -1.0),
        ("non_numeric_fraction", 1.5),
        ("non_numeric_fullwidth_digit", "１"),
        ("non_numeric_bool", True),
    ):
        s = _base()
        s.matrix[9][NUM_COL] = bad
        cases[name] = DefectCase(
            s.snapshot(), frozenset({IssueKind.NON_NUMERIC_NUMBER})
        )

    # 子編號缺漏：(1),(3)；重複：(1),(1)
    s = _base()
    s.matrix[5][ANS_FIRST] = "(3)"
    cases["sub_index_gap"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.SUB_INDEX_MISSING})
    )
    s = _base()
    s.matrix[5][ANS_FIRST] = "(1)"
    cases["sub_index_duplicate"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.SUB_INDEX_DUPLICATE})
    )

    # 孤立子空格：沒有題號、也不在縱向合併範圍內
    s = _base()
    s.matrix[9][NUM_COL] = None
    s.matrix[9][ANS_FIRST] = "(1)"
    s.merges = [m for m in s.merges if m[0] != 9]
    cases["orphan_sub_blank"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.ORPHAN_SUB_BLANK})
    )

    # 缺少答案格：子編號在最後一欄，右側沒有儲存格
    s = _base()
    s.matrix[HEADER_ROW][ANS_FIRST] = None
    s.matrix[HEADER_ROW][ANS_LAST] = "作答"
    s.merges = [m for m in s.merges if m[0] != HEADER_ROW]
    s.matrix[4][ANS_FIRST] = None
    s.matrix[4][ANS_LAST] = "(1)"
    s.matrix[5][ANS_FIRST] = None
    s.matrix[5][ANS_LAST] = "(2)"
    cases["missing_answer_cell_at_edge"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.MISSING_ANSWER_CELL})
    )

    # 目標格重疊：兩個子空格右側的格子被合併成同一格
    s = _base()
    s.merge(4, ANS_LAST, 5, ANS_LAST)
    cases["target_overlap"] = DefectCase(
        s.snapshot(), frozenset({IssueKind.TARGET_OVERLAP})
    )
    return cases
