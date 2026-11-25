"""重新授權入口（US2-AS5；clarify Q1）。"""

import logging

import pytest

from lecture_quiz.app.result_export.models import ExportRejection

OPEN_STAGES = [
    "PREPARING",
    "JOINING",
    "ROUND_OPEN",
    "RESULT_PENDING",
    "RESULT_FINAL",
    "ENDED",
]


def start(env, requester=None):
    return env.run(
        env.service.start_authorization, env.code, requester or env.requester()
    )


@pytest.mark.parametrize("stage", OPEN_STAGES)
def test_available_in_every_non_cancelled_stage(make_env, stage):
    """Scenario: US2-AS5：除已取消外任何階段都可取得授權網址，不經過 002 的服務。"""
    env = make_env(stage=stage, plan=())

    def boom(*args, **kwargs):
        raise AssertionError("不得呼叫 002 的 ImportService.start_auth")

    env.client.app.state.import_service.start_auth = boom
    result = start(env)
    assert result.ok and result.value.startswith("https://")
    assert "start_authorization" in env.auth.calls


def test_cancelled_is_rejected(make_env):
    """已取消的活動拒絕。"""
    env = make_env(stage="CANCELLED", plan=())
    assert start(env).rejection is ExportRejection.ACTIVITY_CANCELLED
    assert env.auth.calls == []


def test_non_teacher_is_rejected(make_env):
    """非老師拒絕。"""
    env = make_env()
    assert start(env, env.student()).rejection is ExportRejection.NOT_TEACHER
    assert env.auth.calls == []


def test_not_configured(make_env):
    """Google 連線設定不齊備 → GOOGLE_NOT_CONFIGURED。"""
    env = make_env()
    env.auth.configured = False
    assert start(env).rejection is ExportRejection.GOOGLE_NOT_CONFIGURED


def test_log_does_not_contain_url_or_state(make_env, caplog):
    """日誌不含授權網址與 state。"""
    env = make_env()
    with caplog.at_level(logging.INFO):
        result = start(env)
    assert result.ok
    text = caplog.text
    assert "state=fake" not in text and "accounts.example.test" not in text
