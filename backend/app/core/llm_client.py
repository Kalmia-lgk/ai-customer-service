# ============================================================
# LLM 客户端工厂 - 统一封装不同提供商的 LLM 调用
# ============================================================
from __future__ import annotations

from typing import AsyncGenerator

from loguru import logger

from app.core.config import settings


class LLMClient:
    """
    通用 LLM 客户端封装
    支持 OpenAI / Anthropic / Groq 三种后端，提供统一的流式接口
    当无法连接真实 LLM 时自动降级为 Demo 模式
    """

    def __init__(self) -> None:
        self._load_config()
        if self._demo_mode:
            logger.warning("Demo mode active - using simulated replies")
        else:
            logger.info(f"LLM client: provider={self.provider}, model={self.model}")

    def _load_config(self) -> None:
        """加载配置：运行时 settings.json > .env"""
        try:
            from app.services.settings_service import settings_service
            self.provider = settings_service.get_active_provider()
            self.model = settings_service.get_active_model()
            self.api_key = settings_service.get_active_api_key()
        except Exception:
            self.provider = settings.LLM_PROVIDER
            self.model = settings.get_llm_model()
            self.api_key = settings.get_llm_api_key()
        self._demo_mode = self._detect_demo_mode()

    def _detect_demo_mode(self) -> bool:
        """检测是否应启用 Demo 模式"""
        import os
        if os.getenv("DEMO_MODE", "").lower() == "true":
            return True
        if "sk-your-" in self.api_key or "gsk_your-" in self.api_key or "sk-ant-your-" in self.api_key:
            return True
        if not self.api_key or len(self.api_key) < 10:
            return True
        return False

    def reload_config(self) -> None:
        """重新加载配置（API Key 更新后调用）"""
        old_demo = self._demo_mode
        self._load_config()
        if old_demo != self._demo_mode:
            logger.info(f"LLM mode switched: demo={self._demo_mode}, provider={self.provider}")

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天接口
        根据配置的 provider 调用对应的 LLM API，逐 token 返回内容
        """
        # Demo 模式：模拟回复
        if self._demo_mode:
            async for chunk in self._stream_demo(messages):
                yield chunk
            return

        match self.provider:
            case "openai":
                async for chunk in self._stream_openai(messages, temperature, max_tokens):
                    yield chunk
            case "anthropic":
                async for chunk in self._stream_anthropic(messages, temperature, max_tokens):
                    yield chunk
            case "groq":
                async for chunk in self._stream_groq(messages, temperature, max_tokens):
                    yield chunk
            case _:
                raise ValueError(f"不支持的 LLM 提供商: {self.provider}")

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """非流式聊天，返回完整内容"""
        chunks: list[str] = []
        async for chunk in self.chat_stream(messages, temperature, max_tokens):
            chunks.append(chunk)
        return "".join(chunks)

    # ========== Demo 模拟模式 ==========

    async def _stream_demo(
        self, messages: list[dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        Demo 模式 —— 模拟真实的 AI 客服回复
        用于无需 API Key 即可演示完整 UI 效果
        """
        import asyncio
        import os

        # 获取用户最后一条消息
        user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_msg = m["content"].strip().lower()
                break

        # 根据用户输入生成对应的模拟回复
        if any(w in user_msg for w in ["你好", "hello", "hi", "嗨", "在吗"]):
            demo_text = (
                "您好！👋 欢迎使用 **AI 智能客服系统**，很高兴为您服务！\n\n"
                "我是您的专属 AI 客服助手，可以帮您：\n\n"
                "- 📚 **知识库问答**：上传企业文档后，我可以基于文档内容精准回答\n"
                "- 🔍 **智能检索**：快速从海量资料中找到您需要的信息\n"
                "- 💬 **多轮对话**：支持上下文理解，交流更自然流畅\n"
                "- 🎧 **人工转接**：复杂问题可一键转接人工客服\n\n"
                "请问有什么可以帮您的？您可以直接提问，或先上传知识库文件哦～"
            )
        elif "demo" in user_msg or "演示" in user_msg or "测试" in user_msg:
            demo_text = (
                "🎮 **Demo 模式说明**\n\n"
                "您当前看到的是 **无 API Key 的演示模式**。\n\n"
                "在此模式下:\n"
                "- ✅ 前端 UI 完全可用\n"
                "- ✅ 流式输出效果正常展示\n"
                "- ✅ 文件上传、知识库管理功能正常\n"
                "- ⚠️ AI 回复为预设演示内容\n\n"
                "**接入真实 AI**:\n"
                "1. 编辑 `.env` 文件\n"
                "2. 填入 `OPENAI_API_KEY`（或其他支持的 LLM Key）\n"
                "3. 重启服务即可\n\n"
                "支持的 LLM 提供商: OpenAI / Anthropic / Groq 🚀"
            )
        elif any(w in user_msg for w in ["价格", "费用", "多少钱", "收费"]):
            demo_text = (
                "关于价格方面，我们的产品提供灵活的定价方案：\n\n"
                "| 方案 | 价格 | 适合场景 |\n"
                "|------|------|----------|\n"
                "| **基础版** | ¥99/月 | 个人使用，基础功能 |\n"
                "| **专业版** | ¥299/月 | 小型团队，高级功能 |\n"
                "| **企业版** | ¥999/月 | 大型企业，定制化服务 |\n\n"
                "> 💡 所有方案均支持 **7 天免费试用**，满意后再付费！\n\n"
                "如果您需要更详细的报价信息，建议联系我们的销售团队获取专属方案。需要我帮您转接吗？"
            )
        elif any(w in user_msg for w in ["退款", "退货", "退钱"]):
            demo_text = (
                "关于退款问题，我理解您的心情。让我为您说明退款流程：\n\n"
                "**退款条件**：\n"
                "1. 购买后 **7 天内** 可申请无理由退款\n"
                "2. 产品存在 **质量问题** 可随时申请\n\n"
                "**退款流程**：\n"
                "1. 在「我的订单」中找到对应订单\n"
                "2. 点击「申请退款」并填写原因\n"
                "3. 我们会在 **1-3 个工作日** 内审核处理\n"
                "4. 审核通过后，款项原路退回\n\n"
                "如果您需要紧急处理，我可以帮您转接人工客服。请问需要吗？"
            )
        elif any(w in user_msg for w in ["人工", "客服", "转接"]):
            demo_text = (
                "🔔 **已收到您的转人工请求**\n\n"
                "我们将为您转接人工客服，请稍等片刻...\n\n"
                "⏰ 预计等待时间: **2-5 分钟**\n"
                "📞 您也可以直接拨打客服热线: **400-XXX-XXXX**\n\n"
                "*在此期间，您可以继续向我提问，我会尽力为您解答。*"
            )
        else:
            demo_text = (
                "感谢您的提问！让我基于知识库为您查找相关信息...\n\n"
                "根据现有资料，这是一个很好的问题。以下是我的分析：\n\n"
                "**核心要点**：\n"
                "1. 我们的产品在设计上充分考虑了用户体验和易用性\n"
                "2. 采用了业界领先的技术架构，确保稳定性和性能\n"
                "3. 提供了完善的售后服务和技术支持体系\n\n"
                "> 💡 **提示**：为了给您更精准的回答，建议上传相关的产品文档或 FAQ 文件到知识库，"
                "这样我能基于实际资料为您提供专业解答。\n\n"
                "如果您需要更详细的信息或有其他问题，请随时告诉我。我也可以为您转接人工客服获取更专业的帮助。"
            )

        # 模拟流式输出 —— 逐字符发送，营造真实感觉
        chunk_size = 3  # 每次发送的字符数
        for i in range(0, len(demo_text), chunk_size):
            yield demo_text[i:i + chunk_size]
            await asyncio.sleep(0.02)  # 模拟网络延迟

    # ========== OpenAI 流式实现 ==========

    async def _stream_openai(
        self, messages: list[dict[str, str]], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """通过 OpenAI SDK 实现流式调用"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=settings.OPENAI_BASE_URL,
            )
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"OpenAI 流式调用失败: {e}")
            yield f"\n\n❌ AI 回复出错: {str(e)}"

    # ========== Anthropic 流式实现 ==========

    async def _stream_anthropic(
        self, messages: list[dict[str, str]], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """通过 Anthropic SDK 实现流式调用"""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)

            # Anthropic 需要 system 消息单独传递
            system_msg = ""
            user_messages: list[dict[str, str]] = []
            for m in messages:
                if m["role"] == "system":
                    system_msg += m["content"] + "\n"
                else:
                    user_messages.append(m)

            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_msg.strip() or None,
                messages=user_messages,  # type: ignore[arg-type]
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic 流式调用失败: {e}")
            yield f"\n\n❌ AI 回复出错: {str(e)}"

    # ========== Groq 流式实现 ==========

    async def _stream_groq(
        self, messages: list[dict[str, str]], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """通过 Groq SDK 实现流式调用（兼容 OpenAI 接口）"""
        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=self.api_key)
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as e:
            logger.error(f"Groq 流式调用失败: {e}")
            yield f"\n\n❌ AI 回复出错: {str(e)}"


# 单例 LLM 客户端
llm_client = LLMClient()
