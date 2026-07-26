"""应用配置：读取 .env，提供路径常量。

.env 只提供"首次启动的默认值"；LLM 四元组等运行时可改的配置
以 SQLite settings 表为准（见 services/settings_service.py）。
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
STATIC_DIR = PROJECT_ROOT / "static"
STATIC_ADMIN_DIR = PROJECT_ROOT / "static-admin"
STATIC_SHARED_DIR = PROJECT_ROOT / "static-shared"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AI智能客服系统"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    JWT_SECRET: str = "change-me-to-a-random-secret-in-production"
    JWT_EXPIRE_HOURS: int = 8

    # LLM 默认值（首次启动写入 settings 表，之后以表为准）
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_API_KEY: str = ""
    LLM_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V4-Flash"
    LLM_INTENT_MODEL: str = ""  # 意图分类用的小模型，留空则用 CHAT_MODEL
    LLM_EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # 兼容旧 .env 的字段名（存在则作为 LLM_* 的回退来源）
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_MODEL: str = ""
    SILICONFLOW_BASE_URL: str = ""

    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RETRIEVAL_TOP_K: int = 4
    RETRIEVAL_MIN_SCORE: float = 0.35

    MAX_UPLOAD_SIZE_MB: int = 20

    def llm_defaults(self) -> dict[str, str]:
        """合并新旧 .env 字段，产出 LLM 配置默认值。"""
        return {
            "llm_base_url": self.SILICONFLOW_BASE_URL or self.LLM_BASE_URL,
            "llm_api_key": self.SILICONFLOW_API_KEY or self.LLM_API_KEY,
            "llm_chat_model": self.SILICONFLOW_MODEL or self.LLM_CHAT_MODEL,
            "llm_intent_model": self.LLM_INTENT_MODEL,
            "llm_embedding_model": self.LLM_EMBEDDING_MODEL,
        }


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
