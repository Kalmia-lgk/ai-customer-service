# ============================================================
# WebSocket 路由 - 客户和管理端的实时通信端点
# ============================================================
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from app.core.security import verify_token
from app.services.escalation_service import escalation_service
from app.services.connection_manager import connection_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/customer/{ticket_id}")
async def customer_websocket(websocket: WebSocket, ticket_id: str):
    """
    客户 WebSocket 连接
    客户通过工单 ID 连接，接收人工回复和状态更新
    """
    # 验证工单存在
    ticket = escalation_service.get_ticket_status(ticket_id)
    if not ticket:
        await websocket.close(code=4004, reason="工单不存在")
        return

    await connection_manager.connect_customer(ticket_id, websocket)

    try:
        # 发送当前状态
        await websocket.send_text(json.dumps({
            "type": "status",
            "ticket": ticket,
        }, ensure_ascii=False))

        # 保持连接，接收客户消息（工单聊天）
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "customer_message":
                content = msg.get("message", "")
                if content:
                    result = escalation_service.customer_send_message(ticket_id, content)
                    if result:
                        # 转发给所有管理员
                        await connection_manager.broadcast_to_admins({
                            "type": "ticket_message",
                            "ticket_id": ticket_id,
                            "message": {"role": "user", "content": content},
                        })

    except WebSocketDisconnect:
        logger.info(f"客户 WebSocket 断开: ticket={ticket_id}")
    except Exception as e:
        logger.error(f"客户 WebSocket 异常: ticket={ticket_id}, {e}")
    finally:
        await connection_manager.disconnect_customer(ticket_id)


@router.websocket("/ws/admin/{staff_id}")
async def admin_websocket(
    websocket: WebSocket,
    staff_id: str,
    token: str = Query(...),
):
    """
    管理端 WebSocket 连接
    接收新工单通知和消息推送

    认证方式: URL 查询参数 ?token=<jwt>
    """
    # 验证 JWT
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4001, reason="未授权")
        return

    await connection_manager.connect_admin(staff_id, websocket)

    try:
        # 发送连接成功
        await websocket.send_text(json.dumps({
            "type": "connected",
            "staff_id": staff_id,
            "message": "管理端 WebSocket 已连接",
        }, ensure_ascii=False))

        # 保持连接，处理管理端发来的消息
        while True:
            data = await websocket.receive_text()
            # 管理端主要接收服务端推送，但也可以发送心跳等
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        logger.info(f"管理员 WebSocket 断开: staff={staff_id}")
    except Exception as e:
        logger.error(f"管理员 WebSocket 异常: staff={staff_id}, {e}")
    finally:
        await connection_manager.disconnect_admin(staff_id)
