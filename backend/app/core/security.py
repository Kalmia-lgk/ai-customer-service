# ============================================================
# 安全模块 - JWT 令牌生成/验证 + 密码哈希
# ============================================================
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from loguru import logger

from app.core.config import settings


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(staff_id: str, staff_name: str = "管理员") -> str:
    """
    创建 JWT 访问令牌
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": staff_id,
        "name": staff_name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token


def verify_token(token: str) -> dict | None:
    """
    验证 JWT 令牌，返回 payload 或 None
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT 验证失败: {e}")
        return None


def get_admin_password_hash() -> str:
    """
    获取管理员密码哈希
    优先级: data/settings.json > .env 默认密码
    """
    # 检查运行时设置
    try:
        from app.services.settings_service import settings_service
        runtime_hash = settings_service.get_password_hash()
        if runtime_hash:
            return runtime_hash
    except Exception:
        pass
    # 回退到 .env 默认密码
    return hash_password(settings.ADMIN_PASSWORD)
