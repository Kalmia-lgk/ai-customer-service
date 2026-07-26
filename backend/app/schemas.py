"""请求 / 响应模型（消灭裸 dict，等价于给每个接口定义严格的表结构）。"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


# ---------- 聊天 ----------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    visitor_id: str = Field(min_length=8, max_length=64)
    session_id: str | None = None


# ---------- 认证 ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class CreateUserRequest(RegisterRequest):
    role: str = Field(default="agent", pattern="^(super_admin|agent)$")


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---------- 工单 ----------

class EscalateRequest(BaseModel):
    visitor_id: str
    session_id: str
    reason: str = Field(default="", max_length=500)


class TicketReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CustomerTicketReplyRequest(TicketReplyRequest):
    visitor_id: str


# ---------- 设置 ----------

class LLMSettingsUpdate(BaseModel):
    llm_base_url: str = Field(min_length=1)
    llm_api_key: str = ""
    llm_chat_model: str = Field(min_length=1)
    llm_intent_model: str = ""
    llm_embedding_model: str = Field(min_length=1)
