"""Google 連線設定：只讀環境變數（research R10）。

- 五個變數都要有值；**空字串視為未設定**，缺任何一項就沒有設定
  （回 `GOOGLE_NOT_CONFIGURED`），
  `GOOGLE_APP_ID` 還須是純數字的 Cloud 專案編號，
  不退回離線路徑、不假裝成功。
- 授權範圍常數與 `state` 有效期限只定義在這個檔案。
- `.env` 由 `python -m lecture_quiz` 載入（`__main__.py` 的 `env_file=".env"`），
  這裡只讀 `os.environ`。
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
"""授權範圍：非敏感的 `drive.file`（待真實驗證，plan「待真實驗證的假設」第 1 項）。"""

SCOPES = (DRIVE_FILE_SCOPE,)
APP_ID_PATTERN = re.compile(r"[0-9]+")
"""`GOOGLE_APP_ID` 必須是 Cloud 專案編號（ASCII 純數字），不是專案 ID 或用戶端 ID。"""
STATE_TTL_SECONDS = 600
"""授權 `state` 的有效期限（秒）。"""

ENV_VARIABLES = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_API_KEY",
    "GOOGLE_APP_ID",
    "OAUTH_REDIRECT_URI",
)


@dataclass(frozen=True)
class GoogleConfig:
    """Google 連線設定。

    Attributes:
        client_id: OAuth 用戶端 ID。
        client_secret: OAuth 用戶端密鑰（不得進日誌）。
        api_key: Picker 用的 API 金鑰。
        app_id: Google Cloud 專案編號。
        redirect_uri: 授權後導回的網址。
    """

    client_id: str
    client_secret: str
    api_key: str
    app_id: str
    redirect_uri: str

    def __repr__(self) -> str:
        """不顯示任何機敏值。"""
        return "GoogleConfig(<redacted>)"


def missing_variables(env: Mapping[str, str] | None = None) -> list[str]:
    """列出缺少、為空字串或格式錯誤的環境變數名稱，給開發者看；不給老師看。

    `GOOGLE_APP_ID` 不是純數字（專案編號）時也算有問題：填錯時 Picker 仍能選檔，
    但 Drive 會回 404，老師只會看到含糊的「沒有讀取權限」。只回傳變數名稱，不回傳值。

    Args:
        env: 環境變數；省略時用 `os.environ`。

    Returns:
        缺少的變數名稱。
    """
    source = os.environ if env is None else env
    problems = [name for name in ENV_VARIABLES if not source.get(name, "").strip()]
    app_id = source.get("GOOGLE_APP_ID", "").strip()
    if app_id and not APP_ID_PATTERN.fullmatch(app_id):
        problems.append("GOOGLE_APP_ID")
    return [name for name in ENV_VARIABLES if name in problems]


def load_config(env: Mapping[str, str] | None = None) -> GoogleConfig | None:
    """讀取設定；任何一項缺少、為空字串或 `GOOGLE_APP_ID` 格式錯誤時回傳 `None`。

    Args:
        env: 環境變數；省略時用 `os.environ`。

    Returns:
        完整設定；未設定時為 `None`。
    """
    source = os.environ if env is None else env
    if missing_variables(source):
        return None
    return GoogleConfig(
        client_id=source["GOOGLE_CLIENT_ID"].strip(),
        client_secret=source["GOOGLE_CLIENT_SECRET"].strip(),
        api_key=source["GOOGLE_API_KEY"].strip(),
        app_id=source["GOOGLE_APP_ID"].strip(),
        redirect_uri=source["OAUTH_REDIRECT_URI"].strip(),
    )
