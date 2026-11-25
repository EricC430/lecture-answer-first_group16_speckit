"""骨架冒煙測試：app 能建立、靜態頁與共用前端模組都能取得。"""

import subprocess
import sys

import pytest

from lecture_quiz.adapters.clock import SystemClock
from lecture_quiz.main import create_app
from tests.conftest import FAKE_CLOCK_START, FakeClock


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("/", 'href="teacher.html"'),  # 006 首頁改為角色卡片，不再有「老師頁」字樣
        ("/teacher.html", 'id="sync-banner"'),
        ("/student.html", 'id="sync-status"'),
        ("/js/api.js", "Idempotency-Key"),
        ("/js/sync.js", "同步中斷，正在重新連線"),
        ("/js/identity.js", "teacher:"),
        ("/css/app.css", "#sync-banner"),
    ],
)
def test_static_files_are_served(client, path, marker):
    response = client.get(path)
    assert response.status_code == 200
    assert marker in response.text


def test_default_app_uses_system_clock():
    app = create_app()
    assert isinstance(app.state.clock, SystemClock)


def test_system_clock_is_timezone_aware():
    assert SystemClock().now().tzinfo is not None


def test_fake_clock_advances_only_on_demand():
    clock = FakeClock()
    assert clock.now() == FAKE_CLOCK_START
    assert clock.advance(1.5) == clock.now()
    assert (clock.now() - FAKE_CLOCK_START).total_seconds() == 1.5


def test_fake_clock_requires_timezone():
    with pytest.raises(ValueError):
        FakeClock(FAKE_CLOCK_START.replace(tzinfo=None))


def test_logging_goes_to_stdout_at_info():
    """在乾淨的子行程確認：INFO 輸出到 stdout、DEBUG 不輸出、stderr 沒有日誌。"""
    script = (
        "import logging\n"
        "from lecture_quiz.main import configure_logging\n"
        "configure_logging()\n"
        "logging.getLogger('probe').debug('debug-line')\n"
        "logging.getLogger('probe').info('info-line')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert "info-line" in result.stdout
    assert "debug-line" not in result.stdout
    assert "info-line" not in result.stderr
