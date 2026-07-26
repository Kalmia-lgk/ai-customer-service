"""工单：状态机 waiting → in_progress → resolved，消息落库 + WS 增量推送。"""
from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Ticket, TicketMessage, User, now_iso
from app.services.ws_manager import manager


def ticket_dict(t: Ticket) -> dict:
    return t.model_dump()


def message_dict(m: TicketMessage) -> dict:
    return m.model_dump()


def get_open_ticket(db: Session, session_id: str) -> Ticket | None:
    stmt = select(Ticket).where(
        Ticket.session_id == session_id, Ticket.status != "resolved"
    )
    return db.exec(stmt).first()


async def create_ticket(
    db: Session, session_id: str, visitor_id: str, reason: str
) -> tuple[Ticket, bool]:
    """建工单；若该会话已有未关闭工单则复用。返回 (工单, 是否新建)。"""
    existing = get_open_ticket(db, session_id)
    if existing:
        return existing, False
    ticket = Ticket(session_id=session_id, visitor_id=visitor_id, reason=reason[:500])
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    await manager.notify_admins({"type": "new_ticket", "ticket": ticket_dict(ticket)})
    return ticket, True


def require_ticket(db: Session, ticket_id: str, visitor_id: str | None = None) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or (visitor_id is not None and ticket.visitor_id != visitor_id):
        raise HTTPException(404, "工单不存在")
    return ticket


def list_tickets(db: Session, status: str | None = None) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(Ticket.status == status)
    return list(db.exec(stmt).all())


def list_ticket_messages(db: Session, ticket_id: str) -> list[TicketMessage]:
    stmt = (
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.id)
    )
    return list(db.exec(stmt).all())


async def claim_ticket(db: Session, ticket: Ticket, agent: User) -> Ticket:
    if ticket.status == "resolved":
        raise HTTPException(400, "工单已关闭")
    ticket.status = "in_progress"
    ticket.assignee_id = agent.id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    await add_message(db, ticket, "system", "系统", f"客服 {agent.name} 已接入对话")
    await manager.broadcast_ticket_event(
        ticket.id, {"type": "ticket_update", "ticket": ticket_dict(ticket)}
    )
    return ticket


async def add_message(
    db: Session, ticket: Ticket, sender: str, sender_name: str, content: str
) -> TicketMessage:
    msg = TicketMessage(
        ticket_id=ticket.id, sender=sender, sender_name=sender_name, content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    await manager.broadcast_ticket_event(
        ticket.id, {"type": "ticket_message", "message": message_dict(msg)}
    )
    return msg


async def resolve_ticket(db: Session, ticket: Ticket, agent: User) -> Ticket:
    ticket.status = "resolved"
    ticket.resolved_at = now_iso()
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    await add_message(db, ticket, "system", "系统", f"客服 {agent.name} 已将工单标记为解决")
    await manager.broadcast_ticket_event(
        ticket.id, {"type": "ticket_update", "ticket": ticket_dict(ticket)}
    )
    return ticket
