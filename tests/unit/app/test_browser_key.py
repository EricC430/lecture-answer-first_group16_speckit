"""007 T004：瀏覽器金鑰的產生與格式檢查（data-model「瀏覽器金鑰」）。"""

import re

import pytest

from lecture_quiz.app.activity.secrets_gen import is_browser_key, new_browser_key

_FORMAT = re.compile(r"[A-Za-z0-9_-]{43}")


def test_new_browser_key_format_and_uniqueness():
    keys = {new_browser_key() for _ in range(1000)}
    assert len(keys) == 1000
    for key in keys:
        assert _FORMAT.fullmatch(key)
        assert is_browser_key(key)


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "a" * 42,
        "a" * 44,
        "a" * 42 + ".",
        "a" * 42 + "=",
        "a" * 42 + " ",
        "a" * 41 + "中文",
        123,
    ],
)
def test_is_browser_key_rejects_bad_values(value):
    assert is_browser_key(value) is False
