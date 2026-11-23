"""T016：代碼與 token 產生、雜湊比對、去重表上限（研究 R5）。"""

import re

from lecture_quiz.app.activity.registry import ActivityRegistry, ProcessedKey
from lecture_quiz.app.activity.secrets_gen import (
    CODE_ALPHABET,
    hash_token,
    new_code,
    new_credential,
    new_token,
    normalize_code_input,
    tokens_match,
)

CODE_RE = re.compile(f"[{CODE_ALPHABET}]{{6}}")


def test_code_alphabet_excludes_confusing_characters():
    assert len(CODE_ALPHABET) == 32
    for ch in "0O1I":
        assert ch not in CODE_ALPHABET


def test_new_code_has_six_characters_from_alphabet():
    for _ in range(200):
        assert CODE_RE.fullmatch(new_code(set()))


def test_new_code_avoids_existing_codes():
    existing = {new_code(set()) for _ in range(50)}
    for _ in range(200):
        assert new_code(existing) not in existing


def test_new_credential_format():
    assert CODE_RE.fullmatch(new_credential())


def test_new_token_is_long_and_unique():
    tokens = {new_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 40 for t in tokens)


def test_hash_token_is_sha256_hex_and_not_the_token():
    token = new_token()
    digest = hash_token(token)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert token not in digest
    assert hash_token(token) == digest


def test_tokens_match_uses_hash_comparison():
    token = new_token()
    assert tokens_match(token, hash_token(token))
    assert not tokens_match(new_token(), hash_token(token))
    assert not tokens_match("", hash_token(token))


def test_normalize_code_input():
    assert normalize_code_input(" k7qh2m ") == "K7QH2M"
    assert normalize_code_input("K7QH2M") == "K7QH2M"


def test_processed_table_keeps_at_most_1000_entries_and_evicts_oldest():
    registry = ActivityRegistry()
    code = "ABCDEF"
    for i in range(1005):
        registry.remember(code, ProcessedKey("hash", f"k{i}"), i)
    assert registry.processed_count(code) == 1000
    for i in range(5):
        assert registry.recall(code, ProcessedKey("hash", f"k{i}")) is None
    assert registry.recall(code, ProcessedKey("hash", "k5")) == 5
    assert registry.recall(code, ProcessedKey("hash", "k1004")) == 1004


def test_processed_keys_are_scoped_by_identity():
    registry = ActivityRegistry()
    registry.remember("ABCDEF", ProcessedKey("teacher", "k"), "first")
    assert registry.recall("ABCDEF", ProcessedKey("device", "k")) is None
    assert registry.recall("ABCDEF", ProcessedKey("teacher", "k")) == "first"


def test_create_keys_are_remembered_globally():
    registry = ActivityRegistry()
    registry.remember_create("key-1", ("ABCDEF", "token"))
    assert registry.recall_create("key-1") == ("ABCDEF", "token")
    assert registry.recall_create("key-2") is None
