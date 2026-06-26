# ============================================================
# 运行时设置服务 - 管理可在 UI 中修改的配置（密码、API Key）
# 存储于 data/settings.json，运行时动态读取，重启不丢失
# ============================================================
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from loguru import logger

from app.core.config import settings as env_settings

DATA_DIR = Path(env_settings.UPLOAD_DIR).parent / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"


class SettingsService:
    """
    运行时配置管理
    优先级: data/settings.json > .env 环境变量
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict = {}
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load()

    def _load(self) -> None:
        try:
            if SETTINGS_FILE.exists():
                self._data = json.loads(SETTINGS_FILE.read_text("utf-8"))
        except Exception as e:
            logger.warning(f"加载 settings.json 失败: {e}")
            self._data = {}
        # 确保必要字段存在
        self._data.setdefault("password_hash", "")
        self._data.setdefault("llm_provider", "")
        self._data.setdefault("openai_api_key", "")
        self._data.setdefault("openai_model", "")
        self._data.setdefault("groq_api_key", "")
        self._data.setdefault("groq_model", "")

    def _save(self) -> None:
        with self._lock:
            SETTINGS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), "utf-8"
            )

    # ==================== 密码管理 ====================

    def get_password_hash(self) -> str:
        """获取运行时密码哈希（为空则从 .env 生成）"""
        return self._data.get("password_hash", "")

    def set_password(self, new_password_hash: str) -> None:
        """更新密码哈希"""
        with self._lock:
            self._data["password_hash"] = new_password_hash
            self._save()
        logger.info("密码已更新")

    # ==================== API 配置 ====================

    def get_api_config(self) -> dict:
        """获取当前生效的 API 配置"""
        return {
            "llm_provider": self._data.get("llm_provider") or env_settings.LLM_PROVIDER,
            "openai_api_key": self._mask_key(self._data.get("openai_api_key") or env_settings.OPENAI_API_KEY),
            "openai_model": self._data.get("openai_model") or env_settings.OPENAI_MODEL,
            "groq_api_key": self._mask_key(self._data.get("groq_api_key") or env_settings.GROQ_API_KEY),
            "groq_model": self._data.get("groq_model") or env_settings.GROQ_MODEL,
            "demo_mode": self._is_demo_mode(),
        }

    def get_active_api_key(self) -> str:
        """获取当前实际使用的 API Key（不脱敏）"""
        provider = self._data.get("llm_provider") or env_settings.LLM_PROVIDER
        if provider == "openai":
            return self._data.get("openai_api_key") or env_settings.OPENAI_API_KEY
        elif provider == "groq":
            return self._data.get("groq_api_key") or env_settings.GROQ_API_KEY
        return ""

    def get_active_provider(self) -> str:
        return self._data.get("llm_provider") or env_settings.LLM_PROVIDER

    def get_active_model(self) -> str:
        provider = self.get_active_provider()
        if provider == "openai":
            return self._data.get("openai_model") or env_settings.OPENAI_MODEL
        elif provider == "groq":
            return self._data.get("groq_model") or env_settings.GROQ_MODEL
        return env_settings.get_llm_model()

    def set_api_config(self, config: dict) -> None:
        """更新 API 配置"""
        with self._lock:
            if "llm_provider" in config:
                self._data["llm_provider"] = config["llm_provider"]
            if "openai_api_key" in config and config["openai_api_key"]:
                self._data["openai_api_key"] = config["openai_api_key"]
            if "openai_model" in config and config["openai_model"]:
                self._data["openai_model"] = config["openai_model"]
            if "groq_api_key" in config and config["groq_api_key"]:
                self._data["groq_api_key"] = config["groq_api_key"]
            if "groq_model" in config and config["groq_model"]:
                self._data["groq_model"] = config["groq_model"]
            self._save()
        logger.info(f"API 配置已更新: provider={self.get_active_provider()}")

    def _is_demo_mode(self) -> bool:
        """检测是否 Demo 模式"""
        api_key = self.get_active_api_key()
        if not api_key or len(api_key) < 10:
            return True
        if "sk-your-" in api_key or "gsk_your-" in api_key:
            return True
        return os.getenv("DEMO_MODE", "").lower() == "true"

    def _mask_key(self, key: str) -> str:
        """脱敏显示 API Key"""
        if not key or len(key) < 10:
            return key
        return key[:8] + "****" + key[-4:]


# 单例
settings_service = SettingsService()
