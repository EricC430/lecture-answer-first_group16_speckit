"""授權閘道：`state` 一次性且有期限、token 只在記憶體（US1-AS3、AS4）。"""

import asyncio
import logging

import pytest
from google.auth.exceptions import RefreshError

from lecture_quiz.adapters.google.auth import GoogleAuthGateway, GoogleSession
from lecture_quiz.adapters.google.config import STATE_TTL_SECONDS, load_config
from lecture_quiz.app.guided_notes_import.models import ImportRejection
from lecture_quiz.app.guided_notes_import.store import ImportStore
from tests.conftest import FakeClock
from tests.unit.app.guided_notes_import.fakes import TEACHER

ENV = {
    "GOOGLE_CLIENT_ID": "id.apps.example",
    "GOOGLE_CLIENT_SECRET": "SUPER-SECRET-VALUE",
    "GOOGLE_API_KEY": "API-KEY-VALUE",
    "GOOGLE_APP_ID": "424242",
    "OAUTH_REDIRECT_URI": "http://localhost:8000/api/oauth/callback",
}
ACCESS_TOKEN = "ya29.SECRET-ACCESS-TOKEN"
CODE = "ABC234"


class FakeCredentials:
    def __init__(self, expired: bool = False, refresh_token: str | None = "r") -> None:
        self.token = ACCESS_TOKEN
        self.expired = expired
        self.refresh_token = refresh_token


class FakeFlow:
    """不連網的 OAuth Flow 替身。"""

    instances: list["FakeFlow"] = []

    def __init__(self, fail: bool = False) -> None:
        self.fetched: list[str] = []
        self.fail = fail
        self.credentials = FakeCredentials()
        FakeFlow.instances.append(self)

    def authorization_url(self, **kwargs):
        return f"https://accounts.example.test/auth?state={kwargs['state']}", kwargs[
            "state"
        ]

    def fetch_token(self, **kwargs):
        self.fetched.append(kwargs["code"])
        if self.fail:
            raise RefreshError("invalid_grant")


def make(config=True, fail=False, refresher=None):
    FakeFlow.instances = []
    clock = FakeClock()
    store = ImportStore()
    gateway = GoogleAuthGateway(
        store,
        clock,
        config_provider=lambda: load_config(ENV) if config else None,
        flow_factory=lambda _c: FakeFlow(fail=fail),
        refresher=refresher or (lambda creds: None),
    )
    return gateway, store, clock


def run(coro):
    return asyncio.run(coro)


def state_of(url: str) -> str:
    return url.split("state=")[1]


def test_not_configured_is_reported_not_faked():
    gateway, *_ = make(config=False)
    assert not gateway.is_configured()
    result = run(gateway.start_authorization(CODE, TEACHER))
    assert result.rejection is ImportRejection.GOOGLE_NOT_CONFIGURED
    assert run(gateway.picker_credentials(CODE)).rejection is (
        ImportRejection.GOOGLE_NOT_CONFIGURED
    )


def test_successful_flow_stores_the_session_in_memory_only():
    """Scenario: US1-AS1"""
    gateway, store, _ = make()
    url = run(gateway.start_authorization(CODE, TEACHER)).value
    assert url is not None
    done = run(gateway.complete_authorization(state_of(url), "auth-code", None))
    assert (done.code, done.status) == (CODE, "ok")
    assert gateway.is_authorized(CODE)
    assert isinstance(store.sessions[CODE], GoogleSession)
    assert ACCESS_TOKEN not in repr(store.sessions[CODE])  # repr 不含 token


def test_state_can_only_be_used_once_and_does_not_exchange_again():
    """Scenario: US1-AS3（重複使用不交換 token）"""
    gateway, _, _ = make()
    state = state_of(run(gateway.start_authorization(CODE, TEACHER)).value or "")
    assert run(gateway.complete_authorization(state, "c1", None)).status == "ok"
    again = run(gateway.complete_authorization(state, "c2", None))
    assert again.status == "error" and again.code is None
    assert FakeFlow.instances[0].fetched == ["c1"]  # 第二次沒有交換


def test_expired_state_is_rejected_without_exchange():
    """Scenario: US1-AS3"""
    gateway, _, clock = make()
    state = state_of(run(gateway.start_authorization(CODE, TEACHER)).value or "")
    clock.advance(STATE_TTL_SECONDS + 1)
    result = run(gateway.complete_authorization(state, "c1", None))
    assert result.status == "error"
    assert FakeFlow.instances[0].fetched == [] and not gateway.is_authorized(CODE)


