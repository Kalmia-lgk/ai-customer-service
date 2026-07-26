"""SQLModel 表模型：一个类 = 表结构 + 数据校验模型。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    """管理端用户（超级管理员 / 客服）。"""

    __tablename__ = "users"

    id: str = Field(default_factory=new_id, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    password_hash: str
    role: str = Field(default="agent")  # super_admin / agent
    created_at: str = Field(default_factory=now_iso)


class ChatSession(SQLModel, table=True):
    """访客会话。visitor_id 由浏览器 localStorage 生成，实现匿名归属与隔离。"""

    __tablename__ = "sessions"

    id: str = Field(default_factory=new_id, primary_key=True)
    visitor_id: str = Field(index=True)
    title: str = Field(default="新会话")
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    role: str  # user / assistant
    content: str
    sources: str | None = None  # JSON 数组文本：知识库引用快照
    created_at: str = Field(default_factory=now_iso)


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(index=True)
    visitor_id: str = Field(index=True)
    status: str = Field(default="waiting")  # waiting / in_progress / resolved
    reason: str = ""
    assignee_id: str | None = Field(default=None, foreign_key="users.id")
    created_at: str = Field(default_factory=now_iso)
    resolved_at: str | None = None


class TicketMessage(SQLModel, table=True):
    __tablename__ = "ticket_messages"

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.id", index=True)
    sender: str  # customer / agent / system
    sender_name: str = ""
    content: str
    created_at: str = Field(default_factory=now_iso)


class KnowledgeDoc(SQLModel, table=True):
    """知识库文档元数据（原始文件在 uploads/，向量在 chroma_db/）。"""

    __tablename__ = "documents"

    id: str = Field(default_factory=new_id, primary_key=True)
    filename: str
    stored_name: str  # uploads/ 下的实际文件名（带 id 前缀防重名）
    size_bytes: int = 0
    chunk_count: int = 0
    status: str = Field(default="ready")  # processing / ready / failed
    error: str | None = None
    created_at: str = Field(default_factory=now_iso)


class Setting(SQLModel, table=True):
    """运行时可改的键值配置（LLM 四元组等），管理端在线修改。"""

    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str = ""
