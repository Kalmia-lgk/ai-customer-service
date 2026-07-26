"""聊天路由：唯一的 /api/chat（SSE），Agent 图就是处理链路本身。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Query
from loguru import logger
from sqlmodel import Session
from starlette.responses import StreamingResponse

from app.agent.graph import graph
from app.db import engine
from app.llm import get_gateway
from app.schemas import ChatRequest
from app.services import session_service

router = APIRouter(prefix="/api", tags=["聊天"])

NOT_CONFIGURED_HINT = (
    "系统尚未配置 AI 服务：请管理员登录管理端，在「设置」页填写 LLM API Key 后即可开始对话。"
)


def sse(data: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    async def gen():
        with Session(engine) as db:
            session = session_service.get_or_create_session(db, req.visitor_id, req.session_id)
            history = session_service.recent_history(db, session)
            session_service.append_message(db, session, "user", req.message)
            yield sse({"session_id": session.id}, "session")

            if not get_gateway().is_configured:
                yield sse({"content": NOT_CONFIGURED_HINT})
                session_service.append_message(db, session, "assistant", NOT_CONFIGURED_HINT)
                yield sse({}, "done")
                return

            state = {
                "user_message": req.message,
                "history": history,
                "session_id": session.id,
                "visitor_id": req.visitor_id,
            }
            answer_parts: list[str] = []
            sources: list[dict] = []
            try:
                async for payload in graph.astream(state, stream_mode="custom"):
                    event = payload.get("event")
                    if event == "token":
                        answer_parts.append(payload["content"])
                        yield sse({"content": payload["content"]})
                    elif event == "sources":
                        sources = payload["sources"]
                        yield sse({"sources": sources}, "sources")
                    elif event == "agent_step":
                        yield sse(payload, "agent_step")
                    elif event == "ticket":
                        yield sse(payload, "ticket")
            except Exception as e:
                logger.exception("聊天处理失败")
                yield sse({"message": f"处理失败：{e}"}, "error")

            if answer_parts:
                session_service.append_message(
                    db, session, "assistant", "".join(answer_parts), sources or None
                )
            yield sse({}, "done")

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------- 会话管理（visitor_id 强制匹配，实现访客隔离）----------

@router.get("/sessions")
async def get_sessions(visitor_id: str = Query(min_length=8)):
    with Session(engine) as db:
        return session_service.list_sessions(db, visitor_id)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, visitor_id: str = Query(min_length=8)):
    with Session(engine) as db:
        session = session_service.require_session(db, session_id, visitor_id)
        return session_service.list_messages(db, session)


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str, visitor_id: str = Query(min_length=8)):
    with Session(engine) as db:
        session = session_service.require_session(db, session_id, visitor_id)
        session_service.delete_session(db, session)
    return {"ok": True}
