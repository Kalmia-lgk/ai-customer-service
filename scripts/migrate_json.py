"""一次性迁移脚本：data/users.json（旧版）→ SQLite users 表。

用法（项目根目录执行）：
    python scripts/migrate_json.py
幂等：已存在的邮箱自动跳过，可重复执行。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import User  # noqa: E402

USERS_JSON = PROJECT_ROOT / "data" / "users.json"


def main() -> None:
    if not USERS_JSON.exists():
        print(f"未找到 {USERS_JSON}，无需迁移")
        return

    data = json.loads(USERS_JSON.read_text("utf-8"))
    init_db()
    migrated = skipped = 0
    with Session(engine) as db:
        for email, info in data.items():
            if db.exec(select(User).where(User.email == email)).first():
                skipped += 1
                continue
            role = info.get("role", "agent")
            if role not in ("super_admin", "agent"):
                role = "agent"  # 旧三级角色并入两级
            db.add(User(
                id=info.get("user_id") or None,
                email=email,
                name=info.get("name", email.split("@")[0]),
                password_hash=info["password_hash"],  # bcrypt 哈希直接沿用
                role=role,
                created_at=info.get("created_at", ""),
            ))
            migrated += 1
        db.commit()
    print(f"迁移完成：新增 {migrated} 个用户，跳过 {skipped} 个已存在用户")


if __name__ == "__main__":
    main()
