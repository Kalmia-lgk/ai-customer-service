# ============================================================
# 管理端 API 路由 - 登录、工单管理、统计、会话监控
# ============================================================
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_password,
    get_admin_password_hash,
)
from app.core.deps import get_current_admin, require_role
from app.schemas.models import (
    AdminLoginRequest,
    AdminLoginResponse,
    EscalationReplyRequest,
    EscalationListResponse,
)
from app.services.chat_service import ChatService
from app.services.escalation_service import escalation_service
from app.services.document_service import DocumentService
from app.services.connection_manager import connection_manager

router = APIRouter(prefix="/api/admin", tags=["管理端"])

chat_service = ChatService()
doc_service = DocumentService()


# ==================== 认证 ====================

@router.post("/login", summary="Login")
async def admin_login(req: AdminLoginRequest):
    from app.services.user_service import user_service
    try:
        return user_service.login(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/register", summary="Register")
async def admin_register(req: dict):
    from app.services.user_service import user_service
    try:
        return user_service.register(req.get("email",""), req.get("password",""), req.get("name",""))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", summary="获取当前管理员信息")
async def get_me(admin: dict = Depends(get_current_admin)):
    """验证令牌有效性，返回当前管理员信息"""
    return admin


# ==================== 工单管理 ====================

@router.get("/escalations", summary="获取工单列表")
async def list_escalations(
    status_filter: str = "all",
    admin: dict = Depends(get_current_admin),
):
    """
    获取工单列表
    status_filter: all / waiting / in_progress / resolved
    """
    if status_filter == "all":
        tickets = escalation_service.get_all_tickets()
    elif status_filter == "pending":
        tickets = escalation_service.get_pending_tickets()
    else:
        all_tickets = escalation_service.get_all_tickets()
        tickets = [t for t in all_tickets if t["status"] == status_filter]

    waiting = sum(1 for t in tickets if t["status"] == "waiting")
    in_progress = sum(1 for t in tickets if t["status"] == "in_progress")

    return EscalationListResponse(
        tickets=tickets,
        waiting_count=waiting,
        in_progress_count=in_progress,
    )


@router.post("/escalations/{ticket_id}/take", summary="接管工单")
async def take_escalation(
    ticket_id: str,
    admin: dict = Depends(get_current_admin),
):
    """管理员接管工单，状态 waiting → in_progress"""
    ticket = escalation_service.take_ticket(
        ticket_id=ticket_id,
        staff_id=admin["staff_id"],
        staff_name=admin["staff_name"],
    )
    if not ticket:
        raise HTTPException(status_code=400, detail="工单不存在或已被接管")

    # 通知客户人工已接入
    await connection_manager.send_to_customer(ticket_id, {
        "type": "human_joined",
        "staff_name": admin["staff_name"],
        "ticket_id": ticket_id,
    })

    # 广播状态更新
    await connection_manager.broadcast_to_admins({
        "type": "ticket_updated",
        "ticket": ticket,
    })

    logger.info(f"[管理端] {admin['staff_name']} 接管工单 {ticket_id}")
    return {"success": True, "ticket": ticket}


@router.post("/escalations/{ticket_id}/reply", summary="回复工单")
async def reply_escalation(
    ticket_id: str,
    req: EscalationReplyRequest,
    admin: dict = Depends(get_current_admin),
):
    """管理员回复客户"""
    ticket = escalation_service.reply_ticket(
        ticket_id=ticket_id,
        staff_id=admin["staff_id"],
        message=req.message,
    )
    if not ticket:
        raise HTTPException(status_code=400, detail="工单不存在或状态不允许")

    # 推送回复给客户
    sent = await connection_manager.send_to_customer(ticket_id, {
        "type": "human_reply",
        "message": req.message,
        "staff_name": admin["staff_name"],
        "ticket_id": ticket_id,
    })

    return {"success": True, "ticket": ticket, "delivered": sent}


@router.post("/escalations/{ticket_id}/resolve", summary="解决工单")
async def resolve_escalation(
    ticket_id: str,
    admin: dict = Depends(get_current_admin),
):
    """管理员解决/关闭工单"""
    ticket = escalation_service.resolve_ticket(
        ticket_id=ticket_id,
        staff_id=admin["staff_id"],
    )
    if not ticket:
        raise HTTPException(status_code=400, detail="工单不存在")

    # 通知客户
    await connection_manager.send_to_customer(ticket_id, {
        "type": "escalation_resolved",
        "ticket_id": ticket_id,
        "message": "人工服务已结束，感谢您的反馈！",
    })

    # 广播更新
    await connection_manager.broadcast_to_admins({
        "type": "ticket_updated",
        "ticket": ticket,
    })

    logger.info(f"[管理端] {admin['staff_name']} 解决工单 {ticket_id}")
    return {"success": True, "ticket": ticket}


# ==================== 统计 ====================

@router.get("/stats", summary="获取仪表盘统计")
async def get_stats(admin: dict = Depends(get_current_admin)):
    """管理端仪表盘统计数据"""
    esc_stats = escalation_service.get_stats()
    kb_stats = doc_service.get_stats()
    sessions = chat_service.get_session_list()

    return {
        "total_conversations": len(sessions),
        "active_escalations": esc_stats["active_escalations"],
        "resolved_today": esc_stats["resolved_today"],
        "total_tickets": esc_stats["total_tickets"],
        "kb_doc_count": kb_stats.get("document_count", 0),
        "kb_chunk_count": kb_stats.get("total_chunks", 0),
        "kb_total_size_mb": kb_stats.get("total_size_mb", 0),
    }


# ==================== 会话监控 ====================

@router.get("/conversations", summary="获取所有会话")
async def list_conversations(admin: dict = Depends(get_current_admin)):
    """查看所有客户会话列表"""
    return {"sessions": chat_service.get_session_list()}


@router.get("/conversations/{session_id}", summary="查看会话详情")
async def get_conversation(session_id: str, admin: dict = Depends(get_current_admin)):
    """查看指定会话的完整对话记录"""
    info = chat_service.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")
    return info


# ==================== 用户管理（仅 super_admin） ====================

@router.get("/users", summary="List users")
async def list_users(admin: dict = Depends(require_role("super_admin"))):
    from app.services.user_service import user_service
    return {"users": user_service.list_users()}


@router.post("/users", summary="Create user")
async def create_user(req: dict, admin: dict = Depends(require_role("super_admin"))):
    from app.services.user_service import user_service
    try:
        return user_service.create_user(
            req.get("email",""), req.get("password",""),
            req.get("name",""), req.get("role","agent"), admin["email"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{email}/role", summary="Change role")
async def update_user_role(email: str, req: dict, admin: dict = Depends(get_current_admin)):
    from app.services.user_service import user_service
    try:
        return user_service.update_user_role(email, req.get("role",""), admin["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{email}", summary="Delete user")
async def delete_user(email: str, admin: dict = Depends(require_role("super_admin"))):
    from app.services.user_service import user_service
    try:
        return user_service.delete_user(email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 系统设置 ====================

@router.get("/settings", summary="Get settings")
async def get_settings(admin: dict = Depends(get_current_admin)):
    from app.services.settings_service import settings_service
    config = settings_service.get_api_config()
    config["current_role"] = admin["role"]
    config["current_email"] = admin["email"]
    return config


@router.post("/settings/change-password", summary="Change password")
async def change_password(req: dict, admin: dict = Depends(get_current_admin)):
    from app.services.user_service import user_service
    try:
        return user_service.change_password(
            admin["staff_id"],
            req.get("current_password",""),
            req.get("new_password","")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings/api-config", summary="Update API config")
async def update_api_config(req: dict, admin: dict = Depends(require_role("super_admin"))):
    from app.services.settings_service import settings_service
    from app.core.llm_client import llm_client
    settings_service.set_api_config(req)
    llm_client.reload_config()
    return {"success": True, "demo_mode": llm_client._demo_mode, "provider": llm_client.provider}
