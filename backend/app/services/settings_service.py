"""运行时配置：settings 表读写。首次启动用 .env 默认值播种。"""
from __future__ import annotations

from sqlmodel import Session, select

from app.config import settings as env
from app.db import engine
from app.models import Setting

LLM_KEYS = (
    "llm_base_url",
    "llm_api_key",
    "llm_chat_model",
    "llm_intent_model",
    "llm_embedding_model",
)


def seed_defaults() -> None:
    """settings 表中缺失的键用 .env 值补齐（只在键不存在时写入，不覆盖在线修改）。"""
    defaults = env.llm_defaults()
    with Session(engine) as db:
        for key in LLM_KEYS:
            if db.get(Setting, key) is None:
                db.add(Setting(key=key, value=defaults.get(key, "")))
        db.commit()


def get_llm_config() -> dict[str, str]:
    with Session(engine) as db:
        rows = db.exec(select(Setting).where(Setting.key.in_(LLM_KEYS))).all()
    cfg = {row.key: row.value for row in rows}
    defaults = env.llm_defaults()
    return {key: cfg.get(key) or defaults.get(key, "") for key in LLM_KEYS}


def update_llm_config(values: dict[str, str]) -> None:
    with Session(engine) as db:
        for key in LLM_KEYS:
            if key not in values:
                continue
            row = db.get(Setting, key)
            if row is None:
                db.add(Setting(key=key, value=values[key]))
            else:
                row.value = values[key]
                db.add(row)
        db.commit()
