"""WebSocket 连接管理：管理端全局频道 + 每工单的访客频道。

约定："REST 保底、WS 提速"——消息一律先落库，WS 只做增量推送；
断线重连后前端用 REST 拉全量补齐，不依赖 WS 保证送达。
"""
from __future__ import annotations

from fastapi import WebSocket
from loguru import logger


class WSManager:
    def __init__(self) -> None:
        self._admins: set[WebSocket] = set()
        self._customers: dict[str, set[WebSocket]] = {}  # ticket_id -> conns

    # ---------- 连接生命周期 ----------

    async def connect_admin(self, ws: WebSocket) -> None:
        await ws.accept()
        self._admins.add(ws)

    def disconnect_admin(self, ws: WebSocket) -> None:
        self._admins.discard(ws)

    async def connect_customer(self, ticket_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._customers.setdefault(ticket_id, set()).add(ws)

    def disconnect_customer(self, ticket_id: str, ws: WebSocket) -> None:
        conns = self._customers.get(ticket_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self._customers.pop(ticket_id, None)

    # ---------- 推送 ----------

    async def notify_admins(self, payload: dict) -> None:
        for ws in list(self._admins):
            try:
                await ws.send_json(payload)
            except Exception:
                self._admins.discard(ws)

    async def notify_ticket_customer(self, ticket_id: str, payload: dict) -> None:
        for ws in list(self._customers.get(ticket_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect_customer(ticket_id, ws)

    async def broadcast_ticket_event(self, ticket_id: str, payload: dict) -> None:
        """同一事件同时推给管理端与该工单的访客。"""
        await self.notify_admins(payload)
        await self.notify_ticket_customer(ticket_id, payload)


manager = WSManager()
logger.debug("WSManager initialized")
