# ============================================================
# 通用 Embedding 客户端 - 兼容任何 OpenAI 风格接口
# (OpenAI 官方 / 硅基流动 SiliconFlow / 其他兼容服务)
# ============================================================
from __future__ import annotations

from typing import Optional

from loguru import logger

from app.core.config import settings


class EmbeddingClient:
    """
    基于 openai SDK 的轻量 Embedding 封装
    配置来源: settings.get_embedding_config()
    （优先级: EMBEDDING_* 显式配置 > 硅基流动 > OpenAI）
    """

    def __init__(self) -> None:
        self._client = None
        self._model = ""

        config = settings.get_embedding_config()
        if config is None:
            logger.warning("⚠️ 未配置任何可用的 Embedding API Key，RAG 检索不可用")
            return

        try:
            from openai import OpenAI
        except ImportError as e:
            logger.warning(f"⚠️ openai SDK 未安装 ({e})，RAG 检索不可用")
            return

        self._client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            timeout=30.0,
        )
        self._model = config["model"]
        logger.info(f"✅ Embedding 就绪: model={self._model}, base_url={config['base_url']}")

    @property
    def is_available(self) -> bool:
        return self._client is not None

    @property
    def model(self) -> str:
        return self._model

    def embed(self, text: str) -> Optional[list[float]]:
        """获取单条文本的向量，失败返回 None"""
        if self._client is None:
            return None
        resp = self._client.embeddings.create(model=self._model, input=text)
        return resp.data[0].embedding

    def embed_batch(self, texts: list[str]) -> Optional[list[list[float]]]:
        """批量获取向量（一次 API 调用），失败抛出异常"""
        if self._client is None:
            return None
        resp = self._client.embeddings.create(model=self._model, input=texts)
        # API 保证顺序与输入一致
        return [item.embedding for item in resp.data]

    # 与 llama-index Embedding 接口对齐的别名
    def get_text_embedding(self, text: str) -> Optional[list[float]]:
        return self.embed(text)

    def get_query_embedding(self, query: str) -> Optional[list[float]]:
        return self.embed(query)
