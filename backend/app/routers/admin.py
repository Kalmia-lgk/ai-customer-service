"""管理路由：统计概览 / 用户管理（超管）/ LLM 配置（超管，保存即热生效）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.db import get_db
from app.llm import get_gateway
from app.models import ChatSession, KnowledgeDoc, Message, Ticket, User
from app.rag.store import get_store
from app.schemas import CreateUserRequest, LLMSettingsUpdate
from app.security import get_current_user, hash_password, require_super_admin
from app.services import settings_service

router = APIRouter(prefix="/api/admin", tags=["管理"])


# ---------- 统计概览 ----------

@router.get("/stats")
async def stats(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    def count(model, *conditions) -> int:
        stmt = select(func.count()).select_from(model)
        for cond in conditions:
            stmt = stmt.where(cond)
        return db.exec(stmt).one()

    # 近 7 日会话量（created_at 是 ISO 字符串，前缀比较即按天分组）
    today = datetime.now(timezone.utc).date()
    daily: list[dict] = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        prefix = day.isoformat()
        n = db.exec(
            select(func.count()).select_from(ChatSession)
            .where(ChatSession.created_at.startswith(prefix))
        ).one()
        daily.append({"date": prefix[5:], "count": n})

    return {
        "sessions": count(ChatSession),
        "messages": count(Message),
        "documents": count(KnowledgeDoc),
        "chunks": get_store().chunk_count(),
        "tickets": {
            "waiting": count(Ticket, Ticket.status == "waiting"),
            "in_progress": count(Ticket, Ticket.status == "in_progress"),
            "resolved": count(Ticket, Ticket.status == "resolved"),
        },
        "daily_sessions": daily,
    }


# ---------- 用户管理（超管） ----------

@router.get("/users")
async def list_users(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.exec(select(User).order_by(User.created_at)).all()
    return [
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "created_at": u.created_at}
        for u in users
    ]


@router.post("/users")
async def create_user(
    req: CreateUserRequest,
    _: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if db.exec(select(User).where(User.email == req.email)).first():
        raise HTTPException(400, "该邮箱已存在")
    user = User(
        email=req.email, name=req.name,
        password_hash=hash_password(req.password), role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(400, "不能删除自己")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    # 先解除工单认领关系，否则 tickets.assignee_id 外键会阻止删除
    for ticket in db.exec(select(Ticket).where(Ticket.assignee_id == user_id)).all():
        ticket.assignee_id = None
        if ticket.status == "in_progress":
            ticket.status = "waiting"
        db.add(ticket)
    db.flush()
    db.delete(user)
    db.commit()
    return {"ok": True}


# ---------- LLM 配置（超管，保存即热生效） ----------

@router.get("/settings")
async def get_settings(_: User = Depends(require_super_admin)):
    return settings_service.get_llm_config()


@router.put("/settings")
async def update_settings(
    req: LLMSettingsUpdate, _: User = Depends(require_super_admin)
):
    settings_service.update_llm_config(req.model_dump())
    get_gateway().reload()  # 全局唯一实例，一处 reload 处处生效
    return {"ok": True}


@router.post("/settings/test")
async def test_settings(_: User = Depends(require_super_admin)):
    """用当前配置发一次最小对话，验证 Key/模型可用。"""
    gateway = get_gateway()
    if not gateway.is_configured:
        raise HTTPException(400, "尚未配置 API Key")
    try:
        parts = []
        async for token in gateway.chat_stream(
            [{"role": "user", "content": "回复「连接成功」四个字"}]
        ):
            parts.append(token)
            if len(parts) > 20:
                break
        return {"ok": True, "reply": "".join(parts)}
    except Exception as e:
        raise HTTPException(400, f"连接失败：{e}")
