"""驗證問題的修正建議與位置顯示（老師可照做的固定文字）。

核心只產生純文字；顯示給老師時前端一律以 `textContent` 輸出（FR-022）。
"""

from lecture_quiz.core.guided_notes_import.models import CellRef, IssueKind

QUOTE_LIMIT = 40
"""被引用的儲存格文字最多保留的字元數。"""

ISSUE_HINTS: dict[IssueKind, str] = {
    IssueKind.MISSING_HEADER_NUMBER: (
        "找不到「題號」表頭。請在表頭列放一個文字剛好是「題號」的儲存格（前後空白會被忽略）。"
    ),
    IssueKind.MISSING_HEADER_ANSWER: (
        "找不到「作答」表頭。請在表頭列放一個文字剛好是「作答」的儲存格（前後空白會被忽略）。"
    ),
    IssueKind.AMBIGUOUS_HEADER: (
        "找到多個「題號」或「作答」表頭，或兩者不在同一列，無法判定要用哪一區。"
        "請讓工作表只有一組表頭，且「題號」與「作答」在同一列。"
    ),
    IssueKind.NON_NUMERIC_NUMBER: (
        "題號必須是正整數（例如 1 或 2）。不接受 0、負數、小數、"
        "「Q1」「第1題」或全形數字，請修改這個儲存格。"
    ),
    IssueKind.NUMBER_GAP: (
        "題號必須從 1 開始連續遞增，這裡預期是第 {expected} 題。請補上或修正題號。"
    ),
    IssueKind.NON_ADJACENT_DUPLICATE: (
        "同一個題號出現在不相鄰的位置。請讓同一題的列相鄰，或把題號儲存格縱向合併。"
    ),
    IssueKind.SUB_INDEX_MISSING: (
        "題組的子編號必須從 (1) 開始連續遞增，且每個子空格都要有子編號"
        "（半形或全形括號、半形數字）。請補上或修正這一列。"
    ),
    IssueKind.SUB_INDEX_DUPLICATE: (
        "同一題出現重複的子編號。請修正為連續不重複的 (1)(2)…。"
    ),
    IssueKind.ORPHAN_SUB_BLANK: (
        "這個子編號沒有所屬的題號。請在題號欄填上題號，或把題號儲存格縱向合併到這一列。"
    ),
    IssueKind.MISSING_ANSWER_CELL: (
        "找不到作答格：子編號或題號右側沒有可用的儲存格。請確認作答格存在於工作表內。"
    ),
    IssueKind.TARGET_OVERLAP: (
        "這個作答格與 {other} 指向同一格，兩個空格不能共用答案位置。請調整合併範圍。"
    ),
}


def column_letters(col: int) -> str:
    """0 起算的欄索引轉成試算表欄字母（0→A、25→Z、26→AA）。

    Args:
        col: 欄索引。

    Returns:
        欄字母。
    """
    letters = ""
    number = col + 1
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def a1(ref: CellRef) -> str:
    """儲存格位置的顯示文字，例如「B5」（列從 1 起算）。

    Args:
        ref: 0 起算的位置。

    Returns:
        A1 表示法。
    """
    return f"{column_letters(ref.col)}{ref.row + 1}"


def hint_for(kind: IssueKind, **details: object) -> str:
    """取得問題種類的修正建議，並填入細節。

    Args:
        kind: 問題種類。
        **details: 建議文字中的欄位（例如 `expected`、`other`）。

    Returns:
        老師可照做的建議。
    """
    return (
        ISSUE_HINTS[kind].format(**details)
        if details
        else ISSUE_HINTS[kind].split("{")[0]
    )


def quote(text: str | None) -> str | None:
    """截斷被引用的儲存格文字；沒有內容時回傳 `None`。

    Args:
        text: 儲存格顯示文字。

    Returns:
        最多 `QUOTE_LIMIT` 字元的文字。
    """
    if text is None or text.strip() == "":
        return None
    return text[:QUOTE_LIMIT]
