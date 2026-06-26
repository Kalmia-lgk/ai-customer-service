# ============================================================
# Pydantic 数据模型 (Schema) - 定义所有 API 请求/响应模型
# ============================================================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ==================== 聊天相关模型 ====================

class ChatMessage(BaseModel):
    """单条聊天消息"""
    role: str = Field(..., description="角色：user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """POST /api/chat 请求体"""
    session_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="会话 ID，不传则自动创建新会话",
    )
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    stream: bool = Field(default=True, description="是否启用流式输出")


class SourceCitation(BaseModel):
    """知识库引用来源"""
    document_name: str = Field(..., description="文档名称")
    snippet: str = Field(..., description="引用片段（摘要）")
    score: float = Field(..., description="相关度分数")
    page: Optional[int] = Field(default=None, description="所在页码（PDF 等）")


class ChatResponse(BaseModel):
    """非流式聊天的响应体"""
    session_id: str = Field(..., description="会话 ID")
    message: str = Field(..., description="AI 回复内容")
    sources: list[SourceCitation] = Field(
        default_factory=list, description="引用的知识库来源"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(), description="时间戳"
    )


# ==================== 会话管理模型 ====================

class SessionMeta(BaseModel):
    """会话元数据"""
    session_id: str = Field(..., description="会话 ID")
    title: str = Field(default="新会话", description="会话标题")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="最后更新时间")
    message_count: int = Field(default=0, description="消息数量")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: list[SessionMeta]


# ==================== 文档管理模型 ====================

class DocumentInfo(BaseModel):
    """文档信息"""
    doc_id: str = Field(..., description="文档唯一 ID")
    filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型（后缀）")
    file_size: int = Field(..., description="文件大小（字节）")
    chunk_count: int = Field(default=0, description="向量块数量")
    uploaded_at: str = Field(..., description="上传时间")
    status: str = Field(default="active", description="状态：active / processing / error")


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: list[DocumentInfo]


class ReindexResponse(BaseModel):
    """重建索引响应"""
    success: bool
    message: str
    doc_count: int = 0
    total_chunks: int = 0


class UploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    message: str
    document: Optional[DocumentInfo] = None


# ==================== 通用响应模型 ====================

class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(default=None, description="错误码")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str
    llm_provider: str
    demo_mode: bool = False
    rag_available: bool = False
    chroma_chunks: int = 0


# ==================== 管理端认证模型 ====================

class AdminLoginRequest(BaseModel):
    """管理端登录请求"""
    email: str = Field(..., description="管理员邮箱")
    password: str = Field(..., min_length=1, description="密码")


class AdminLoginResponse(BaseModel):
    """管理端登录响应"""
    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = "bearer"
    staff_id: str = Field(..., description="员工 ID")
    staff_name: str = Field(..., description="员工姓名")
    expires_in: int = Field(..., description="过期时间（秒）")


# ==================== 工单/转人工模型 ====================

class EscalationTicket(BaseModel):
    """转人工工单"""
    ticket_id: str = Field(..., description="工单 ID")
    session_id: str = Field(..., description="关联的会话 ID")
    customer_name: str = Field(default="匿名用户", description="客户名称")
    status: str = Field(default="waiting", description="状态: waiting / in_progress / resolved")
    priority: str = Field(default="medium", description="优先级: low / medium / high")
    reason: str = Field(default="", description="转人工原因")
    assigned_staff_id: Optional[str] = Field(default=None, description="接单员工 ID")
    assigned_staff_name: Optional[str] = Field(default=None, description="接单员工姓名")
    created_at: str = Field(..., description="创建时间")
    resolved_at: Optional[str] = Field(default=None, description="解决时间")
    messages: list[dict] = Field(default_factory=list, description="人工对话消息列表")
    conversation_snapshot: list[dict] = Field(default_factory=list, description="转人工前的对话快照")


class EscalationCreateRequest(BaseModel):
    """创建工单请求"""
    session_id: str = Field(..., description="会话 ID")
    reason: str = Field(default="用户请求转人工", description="转人工原因")


class EscalationReplyRequest(BaseModel):
    """人工回复请求"""
    message: str = Field(..., min_length=1, description="回复内容")


class EscalationListResponse(BaseModel):
    """工单列表响应"""
    tickets: list[EscalationTicket]
    waiting_count: int = 0
    in_progress_count: int = 0


# ==================== 统计模型 ====================

class DashboardStats(BaseModel):
    """管理端仪表盘统计"""
    total_conversations: int = 0
    active_escalations: int = 0
    resolved_today: int = 0
    kb_doc_count: int = 0
    kb_chunk_count: int = 0
