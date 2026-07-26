"""SQLite 数据库引擎与会话管理（把 SQLite 当"单文件版 MySQL"用）。"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "app.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    # FastAPI 多线程处理请求，SQLite 默认限制同线程访问，需放开
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   # 改善并发读写
    cursor.execute("PRAGMA foreign_keys=ON")    # SQLite 默认不启用外键约束
    cursor.close()


def init_db() -> None:
    """建表（等价于执行各模型对应的 CREATE TABLE IF NOT EXISTS）。"""
    import app.models  # noqa: F401  确保模型已注册到 metadata

    SQLModel.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：每个请求一个数据库会话。"""
    with Session(engine) as session:
        yield session
