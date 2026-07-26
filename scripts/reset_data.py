"""清空业务数据（会话/消息/工单/知识库），保留用户账号。

用途：交付前清理测试数据，或需要"重置系统"时使用。
用法：python scripts/reset_data.py [--drop-test-users]
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlmodel import Session, delete, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import (  # noqa: E402
    ChatSession, KnowledgeDoc, Message, Ticket, TicketMessage, User,
)
from app.rag.store import get_store  # noqa: E402
from app.config import UPLOAD_DIR  # noqa: E402

TEST_USER_SUFFIXES = ("@test.local", "e2e-admin@outlook.com")


def main() -> None:
    init_db()
    drop_test_users = "--drop-test-users" in sys.argv
    with Session(engine) as db:
        for model in (Message, ChatSession, TicketMessage, Ticket, KnowledgeDoc):
            db.exec(delete(model))
        if drop_test_users:
            for u in db.exec(select(User)).all():
                if any(u.email.endswith(s) or u.email == s for s in TEST_USER_SUFFIXES):
                    db.delete(u)
                    print(f"删除测试账号: {u.email}")
        db.commit()

    # 清空向量库与上传文件
    get_store().reset()
    for f in UPLOAD_DIR.iterdir():
        if f.name != ".gitkeep":
            f.unlink()
    print("已清空：会话 / 消息 / 工单 / 知识库文档 / 向量库 / uploads")


if __name__ == "__main__":
    main()
