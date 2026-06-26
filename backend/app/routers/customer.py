# ============================================================
# 客户端 API 路由 - 面向最终客户的聊天 + 转人工
# ============================================================
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from app.schemas.models import ChatRequest, EscalationCreateRequest
from app.services.chat_service import ChatService
from app.services.escalation_service import escalation_service
from app.services.connection_manager import connection_manager

router = APIRouter(prefix="/api/customer", tags=["客户端"])

chat_service = ChatService()


@router.post("/chat", summary="客户流式聊天")
async def customer_chat(request: ChatRequest):
    """
    客户聊天接口 - SSE 流式输出
    与 /api/chat 相同逻辑，独立前缀方便未来区分
    """
    logger.info(f"[客户] 聊天: session={request.session_id}, msg='{request.message[:50]}...'")

    async def event_generator():
        try:
            async for chunk in chat_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
            ):
                event_type = chunk.get("type", "message")
                payload = {k: v for k, v in chunk.items() if k != "type"}

                if event_type == "thinking":
                    yield f"event: thinking\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "sources":
                    yield f"event: sources\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "session":
                    yield f"event: session\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "token":
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "done":
                    yield f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event_type == "error":
                    yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[客户] SSE 异常: {e}")
            yield f"event: error\ndata: {json.dumps({'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/escalate", summary="请求转人工")
async def escalate_to_human(request: EscalationCreateRequest):
    """
    客户请求转人工客服
    创建工单并通知所有在线管理员
    """
    # 获取对话快照
    info = chat_service.get_session_info(request.session_id)
    snapshot = info.get("messages", []) if info else []

    # 创建工单
    ticket = escalation_service.create_ticket(
        session_id=request.session_id,
        reason=request.reason,
        conversation_snapshot=snapshot[-10:],  # 最近10条消息
    )

    # 广播通知所有管理员
    await connection_manager.broadcast_to_admins({
        "type": "new_escalation",
        "ticket": ticket,
    })

    logger.info(f"[客户] 转人工请求已提交: ticket={ticket['ticket_id']}")
    return {
        "success": True,
        "message": "转人工请求已提交，请等待客服接入",
        "ticket_id": ticket["ticket_id"],
    }


@router.get("/ticket/{ticket_id}/status", summary="查询工单状态")
async def get_ticket_status(ticket_id: str):
    """客户轮询/查询工单状态"""
    status = escalation_service.get_ticket_status(ticket_id)
    if not status:
        raise HTTPException(status_code=404, detail="工单不存在")
    return status


@router.post("/ticket/{ticket_id}/message", summary="客户在工单中发消息")
async def customer_ticket_message(ticket_id: str, message: dict):
    """客户在人工服务过程中发送消息"""
    content = message.get("message", "")
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    result = escalation_service.customer_send_message(ticket_id, content)
    if not result:
        raise HTTPException(status_code=400, detail="工单不存在或状态不允许")

    # 通知管理员有新消息
    await connection_manager.broadcast_to_admins({
        "type": "ticket_message",
        "ticket_id": ticket_id,
        "message": {"role": "user", "content": content},
    })

    return {"success": True}
