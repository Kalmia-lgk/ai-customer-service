"""重置管理端账号密码。用法：python scripts/reset_password.py <邮箱> <新密码>"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: python scripts/reset_password.py <邮箱> <新密码>")
        sys.exit(1)
    email, new_pwd = sys.argv[1], sys.argv[2]
    if len(new_pwd) < 6:
        print("密码至少 6 位")
        sys.exit(1)
    init_db()
    with Session(engine) as db:
        user = db.exec(select(User).where(User.email == email)).first()
        if user is None:
            print(f"账号不存在: {email}")
            print("现有账号:", [u.email for u in db.exec(select(User)).all()])
            sys.exit(1)
        user.password_hash = hash_password(new_pwd)
        db.add(user)
        db.commit()
        print(f"已重置 {email}（{user.role}）的密码")


if __name__ == "__main__":
    main()
