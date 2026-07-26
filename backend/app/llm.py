"""LLMGateway：全项目唯一的 LLM 出口（单一 OpenAI 兼容通路）。

- 全局唯一实例挂在 FastAPI app.state 上，所有路由共享；
- 管理端修改配置后调用 reload()，下一次请求即用新配置（根治旧版热更新 Bug）；
- 未配置 API Key 时 is_configured 为 False，聊天接口返回配置引导提示。
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.services import settings_service

INTENT_PROMPT = """你是客服系统的意图分类器。根据用户最新消息和对话上下文，判断意图并只输出 JSON。

三种意图：
- "knowledge"：询问产品/服务/政策等需要查知识库回答的问题
- "escalation"：明确表达想要人工客服接待（包括表达对 AI 回答不满、要求"找个人""活人"等语义等价说法）
- "chitchat"：打招呼、闲聊、感谢等无需查资料的对话

只输出如 {"intent": "knowledge"} 的 JSON，不要输出其他内容。"""


class IntentResult(BaseModel):
    intent: str = "knowledge"


class LLMGateway:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.base_url = ""
        self.api_key = ""
        self.chat_model = ""
        self.intent_model = ""
        self.embedding_model = ""
        self.reload()

    def reload(self) -> None:
        cfg = settings_service.get_llm_config()
        self.base_url = cfg["llm_base_url"]
        self.api_key = cfg["llm_api_key"]
        self.chat_model = cfg["llm_chat_model"]
        self.intent_model = cfg["llm_intent_model"] or cfg["llm_chat_model"]
        self.embedding_model = cfg["llm_embedding_model"]
        if self.is_configured:
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self._client = None
        logger.info(f"LLMGateway reloaded: base={self.base_url} chat={self.chat_model}")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.chat_model)

    def _require_client(self) -> AsyncOpenAI:
        if self._client is None:
            raise RuntimeError("LLM 未配置：请在管理端「设置」中填写 API Key")
        return self._client

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """流式对话，逐 token 产出。"""
        stream = await self._require_client().chat.completions.create(
            model=self.chat_model, messages=messages, stream=True, temperature=0.7,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def classify_intent(self, message: str, history: list[dict]) -> IntentResult:
        """LLM 结构化输出做意图判断（替代关键词 if/else）。失败时回退 knowledge。"""
        recent = history[-4:]
        context = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in recent)
        try:
            resp = await self._require_client().chat.completions.create(
                model=self.intent_model,
                messages=[
                    {"role": "system", "content": INTENT_PROMPT},
                    {"role": "user", "content": f"对话上下文：\n{context}\n\n用户最新消息：{message}"},
                ],
                temperature=0,
                max_tokens=32,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            intent = json.loads(raw).get("intent", "knowledge")
            if intent not in ("knowledge", "escalation", "chitchat"):
                intent = "knowledge"
            return IntentResult(intent=intent)
        except Exception as e:  # 意图分类失败不应阻断聊天
            logger.warning(f"意图分类失败，回退 knowledge: {e}")
            return IntentResult(intent="knowledge")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._require_client().embeddings.create(
            model=self.embedding_model, input=texts,
        )
        return [d.embedding for d in resp.data]


# 全局唯一实例（main.py 的 lifespan 中初始化后也可直接 import 使用）
gateway: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    global gateway
    if gateway is None:
        gateway = LLMGateway()
    return gateway
