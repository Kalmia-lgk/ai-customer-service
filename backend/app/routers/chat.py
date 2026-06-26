# ============================================================
# 聊天路由 - 处理对话相关 API
# POST /api/chat         流式聊天
# GET  /api/sessions     会话列表
# GET  /api/sessions/{id}会话详情
# DELETE /api/sessions/{id} 删除会话
# ============================================================
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from app.schemas.models import (
    ChatRequest,
    SessionListResponse,
    SessionMeta,
    ErrorResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api", tags=["聊天"])

# 全局服务实例
chat_service = ChatService()


@router.post("/chat", summary="流式聊天")
async def chat_endpoint(request: ChatRequest):
    """
    核心聊天接口，使用 Server-Sent Events (SSE) 实现流式输出

    事件类型:
    - session:   返回/创建 session_id
    - thinking:  处理状态提示
    - sources:   知识库引用来源
    - token:     逐字内容
    - done:      完成标记
    - error:     错误信息
    """
    logger.info(f"收到聊天请求: session={request.session_id}, msg='{request.message[:50]}...'")

    async def event_generator():
        """SSE 事件流生成器"""
        try:
            async for chunk in chat_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
            ):
                event_type = chunk.get("type", "message")
                # 移除 type 字段后发送
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
            logger.error(f"SSE 事件流异常: {e}")
            yield f"event: error\ndata: {json.dumps({'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/sessions", summary="获取会话列表")
async def list_sessions():
    """获取所有会话列表，按更新时间倒序"""
    sessions = chat_service.get_session_list()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}", summary="获取会话详情")
async def get_session(session_id: str):
    """获取指定会话的完整信息（含历史消息）"""
    info = chat_service.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")
    return info


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str):
    """删除指定会话及其历史记录"""
    ok = chat_service.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}
