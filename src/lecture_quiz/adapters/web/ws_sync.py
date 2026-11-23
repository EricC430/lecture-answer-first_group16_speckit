"""WebSocket 同步（contracts/sync-websocket.md）；`WebSocketHub` 實作 `SyncPublisher`。

WebSocket 只推送、不接收操作。連線後第一則訊息必須是
`{"type": "auth", "token": ...}`（token 不放在網址），之後：
- 立即送出依角色裁切的快照；之後每次狀態變更都推送新快照。
- 每 `ping_interval` 秒送一次 `{"type": "ping"}`。
- 活動不存在：送 `gone`，以 4410 關閉。token 無效：送 `unauthorized`，以 4401 關閉。
- 第一則訊息不是 auth：以 4400 關閉；逾時沒送：以 4408 關閉。
單一連線送出失敗時只關閉那條連線，不影響其他連線與狀態。
"""

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from lecture_quiz.app.activity.ports import DisconnectReason, Requester
from lecture_quiz.app.activity.secrets_gen import normalize_code_input
from lecture_quiz.app.activity.service import ActivityService
from lecture_quiz.core.activity.commands import Anonymous, Device
from lecture_quiz.core.activity.models import Activity

logger = logging.getLogger(__name__)

CLOSE_BAD_FIRST_MESSAGE = 4400
CLOSE_UNAUTHORIZED = 4401
CLOSE_AUTH_TIMEOUT = 4408
CLOSE_GONE = 4410


@dataclass(eq=False)
class _Connection:
    """一條已認證的連線。"""

    websocket: WebSocket
    requester: Requester
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def role(self) -> str:
        return "student" if isinstance(self.requester, Device) else "teacher"

    async def send(self, message: dict[str, object]) -> None:
        async with self.send_lock:
            await self.websocket.send_json(message)


class WebSocketHub:
    """管理所有活動的 WebSocket 連線，並把狀態變更推送出去。"""

    def __init__(self, auth_timeout: float = 5.0, ping_interval: float = 10.0) -> None:
        """建立 hub。

        Args:
            auth_timeout: 等待第一則 auth 訊息的秒數。
            ping_interval: 送 ping 的間隔秒數。
        """
        self._auth_timeout = auth_timeout
        self._ping_interval = ping_interval
        self._service: ActivityService | None = None
        self._connections: dict[str, set[_Connection]] = {}

    def bind(self, service: ActivityService) -> None:
        """綁定活動服務（服務建立後設定一次）。

        Args:
            service: 用來驗證 token 與取得快照的服務。
        """
        self._service = service

    def connection_count(self, code: str) -> int:
        """該活動目前的連線數。

        Args:
            code: 活動代碼。

        Returns:
            連線數。
        """
        return len(self._connections.get(code, ()))

    async def publish(self, activity: Activity) -> None:
        """把最新狀態推送到該活動的每一條連線，各自依角色裁切。

        Args:
            activity: 變更後的活動。
        """
        for conn in list(self._connections.get(activity.code, ())):
            view = ActivityService.snapshot_for(activity, conn.requester)
            if view is None:
                continue
            try:
                await conn.send(view.to_json())
            except Exception:
                logger.info(
                    "推送失敗，關閉該連線 activity=%s role=%s", activity.code, conn.role
                )
                self._unregister(activity.code, conn)
                with contextlib.suppress(Exception):
                    await conn.websocket.close()

    async def disconnect_device(
        self, code: str, token_hash: str, reason: DisconnectReason
    ) -> None:
        """通知裝置已失去組別身分（離開本組或組別被刪除），並關閉它的連線。

        Args:
            code: 活動代碼。
            token_hash: 裝置 token 的雜湊。
            reason: `LEFT_GROUP` 或 `GROUP_DELETED`。
        """
        for conn in list(self._connections.get(code, ())):
            requester = conn.requester
            if not isinstance(requester, Device) or requester.token_hash != token_hash:
                continue
            self._unregister(code, conn)
            with contextlib.suppress(Exception):
                await conn.send({"type": "unauthorized", "reason": reason})
                await conn.websocket.close(code=CLOSE_UNAUTHORIZED)
            logger.info("裝置失去組別身分 activity=%s reason=%s", code, reason)

    async def serve(self, websocket: WebSocket, raw_code: str) -> None:
        """處理一條 WebSocket 連線的完整生命週期。

        Args:
            websocket: 連線。
            raw_code: 路徑中的活動代碼。
        """
        assert self._service is not None, "WebSocketHub 尚未綁定服務"
        await websocket.accept()
        code = normalize_code_input(raw_code)
        token = await self._receive_auth(websocket)
        if token is None:
            return
        if self._service.get(code) is None:
            await websocket.send_json({"type": "gone"})
            await websocket.close(code=CLOSE_GONE)
            return
        requester = self._service.resolve_requester(code, token)
        if isinstance(requester, Anonymous):
            await websocket.send_json(
                {"type": "unauthorized", "reason": "INVALID_TOKEN"}
            )
            await websocket.close(code=CLOSE_UNAUTHORIZED)
            return

        conn = _Connection(websocket, requester)
        self._connections.setdefault(code, set()).add(conn)
        logger.info("同步連線建立 activity=%s role=%s", code, conn.role)
        ping_task = asyncio.get_running_loop().create_task(self._ping_loop(conn))
        try:
            snapshot = self._service.snapshot(code, requester)
            if snapshot.ok and snapshot.value is not None:
                await conn.send(snapshot.value.to_json())
            while True:
                await websocket.receive_text()
                # 認證後的任何訊息都忽略；不記錄內容，避免把 token 寫入日誌
                logger.warning(
                    "忽略同步連線的多餘訊息 activity=%s role=%s", code, conn.role
                )
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.info("同步連線中斷 activity=%s role=%s", code, conn.role)
        finally:
            ping_task.cancel()
            self._unregister(code, conn)
            logger.info("同步連線關閉 activity=%s role=%s", code, conn.role)

    async def _receive_auth(self, websocket: WebSocket) -> str | None:
        """等待第一則 auth 訊息；不合格時關閉連線並回傳 `None`。"""
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), self._auth_timeout)
        except TimeoutError:
            await websocket.close(code=CLOSE_AUTH_TIMEOUT)
            return None
        except WebSocketDisconnect:
            return None
        try:
            message = json.loads(raw)
        except ValueError:
            message = None
        token = message.get("token") if isinstance(message, dict) else None
        if (
            not isinstance(message, dict)
            or message.get("type") != "auth"
            or not isinstance(token, str)
        ):
            await websocket.close(code=CLOSE_BAD_FIRST_MESSAGE)
            return None
        return token

    async def _ping_loop(self, conn: _Connection) -> None:
        with contextlib.suppress(Exception):
            while True:
                await asyncio.sleep(self._ping_interval)
                await conn.send({"type": "ping"})

    def _unregister(self, code: str, conn: _Connection) -> None:
        conns = self._connections.get(code)
        if conns is not None:
            conns.discard(conn)
            if not conns:
                del self._connections[code]


def create_router(hub: WebSocketHub) -> APIRouter:
    """建立 WebSocket 路由 `/ws/activities/{code}`。

    Args:
        hub: 處理連線的 hub。

    Returns:
        含 WebSocket 路由的 router。
    """
    router = APIRouter()

    @router.websocket("/ws/activities/{code}")
    async def activity_sync(websocket: WebSocket, code: str) -> None:
        """活動同步通道。"""
        await hub.serve(websocket, code)

    return router
