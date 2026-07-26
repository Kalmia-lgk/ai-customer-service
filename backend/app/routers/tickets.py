"""工单路由：管理端（JWT）+ 访客端（visitor_id 校验）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_db
from app.models import ChatSession, User
from app.schemas import CustomerTicketReplyRequest, EscalateRequest, TicketReplyRequest
from app.security import get_current_user
from app.services import session_service, ticket_service

router = APIRouter(prefix="/api", tags=["工单"])


# ---------- 管理端 ----------

@router.get("/tickets")
async def admin_list_tickets(
    status: str | None = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ticket_service.list_tickets(db, status)


@router.get("/tickets/{ticket_id}/messages")
async def admin_ticket_messages(
    ticket_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id)
    return {
        "ticket": ticket,
        "messages": ticket_service.list_ticket_messages(db, ticket.id),
    }


@router.get("/tickets/{ticket_id}/context")
async def admin_ticket_context(
    ticket_id: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """工单关联会话的 AI 聊天记录，供客服了解前情。"""
    ticket = ticket_service.require_ticket(db, ticket_id)
    session = db.get(ChatSession, ticket.session_id)
    if session is None:
        return []
    return session_service.list_messages(db, session)


@router.post("/tickets/{ticket_id}/claim")
async def claim_ticket(
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id)
    return await ticket_service.claim_ticket(db, ticket, user)


@router.post("/tickets/{ticket_id}/reply")
async def agent_reply(
    ticket_id: str,
    req: TicketReplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id)
    return await ticket_service.add_message(db, ticket, "agent", user.name, req.content)


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id)
    return await ticket_service.resolve_ticket(db, ticket, user)


# ---------- 访客端 ----------

@router.post("/customer/escalate")
async def customer_escalate(req: EscalateRequest, db: Session = Depends(get_db)):
    """手动"转人工"按钮，与 Agent 的 escalate 节点走同一个服务函数。"""
    session_service.require_session(db, req.session_id, req.visitor_id)
    ticket, created = await ticket_service.create_ticket(
        db, req.session_id, req.visitor_id, req.reason or "访客手动请求人工客服"
    )
    return {"ticket": ticket, "created": created}


@router.get("/customer/active-ticket")
async def customer_active_ticket(
    visitor_id: str = Query(min_length=8),
    session_id: str = Query(min_length=8),
    db: Session = Depends(get_db),
):
    """查询当前会话是否有未关闭工单（刷新页面后恢复人工对话状态）。"""
    session_service.require_session(db, session_id, visitor_id)
    ticket = ticket_service.get_open_ticket(db, session_id)
    return {"ticket": ticket}


@router.get("/customer/tickets/{ticket_id}")
async def customer_ticket_detail(
    ticket_id: str,
    visitor_id: str = Query(min_length=8),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id, visitor_id)
    return {
        "ticket": ticket,
        "messages": ticket_service.list_ticket_messages(db, ticket.id),
    }


@router.post("/customer/tickets/{ticket_id}/reply")
async def customer_reply(
    ticket_id: str,
    req: CustomerTicketReplyRequest,
    db: Session = Depends(get_db),
):
    ticket = ticket_service.require_ticket(db, ticket_id, req.visitor_id)
    return await ticket_service.add_message(db, ticket, "customer", "访客", req.content)