@pytest.mark.parametrize("bad_state", [None, "", "forged-state", "x" * 500])
def test_unknown_or_missing_state_does_not_exchange(bad_state):
    """Scenario: US1-AS3"""
    gateway, *_ = make()
    run(gateway.start_authorization(CODE, TEACHER))
    result = run(gateway.complete_authorization(bad_state, "c1", None))
    assert result.status == "error"
    assert FakeFlow.instances[0].fetched == []


def test_user_cancel_or_deny_is_reported_as_denied_without_exchange():
    """Scenario: US1-AS3"""
    gateway, _, _ = make()
    state = state_of(run(gateway.start_authorization(CODE, TEACHER)).value or "")
    result = run(gateway.complete_authorization(state, None, "access_denied"))
    assert (result.code, result.status) == (CODE, "denied")
    assert FakeFlow.instances[0].fetched == [] and not gateway.is_authorized(CODE)


def test_failed_code_exchange_is_an_error_and_stores_nothing():
    """Scenario: US1-AS4"""
    gateway, store, _ = make(fail=True)
    state = state_of(run(gateway.start_authorization(CODE, TEACHER)).value or "")
    result = run(gateway.complete_authorization(state, "c1", None))
    assert result.status == "error" and CODE not in store.sessions


def test_tokens_never_appear_in_return_values_or_logs(caplog):
    """FR-022、技術限制 3"""
    caplog.set_level(logging.DEBUG)
    gateway, store, _ = make()
    started = run(gateway.start_authorization(CODE, TEACHER))
    state = state_of(started.value or "")
    done = run(gateway.complete_authorization(state, "THE-AUTH-CODE", None))
    picker = run(gateway.picker_credentials(CODE))
    assert picker.value is not None
    for obj in (done, repr(picker.value), repr(store.sessions[CODE])):
        assert ACCESS_TOKEN not in repr(obj) and "API-KEY-VALUE" not in repr(obj)
    logged = caplog.text
    for secret in (ACCESS_TOKEN, "THE-AUTH-CODE", state, "SUPER-SECRET-VALUE"):
        assert secret not in logged


def test_picker_credentials_returns_short_lived_token_and_ids():
    """FR-001"""
    gateway, *_ = make()
    state = state_of(run(gateway.start_authorization(CODE, TEACHER)).value or "")
    run(gateway.complete_authorization(state, "c", None))
    picker = run(gateway.picker_credentials(CODE)).value
    assert picker is not None
    assert (picker.access_token, picker.api_key, picker.app_id) == (
        ACCESS_TOKEN,
        "API-KEY-VALUE",
        "424242",
    )


def test_not_authorized_without_a_session():
    """Scenario: US1-AS3"""
    gateway, *_ = make()
    assert not gateway.is_authorized(CODE)
    assert (
        run(gateway.picker_credentials(CODE)).rejection
        is ImportRejection.NOT_AUTHORIZED
    )
    assert (
        run(gateway.valid_credentials(CODE)).rejection is ImportRejection.NOT_AUTHORIZED
    )


def test_expired_token_is_refreshed_and_failure_means_reauthorize():
    """Scenario: US1-AS4"""
    refreshed: list[object] = []

    def refresher(creds):
        refreshed.append(creds)
        creds.expired = False

    gateway, store, _ = make(refresher=refresher)
    store.sessions[CODE] = GoogleSession(FakeCredentials(expired=True))
    assert run(gateway.valid_credentials(CODE)).ok and len(refreshed) == 1

    def failing(_creds):
        raise RefreshError("revoked")

    gateway2, store2, _ = make(refresher=failing)
    store2.sessions[CODE] = GoogleSession(FakeCredentials(expired=True))
    assert (
        run(gateway2.valid_credentials(CODE)).rejection is ImportRejection.AUTH_EXPIRED
    )


def test_expired_token_without_refresh_token_needs_reauthorization():
    """Scenario: US1-AS4"""
    gateway, store, _ = make()
    store.sessions[CODE] = GoogleSession(
        FakeCredentials(expired=True, refresh_token=None)
    )
    assert not gateway.is_authorized(CODE)
    assert (
        run(gateway.valid_credentials(CODE)).rejection is ImportRejection.AUTH_EXPIRED
    )
