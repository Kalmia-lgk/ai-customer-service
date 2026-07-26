"""会话与消息：全部落 SQLite，按 visitor_id 隔离。"""
from __future__ import annotations

import json

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import ChatSession, Message, now_iso

HISTORY_LIMIT = 8  # 传给 LLM 的最近消息条数


def get_or_create_session(db: Session, visitor_id: str, session_id: str | None) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.visitor_id == visitor_id:
            return session
    session = ChatSession(visitor_id=visitor_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def require_session(db: Session, session_id: str, visitor_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.visitor_id != visitor_id:
        raise HTTPException(404, "会话不存在")
    return session


def list_sessions(db: Session, visitor_id: str) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .where(ChatSession.visitor_id == visitor_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
    )
    return list(db.exec(stmt).all())


def list_messages(db: Session, session: ChatSession) -> list[dict]:
    stmt = select(Message).where(Message.session_id == session.id).order_by(Message.id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at,
        }
        for m in db.exec(stmt).all()
    ]


def recent_history(db: Session, session: ChatSession) -> list[dict]:
    """给 LLM 的最近几轮消息（不含 sources 等附加信息）。"""
    stmt = (
        select(Message)
        .where(Message.session_id == session.id)
        .order_by(Message.id.desc())
        .limit(HISTORY_LIMIT)
    )
    rows = list(db.exec(stmt).all())[::-1]
    return [{"role": m.role, "content": m.content} for m in rows]


def append_message(
    db: Session,
    session: ChatSession,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> Message:
    msg = Message(
        session_id=session.id,
        role=role,
        content=content,
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
    )
    # 首条用户消息作为会话标题
    if role == "user" and session.title == "新会话":
        session.title = content[:30]
    session.updated_at = now_iso()
    db.add(msg)
    db.add(session)
    db.commit()
    db.refresh(msg)
    return msg


def delete_session(db: Session, session: ChatSession) -> None:
    for m in db.exec(select(Message).where(Message.session_id == session.id)).all():
        db.delete(m)
    db.delete(session)
    db.commit()
