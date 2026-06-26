# ============================================================
# WebSocket 连接管理器 - 管理客户和管理端的实时连接
# ============================================================
from __future__ import annotations

import json
from typing import Optional

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """
    WebSocket 连接池
    维护三组连接: 客户(按 ticket_id)、管理员(按 staff_id)、工单房间
    """

    def __init__(self) -> None:
        # ticket_id → WebSocket (客户连接)
        self._customer_sockets: dict[str, WebSocket] = {}
        # staff_id → WebSocket (管理员连接)
        self._admin_sockets: dict[str, WebSocket] = {}

    # ==================== 客户连接 ====================

    async def connect_customer(self, ticket_id: str, websocket: WebSocket) -> None:
        """客户通过 WebSocket 连接到工单"""
        await websocket.accept()
        # 断开旧连接
        old = self._customer_sockets.pop(ticket_id, None)
        if old:
            try:
                await old.close()
            except Exception:
                pass
        self._customer_sockets[ticket_id] = websocket
        logger.info(f"客户 WebSocket 已连接: ticket={ticket_id}")

    async def disconnect_customer(self, ticket_id: str) -> None:
        """断开客户连接"""
        ws = self._customer_sockets.pop(ticket_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(f"客户 WebSocket 已断开: ticket={ticket_id}")

    async def send_to_customer(self, ticket_id: str, data: dict) -> bool:
        """向客户推送消息"""
        ws = self._customer_sockets.get(ticket_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"向客户推送失败 ticket={ticket_id}: {e}")
            await self.disconnect_customer(ticket_id)
            return False

    # ==================== 管理员连接 ====================

    async def connect_admin(self, staff_id: str, websocket: WebSocket) -> None:
        """管理员通过 WebSocket 连接"""
        await websocket.accept()
        old = self._admin_sockets.pop(staff_id, None)
        if old:
            try:
                await old.close()
            except Exception:
                pass
        self._admin_sockets[staff_id] = websocket
        logger.info(f"管理员 WebSocket 已连接: staff={staff_id}")

    async def disconnect_admin(self, staff_id: str) -> None:
        """断开管理员连接"""
        ws = self._admin_sockets.pop(staff_id, None)
        if ws:
            try:
                await ws.close()
            except Exception:
                pass
        logger.info(f"管理员 WebSocket 已断开: staff={staff_id}")

    async def send_to_admin(self, staff_id: str, data: dict) -> bool:
        """向指定管理员推送消息"""
        ws = self._admin_sockets.get(staff_id)
        if not ws:
            return False
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"向管理员推送失败 staff={staff_id}: {e}")
            await self.disconnect_admin(staff_id)
            return False

    async def broadcast_to_admins(self, data: dict) -> int:
        """向所有在线管理员广播消息，返回成功发送数"""
        count = 0
        for staff_id in list(self._admin_sockets.keys()):
            if await self.send_to_admin(staff_id, data):
                count += 1
        logger.info(f"广播至 {count}/{len(self._admin_sockets)} 个管理员")
        return count


# 单例
connection_manager = ConnectionManager()
