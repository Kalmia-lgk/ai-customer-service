"""WebSocket 路由：管理端全局频道 + 每工单访客频道（只推送，发消息走 REST）。"""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlmodel import Session

from app.db import engine
from app.security import decode_token
from app.services.ticket_service import require_ticket
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/admin")
async def ws_admin(ws: WebSocket, token: str = Query(default="")):
    try:
        decode_token(token)
    except Exception:
        await ws.close(code=4401)
        return
    await manager.connect_admin(ws)
    try:
        while True:
            await ws.receive_text()  # 仅保持连接（客户端可发 ping）
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"admin ws closed: {e}")
    finally:
        manager.disconnect_admin(ws)


@router.websocket("/ws/customer/{ticket_id}")
async def ws_customer(ws: WebSocket, ticket_id: str, visitor_id: str = Query(default="")):
    with Session(engine) as db:
        try:
            require_ticket(db, ticket_id, visitor_id)
        except Exception:
            await ws.close(code=4404)
            return
    await manager.connect_customer(ticket_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"customer ws closed: {e}")
    finally:
        manager.disconnect_customer(ticket_id, ws)
