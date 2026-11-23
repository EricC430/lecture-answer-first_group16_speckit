"""活動代碼、組別憑證、token 的產生與雜湊（研究 R5）。

亂數一律用 `secrets`；token 只保存 SHA-256，比對用 `secrets.compare_digest`。
"""

import hashlib
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
