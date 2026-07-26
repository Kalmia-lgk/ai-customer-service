"""认证路由：登录 / 首次注册 / 当前用户 / 改密码。

注册策略：系统中不存在 super_admin 时开放注册（首个注册者即超管），
之后注册接口自动关闭，账号由管理员在后台创建。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_db
from app.models import User
from app.schemas import ChangePasswordRequest, LoginRequest, RegisterRequest
from app.security import create_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


def user_public(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


def has_super_admin(db: Session) -> bool:
    return db.exec(select(User).where(User.role == "super_admin")).first() is not None


@router.get("/status")
async def auth_status(db: Session = Depends(get_db)):
    """前端据此决定显示登录还是初始化注册。"""
    return {"registration_open": not has_super_admin(db)}


@router.post("/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if has_super_admin(db):
        raise HTTPException(403, "系统已初始化，请联系管理员创建账号")
    if db.exec(select(User).where(User.email == req.email)).first():
        raise HTTPException(400, "该邮箱已注册")
    user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="super_admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user), "user": user_public(user)}


@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.exec(select(User).where(User.email == req.email)).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    return {"token": create_token(user), "user": user_public(user)}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return user_public(user)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = hash_password(req.new_password)
    db.add(user)
    db.commit()
    return {"ok": True}
