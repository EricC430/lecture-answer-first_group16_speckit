"""活動代碼、組別憑證、token 的產生與雜湊（研究 R5）。

亂數一律用 `secrets`；token 只保存 SHA-256，比對用 `secrets.compare_digest`。
"""

import hashlib
import re
import secrets
from collections.abc import Collection

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def _random_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def new_code(existing: Collection[str]) -> str:
    """產生不與 `existing` 重複的 6 碼活動代碼。

    Args:
        existing: 存續中活動的代碼。

    Returns:
        新的活動代碼。
    """
    while True:
        code = _random_code()
        if code not in existing:
            return code


def new_credential() -> str:
    """產生 6 碼組別加入憑證（字元集同活動代碼）。

    Returns:
        新的憑證。
    """
    return _random_code()


def new_token() -> str:
    """產生老師或裝置 token（32 bytes 的 URL-safe 字串）。

    Returns:
        新的 token。
    """
    return secrets.token_urlsafe(32)


BROWSER_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")


def new_browser_key() -> str:
    """產生瀏覽器金鑰（007 research R1：256 位元、43 個 URL 安全字元）。

    同一瀏覽器的所有分頁共用這把金鑰；它的雜湊就是該瀏覽器在各活動的裝置雜湊。

    Returns:
        新的瀏覽器金鑰。
    """
    return secrets.token_urlsafe(32)


def is_browser_key(value: object) -> bool:
    """檢查是否為格式正確的瀏覽器金鑰；格式不符一律視為沒有金鑰（007 FR-008）。

    Args:
        value: 任意值（通常是 cookie 或 Bearer 的原始內容）。

    Returns:
        長度 43、字元集 `[A-Za-z0-9_-]` 時為 True。
    """
    return isinstance(value, str) and BROWSER_KEY_PATTERN.fullmatch(value) is not None


def hash_token(token: str) -> str:
    """計算 token 的 SHA-256。

    Args:
        token: 原始 token。

    Returns:
        64 個字元的十六進位雜湊。
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, token_hash: str) -> bool:
    """以固定時間比對 token 與已保存的雜湊。

    Args:
        token: 請求帶來的原始 token。
        token_hash: 已保存的雜湊。

    Returns:
        相符時為 True。
    """
    return secrets.compare_digest(hash_token(token), token_hash)


def normalize_code_input(raw: str) -> str:
    """正規化使用者輸入的活動代碼：去除首尾空白並轉成大寫（FR-001）。

    Args:
        raw: 原始輸入。

    Returns:
        正規化後的代碼。
    """
    return raw.strip().upper()
