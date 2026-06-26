# ============================================================
# 转人工工单服务 - 工单队列 CRUD + JSON 文件持久化
# ============================================================
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.schemas.models import EscalationTicket

# 数据目录
DATA_DIR = Path(settings.UPLOAD_DIR).parent / "data"


class EscalationService:
    """
    工单队列管理
    使用 JSON 文件持久化 + 线程锁防并发
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()  # 可重入锁，防止 self._save() 死锁
        self._file = DATA_DIR / "escalations.json"
        self._tickets: dict[str, dict] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()
        logger.info(f"工单服务初始化完成, {len(self._tickets)} 个历史工单")

    def _load(self) -> None:
        """从文件加载工单"""
        try:
            if self._file.exists():
                data = json.loads(self._file.read_text("utf-8"))
                for t in data:
                    self._tickets[t["ticket_id"]] = t
        except Exception as e:
            logger.error(f"加载工单文件失败: {e}")

    def _save(self) -> None:
        """保存工单到文件"""
        try:
            with self._lock:
                self._file.write_text(
                    json.dumps(list(self._tickets.values()), ensure_ascii=False, indent=2),
                    "utf-8",
                )
        except Exception as e:
            logger.error(f"保存工单文件失败: {e}")

    # ==================== 客户接口 ====================

    def create_ticket(
        self,
        session_id: str,
        reason: str = "用户请求转人工",
        conversation_snapshot: list[dict] | None = None,
    ) -> dict:
        """创建新的转人工工单"""
        ticket_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        ticket = {
            "ticket_id": ticket_id,
            "session_id": session_id,
            "customer_name": "匿名用户",
            "status": "waiting",
            "priority": "medium",
            "reason": reason,
            "assigned_staff_id": None,
            "assigned_staff_name": None,
            "created_at": now,
            "resolved_at": None,
            "messages": [],
            "conversation_snapshot": conversation_snapshot or [],
        }

        with self._lock:
            self._tickets[ticket_id] = ticket
            self._save()

        logger.info(f"新工单创建: {ticket_id}, 原因: {reason}")
        return dict(ticket)

    def get_ticket_status(self, ticket_id: str) -> dict | None:
        """查询工单状态（供客户轮询）"""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        return {
            "ticket_id": ticket["ticket_id"],
            "status": ticket["status"],
            "assigned_staff_name": ticket.get("assigned_staff_name"),
            "messages": ticket.get("messages", []),
        }

    # ==================== 管理端接口 ====================

    def get_pending_tickets(self) -> list[dict]:
        """获取所有待处理工单（按创建时间倒序）"""
        tickets = [t for t in self._tickets.values() if t["status"] in ("waiting", "in_progress")]
        tickets.sort(key=lambda t: t["created_at"], reverse=True)
        return [dict(t) for t in tickets]

    def get_all_tickets(self) -> list[dict]:
        """获取所有工单"""
        tickets = list(self._tickets.values())
        tickets.sort(key=lambda t: t["created_at"], reverse=True)
        return [dict(t) for t in tickets]

    def take_ticket(self, ticket_id: str, staff_id: str, staff_name: str) -> dict | None:
        """管理员接管工单"""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        if ticket["status"] != "waiting":
            return None  # 已被其他人接管

        with self._lock:
            ticket["status"] = "in_progress"
            ticket["assigned_staff_id"] = staff_id
            ticket["assigned_staff_name"] = staff_name
            ticket["messages"].append({
                "role": "system",
                "content": f"人工客服 {staff_name} 已接入",
                "timestamp": datetime.now().isoformat(),
            })
            self._save()

        logger.info(f"工单 {ticket_id} 已被 {staff_name} 接管")
        return dict(ticket)

    def reply_ticket(self, ticket_id: str, staff_id: str, message: str) -> dict | None:
        """管理员回复工单"""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        if ticket["status"] != "in_progress":
            return None

        msg = {
            "role": "assistant",
            "content": message,
            "staff_name": ticket.get("assigned_staff_name", "客服"),
            "timestamp": datetime.now().isoformat(),
        }

        with self._lock:
            ticket["messages"].append(msg)
            self._save()

        return dict(ticket)

    def resolve_ticket(self, ticket_id: str, staff_id: str) -> dict | None:
        """管理员解决/关闭工单"""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None

        with self._lock:
            ticket["status"] = "resolved"
            ticket["resolved_at"] = datetime.now().isoformat()
            ticket["messages"].append({
                "role": "system",
                "content": "工单已解决，感谢您的反馈！",
                "timestamp": datetime.now().isoformat(),
            })
            self._save()

        logger.info(f"工单 {ticket_id} 已解决")
        return dict(ticket)

    def get_stats(self) -> dict:
        """获取工单统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        resolved_today = sum(
            1 for t in self._tickets.values()
            if t["status"] == "resolved" and (t.get("resolved_at") or "").startswith(today)
        )
        active = sum(1 for t in self._tickets.values() if t["status"] in ("waiting", "in_progress"))
        return {
            "active_escalations": active,
            "resolved_today": resolved_today,
            "total_tickets": len(self._tickets),
        }

    def customer_send_message(self, ticket_id: str, message: str) -> dict | None:
        """客户在工单中发送消息"""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return None
        if ticket["status"] not in ("in_progress",):
            return None

        msg = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }

        with self._lock:
            ticket["messages"].append(msg)
            self._save()

        return dict(ticket)


# 单例
escalation_service = EscalationService()
