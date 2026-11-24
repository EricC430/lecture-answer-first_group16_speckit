"""Google 授權（授權碼流程）：`state` 一次性且有期限，token 只存記憶體。

- 後端用 `google-auth-oauthlib` 的 `Flow` 產生授權網址並以授權碼換 token；token 只放在
  `ImportStore.sessions`，重啟即清空，不寫檔案、不進日誌、不回傳給前端。
- 唯一給前端的是 `picker_credentials` 回傳的短效 access token（`drive.file` 範圍），
  由 HTTP 層以 `Cache-Control: no-store` 回應。
- 日誌只記活動代碼與結果，不記 token、授權碼、`state`、client secret。
"""

import asyncio
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2.rfc6749.errors import OAuth2Error

from lecture_quiz.adapters.google.config import (
    SCOPES,
    STATE_TTL_SECONDS,
    GoogleConfig,
    load_config,
)
from lecture_quiz.adapters.google.errors import CAUGHT, map_exception
from lecture_quiz.app.activity.ports import Clock, Requester
from lecture_quiz.app.guided_notes_import.models import (
    CallbackResult,
    ImportRejection,
    PickerConfig,
    Result,
)
from lecture_quiz.app.guided_notes_import.store import ImportStore

logger = logging.getLogger("lecture_quiz.google")

MAX_PENDING = 100
"""同時等待回呼的授權上限；超過時淘汰最舊的。"""


class FlowLike(Protocol):
    """`google_auth_oauthlib.flow.Flow` 用到的部分（測試以替身取代，不連網）。"""

    @property
    def credentials(self) -> Any:
        """換到 token 之後的憑證。"""
        ...

    def authorization_url(self, **kwargs: Any) -> tuple[str, str]:
        """產生授權網址。"""
        ...

    def fetch_token(self, **kwargs: Any) -> Any:
        """以授權碼換 token（同步、會連網）。"""
        ...


FlowFactory = Callable[[GoogleConfig], FlowLike]
Refresher = Callable[[Any], None]


