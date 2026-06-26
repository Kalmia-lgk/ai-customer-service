# ============================================================
# 应用配置中心 - 使用 pydantic-settings 管理所有环境变量
# ============================================================
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# 获取项目根目录（backend/app/core/config.py → backend/ → 项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """
    全局应用配置类
    所有配置项都可通过环境变量 / .env 文件覆盖
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== 应用基础配置 ==========
    APP_NAME: str = "AI智能客服系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ========== LLM 提供商 ==========
    LLM_PROVIDER: Literal["openai", "anthropic", "groq"] = "openai"

    # ========== OpenAI 配置 ==========
    OPENAI_API_KEY: str = "sk-your-openai-api-key-here"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # ========== Anthropic 配置 ==========
    ANTHROPIC_API_KEY: str = "sk-ant-your-anthropic-api-key-here"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # ========== Groq 配置 ==========
    GROQ_API_KEY: str = "gsk_your-groq-api-key-here"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ========== 知识库配置 ==========
    CHROMA_PERSIST_DIR: str = str(PROJECT_ROOT / "chroma_db")
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 4

    # ========== 文件上传 ==========
    MAX_UPLOAD_SIZE_MB: int = 100
    UPLOAD_DIR: str = str(PROJECT_ROOT / "uploads")

    # ========== CORS ==========
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    # ========== 管理端认证 ==========
    JWT_SECRET: str = "change-me-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    ADMIN_EMAIL: str = "admin@aicc.com"
    ADMIN_PASSWORD: str = "admin123"  # 首次启动时自动哈希

    @property
    def max_upload_bytes(self) -> int:
        """将 MB 转换为字节"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def get_llm_api_key(self) -> str:
        """根据当前提供商获取对应的 API Key"""
        key_map = {
            "openai": self.OPENAI_API_KEY,
            "anthropic": self.ANTHROPIC_API_KEY,
            "groq": self.GROQ_API_KEY,
        }
        return key_map[self.LLM_PROVIDER]

    def get_llm_model(self) -> str:
        """根据当前提供商获取对应的模型名"""
        model_map = {
            "openai": self.OPENAI_MODEL,
            "anthropic": self.ANTHROPIC_MODEL,
            "groq": self.GROQ_MODEL,
        }
        return model_map[self.LLM_PROVIDER]


# 单例配置实例，全局复用
settings = Settings()

# 确保必要目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
