# ============================================================
# 用户服务 - 注册即用 + 角色权限 (super_admin / admin / agent)
# ============================================================
from __future__ import annotations

import json
import os
import random
import string
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token

DATA_DIR = Path(settings.UPLOAD_DIR).parent / "data"
USERS_FILE = DATA_DIR / "users.json"


class UserService:

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: dict[str, dict] = {}
        self._codes: dict[str, dict] = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()
        logger.info(f"User service: {len(self._users)} users")

    def _load(self):
        try:
            if USERS_FILE.exists():
                self._users = json.loads(USERS_FILE.read_text("utf-8"))
        except Exception:
            self._users = {}

    def _save(self):
        with self._lock:
            USERS_FILE.write_text(json.dumps(self._users, ensure_ascii=False, indent=2), "utf-8")

    # ==================== 注册 ====================

    def register(self, email: str, password: str, name: str = "") -> dict:
        email = email.strip().lower()
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if email in self._users:
            raise ValueError("Email already registered")

        # 第一个注册的用户自动成为 super_admin
        role = "super_admin" if len(self._users) == 0 else "agent"
        if not name:
            name = email.split("@")[0]

        user = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "name": name,
            "password_hash": hash_password(password),
            "role": role,
            "verified": True,  # 注册即验证，无需邮箱验证码
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "system" if role == "super_admin" else "",
            "avatar": f"https://ui-avatars.com/api/?name={name}&background=4f46e5&color=fff",
        }

        with self._lock:
            self._users[email] = user
            self._save()

        logger.info(f"User registered: {email} role={role}")
        return {"success": True, "message": f"Registration successful. Role: {role}", "role": role}

    # ==================== 登录 ====================

    def login(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        user = self._users.get(email)
        if not user:
            raise ValueError("Email not registered")
        if not verify_password(password, user["password_hash"]):
            raise ValueError("Incorrect password")

        return self._make_login_response(user)

    def _make_login_response(self, user: dict) -> dict:
        token = create_access_token(user["user_id"], user["name"])
        return {
            "access_token": token, "token_type": "bearer",
            "user_id": user["user_id"], "email": user["email"],
            "name": user["name"], "role": user["role"],
            "avatar": user.get("avatar", ""),
            "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
        }

    # ==================== 角色权限 ====================

    def get_user_by_id(self, user_id: str) -> dict | None:
        for u in self._users.values():
            if u["user_id"] == user_id:
                return u
        return None

    def get_user_by_email(self, email: str) -> dict | None:
        return self._users.get(email.strip().lower())

    def is_super_admin(self, user_id: str) -> bool:
        u = self.get_user_by_id(user_id)
        return u is not None and u.get("role") == "super_admin"

    def is_admin_or_above(self, user_id: str) -> bool:
        u = self.get_user_by_id(user_id)
        return u is not None and u.get("role") in ("super_admin", "admin")

    # ==================== 用户管理（仅 super_admin） ====================

    def list_users(self) -> list[dict]:
        return [{
            "user_id": u["user_id"], "email": u["email"], "name": u["name"],
            "role": u["role"], "created_at": u.get("created_at", ""),
        } for u in self._users.values()]

    def create_user(self, email: str, password: str, name: str, role: str, created_by: str) -> dict:
        email = email.strip().lower()
        if email in self._users:
            raise ValueError("Email already exists")
        if role not in ("admin", "agent"):
            raise ValueError("Role must be admin or agent")

        user = {
            "user_id": str(uuid.uuid4()), "email": email, "name": name or email.split("@")[0],
            "password_hash": hash_password(password), "role": role, "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat(), "created_by": created_by,
            "avatar": f"https://ui-avatars.com/api/?name={name or email.split('@')[0]}&background=4f46e5&color=fff",
        }
        with self._lock:
            self._users[email] = user
            self._save()
        logger.info(f"User created: {email} role={role} by {created_by}")
        return {"success": True, "message": f"User {email} created as {role}"}

    def update_user_role(self, email: str, new_role: str, actor_email: str = "") -> dict:
        user = self._users.get(email.strip().lower())
        if not user:
            raise ValueError("User not found")
        if new_role not in ("super_admin", "admin", "agent"):
            raise ValueError("Invalid role")
        if email.strip().lower() == actor_email.strip().lower():
            # Self-demotion: super_admin can demote to admin/agent
            if user["role"] != "super_admin":
                raise ValueError("Only super_admin can change their own role")
            if new_role == "super_admin":
                raise ValueError("Already super_admin")
        else:
            # Changing someone else: only super_admin can do this
            actor = self._users.get(actor_email.strip().lower()) if actor_email else None
            if actor and actor["role"] != "super_admin":
                raise ValueError("Only super_admin can change roles")
        with self._lock:
            user["role"] = new_role
            self._save()
        logger.info(f"User {email} role -> {new_role} by {actor_email}")
        return {"success": True, "message": f"{email} is now {new_role}"}

    def delete_user(self, email: str) -> dict:
        email = email.strip().lower()
        user = self._users.get(email)
        if not user:
            raise ValueError("User not found")
        if user["role"] == "super_admin":
            raise ValueError("Cannot delete super_admin")
        with self._lock:
            del self._users[email]
            self._save()
        logger.info(f"User deleted: {email}")
        return {"success": True}

    def change_password(self, user_id: str, old_pw: str, new_pw: str) -> dict:
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        if not verify_password(old_pw, user["password_hash"]):
            raise ValueError("Current password is incorrect")
        if len(new_pw) < 6:
            raise ValueError("New password must be at least 6 characters")
        with self._lock:
            user["password_hash"] = hash_password(new_pw)
            self._save()
        return {"success": True, "message": "Password changed"}


user_service = UserService()
