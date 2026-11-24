"""啟動方式：`python -m lecture_quiz` 載入 `.env` 且不記錄授權碼（FR-022、技術限制 3）。

`/api/oauth/callback?code=…&state=…` 帶授權碼與 `state`；uvicorn 預設的 access log 會把
查詢字串寫進日誌，所以啟動時必須關閉 access log 並由根 logger 統一輸出。
"""

from unittest import mock

import lecture_quiz.__main__ as launcher


def test_launcher_loads_env_file_and_keeps_access_log_off():
    with mock.patch.object(launcher.uvicorn, "run") as run:
        launcher.main()
    run.assert_called_once()
    kwargs = run.call_args.kwargs
    assert kwargs["env_file"] == ".env"
    assert kwargs["access_log"] is False
    assert kwargs["log_config"] is None
    assert kwargs["host"] == "127.0.0.1"
