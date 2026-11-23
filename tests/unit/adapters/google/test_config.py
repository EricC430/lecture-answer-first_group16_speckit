"""Google 設定：缺值、空字串、全部齊備（FR-022、research R10）。"""

import pytest

from lecture_quiz.adapters.google.config import (
    ENV_VARIABLES,
    SCOPES,
    load_config,
    missing_variables,
)

FULL = {
    "GOOGLE_CLIENT_ID": "id.apps.example",
    "GOOGLE_CLIENT_SECRET": "s3cret-value",
    "GOOGLE_API_KEY": "key-value",
    "GOOGLE_APP_ID": "123456",
    "OAUTH_REDIRECT_URI": "http://localhost:8000/api/oauth/callback",
}


def test_all_present_gives_a_config():
    config = load_config(FULL)
    assert config is not None
    assert config.redirect_uri == FULL["OAUTH_REDIRECT_URI"]
    assert missing_variables(FULL) == []


@pytest.mark.parametrize("name", ENV_VARIABLES)
def test_a_missing_variable_means_not_configured(name):
    env = {k: v for k, v in FULL.items() if k != name}
    assert load_config(env) is None
    assert missing_variables(env) == [name]


@pytest.mark.parametrize("name", ENV_VARIABLES)
@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_string_counts_as_not_set(name, empty):
    env = {**FULL, name: empty}
    assert load_config(env) is None
    assert missing_variables(env) == [name]


def test_nothing_set_lists_every_variable():
    assert missing_variables({}) == list(ENV_VARIABLES)
    assert load_config({}) is None


def test_scope_is_the_non_sensitive_drive_file_scope():
    assert SCOPES == ("https://www.googleapis.com/auth/drive.file",)


def test_repr_does_not_leak_secrets():
    config = load_config(FULL)
    assert config is not None
    assert "s3cret-value" not in repr(config) and "key-value" not in repr(config)
