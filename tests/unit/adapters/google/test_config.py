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


@pytest.mark.parametrize(
    "bad",
    ["my-project-123", "123456-abc.apps.googleusercontent.com", "12 34", "١٢٣", "-1"],
)
def test_app_id_must_be_the_numeric_project_number(bad):
    """GOOGLE_APP_ID 非 Cloud 專案編號時視為設定錯誤，不等到選檔後才變成 404。"""
    env = {**FULL, "GOOGLE_APP_ID": bad}
    assert load_config(env) is None
    assert missing_variables(env) == ["GOOGLE_APP_ID"]


def test_numeric_app_id_with_surrounding_spaces_is_accepted():
    env = {**FULL, "GOOGLE_APP_ID": " 123456789012 "}
    config = load_config(env)
    assert config is not None and config.app_id == "123456789012"