def default_flow_factory(config: GoogleConfig) -> FlowLike:
    """以設定建立真實的 OAuth `Flow`（網頁應用程式用戶端）。

    Args:
        config: Google 連線設定。

    Returns:
        尚未授權的 `Flow`。
    """
    client_config = {
        "web": {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config, scopes=list(SCOPES), redirect_uri=config.redirect_uri
    )


def default_refresher(credentials: Any) -> None:
    """以 refresh token 更新過期的 access token（同步、會連網）。"""
    credentials.refresh(GoogleRequest())


@dataclass
class GoogleSession:
    """一個活動老師的授權 session（只在記憶體；不得進日誌）。

    Attributes:
        credentials: `google.oauth2.credentials.Credentials`。
    """

    credentials: Any

    def __repr__(self) -> str:
        """不顯示 token。"""
        return "GoogleSession(<redacted>)"


@dataclass
class _Pending:
    """等待 Google 導回的授權：`state` 對應的活動與 flow。"""

    code: str
    flow: FlowLike
    expires_at: datetime


class GoogleAuthGateway:
    """`AuthGateway` 的真實實作；也提供 `valid_credentials` 給 Sheets 讀取器使用。"""

    def __init__(
        self,
        store: ImportStore,
        clock: Clock,
        config_provider: Callable[[], GoogleConfig | None] = load_config,
        flow_factory: FlowFactory = default_flow_factory,
        refresher: Refresher = default_refresher,
    ) -> None:
        """建立閘道。

        Args:
            store: 記憶體存放（token 放在 `sessions`）。
            clock: 時鐘，只用於 `state` 有效期限。
            config_provider: 取得設定的函式（每次使用才讀，`.env` 載入時機不影響）。
            flow_factory: 建立 OAuth `Flow`；測試傳入替身。
            refresher: 更新過期 token；測試傳入替身。
        """
        self._store = store
        self._clock = clock
        self._config_provider = config_provider
        self._flow_factory = flow_factory
        self._refresher = refresher
        self._pending: dict[str, _Pending] = {}

    def is_configured(self) -> bool:
        """設定是否齊備（空字串視為未設定）。"""
        return self._config_provider() is not None

    def _drop_expired(self) -> None:
        now = self._clock.now()
        for state in [s for s, p in self._pending.items() if p.expires_at <= now]:
            del self._pending[state]
        while len(self._pending) >= MAX_PENDING:
            del self._pending[next(iter(self._pending))]

    async def start_authorization(self, code: str, requester: Requester) -> Result[str]:
        """產生一次性且有期限的 `state`，回傳 Google 授權網址。

        Args:
            code: 活動代碼。
            requester: 已通過老師檢查的請求者。

        Returns:
            授權網址；沒有設定時為 `GOOGLE_NOT_CONFIGURED`。
        """
        config = self._config_provider()
        if config is None:
            return Result.failure(ImportRejection.GOOGLE_NOT_CONFIGURED)
        self._drop_expired()
        state = secrets.token_urlsafe(32)
        flow = self._flow_factory(config)
        url, _ = flow.authorization_url(
            state=state, access_type="offline", prompt="consent"
        )
        self._pending[state] = _Pending(
            code, flow, self._clock.now() + timedelta(seconds=STATE_TTL_SECONDS)
        )
        logger.info("授權開始 activity=%s", code)
        return Result.success(url)

    async def complete_authorization(
        self, state: str | None, auth_code: str | None, error: str | None
    ) -> CallbackResult:
        """處理 Google 導回：`state` 不符、過期或重複使用都不交換 token。

        Args:
            state: 導回帶的 `state`。
            auth_code: 授權碼。
            error: Google 回報的錯誤（使用者取消或拒絕時有值）。

        Returns:
            活動代碼與結果（`ok`、`denied`、`error`）。
        """
        pending = self._pending.pop(state, None) if state else None  # 只能用一次
        if pending is None or pending.expires_at <= self._clock.now():
            logger.info("授權回呼 state 無效或已過期")
            return CallbackResult(code=None, status="error")
        if error:
            logger.info("授權被取消或拒絕 activity=%s", pending.code)
            return CallbackResult(code=pending.code, status="denied")
        if not auth_code:
            return CallbackResult(code=pending.code, status="error")
        try:
            await asyncio.to_thread(pending.flow.fetch_token, code=auth_code)
        except (OAuth2Error, Warning, *CAUGHT):
            logger.info("授權碼交換失敗 activity=%s", pending.code)
            return CallbackResult(code=pending.code, status="error")
        self._store.sessions[pending.code] = GoogleSession(pending.flow.credentials)
        logger.info("授權成功 activity=%s", pending.code)
        return CallbackResult(code=pending.code, status="ok")

    def _session(self, code: str) -> GoogleSession | None:
        session = self._store.sessions.get(code)
        return session if isinstance(session, GoogleSession) else None

    def is_authorized(self, code: str) -> bool:
        """該活動老師是否有有效授權（token 未過期，或可用 refresh token 更新）。

        Args:
            code: 活動代碼。

        Returns:
            已授權為 True。
        """
        session = self._session(code)
        if session is None:
            return False
        creds = session.credentials
        return bool(not creds.expired or creds.refresh_token)

    async def valid_credentials(self, code: str) -> Result[Any]:
        """取得有效的憑證；過期時先更新，失敗回報需要重新授權。

        Args:
            code: 活動代碼。

        Returns:
            成功時為 `Credentials`（只給轉接層內部使用，不得外洩）。
        """
        session = self._session(code)
        if session is None:
            return Result.failure(ImportRejection.NOT_AUTHORIZED)
        creds = session.credentials
        if creds.expired:
            if not creds.refresh_token:
                return Result.failure(ImportRejection.AUTH_EXPIRED)
            try:
                await asyncio.to_thread(self._refresher, creds)
            except CAUGHT as exc:
                logger.info("token 更新失敗 activity=%s", code)
                return Result.failure(map_exception(exc))
        return Result.success(creds)

    async def picker_credentials(self, code: str) -> Result[PickerConfig]:
        """取得 Picker 用的短效憑證（只含 `drive.file` 範圍的 access token）。

        Args:
            code: 活動代碼。

        Returns:
            成功時為 `PickerConfig`。
        """
        config = self._config_provider()
        if config is None:
            return Result.failure(ImportRejection.GOOGLE_NOT_CONFIGURED)
        creds = await self.valid_credentials(code)
        if not creds.ok or creds.value is None:
            return Result.failure(creds.rejection or ImportRejection.NOT_AUTHORIZED)
        return Result.success(
            PickerConfig(str(creds.value.token), config.api_key, config.app_id)
        )
