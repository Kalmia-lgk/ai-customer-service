# ============================================================
# 聊天服务 - 处理多轮对话、LLM 调用、流式输出与知识库集成
# ============================================================
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import AsyncGenerator, Optional

from loguru import logger

from app.core.llm_client import LLMClient
from app.schemas.models import SourceCitation

# RAG 检索器（按需初始化，Demo 模式下为 None）
_retrieval = None


def _get_retrieval():
    """按需获取检索器实例，避免 Demo 模式触发重型依赖导入"""
    global _retrieval
    if _retrieval is None:
        try:
            from app.rag.retrieval import DocumentRetrieval
            _retrieval = DocumentRetrieval()
            logger.info("知识库检索器已加载")
        except Exception as e:
            logger.warning(f"知识库检索器不可用: {e}")
            _retrieval = False  # 标记为已尝试但失败
    return _retrieval if _retrieval is not False else None


# 客服 System Prompt（关键：定义 AI 客服的行为准则）
SYSTEM_PROMPT = """你是一个专业、友好的 AI 智能客服助手。请遵循以下准则：

1. **热情专业**: 用礼貌、温暖的语言回复用户，让用户感受到真诚的服务。
2. **知识驱动**: 优先使用提供的参考资料来回答问题。引用资料时，自然地提及来源。
3. **诚实透明**: 如果参考资料不足以回答问题，如实告知用户，并建议联系人工客服。
4. **结构清晰**: 回答使用分点、加粗标题等方式组织，方便用户阅读。
5. **主动引导**: 在回答末尾主动询问是否还有其他需要帮助的地方。
6. **安全边界**: 不编造信息，不对公司产品做出超出参考资料范围的承诺。

你是用户值得信赖的 AI 助手，请用心服务每一位用户。"""


class SessionStore:
    """
    会话存储（基于内存 + JSON 文件持久化）
    管理所有对话会话的历史记录
    """

    def __init__(self) -> None:
        import os
        self._sessions: dict[str, list[dict]] = {}
        self._meta: dict[str, dict] = {}

    def create_session(self) -> str:
        """创建新会话，返回 session_id"""
        import uuid
        sid = str(uuid.uuid4())
        self._sessions[sid] = []
        self._meta[sid] = {
            "title": "新会话",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
        }
        return sid

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """向会话添加一条消息"""
        if session_id not in self._sessions:
            self.create_session()
        self._sessions[session_id].append({"role": role, "content": content})
        self._meta[session_id]["updated_at"] = datetime.now().isoformat()
        self._meta[session_id]["message_count"] = len(self._sessions[session_id])
        # 用第一条用户消息作为会话标题
        if role == "user" and self._meta[session_id]["title"] == "新会话":
            self._meta[session_id]["title"] = content[:30] + ("..." if len(content) > 30 else "")

    def get_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """获取会话历史（最近的 N 条）"""
        msgs = self._sessions.get(session_id, [])
        return msgs[-limit * 2:]  # 保留最近 N 轮（user + assistant 各一条）

    def get_meta(self, session_id: str) -> Optional[dict]:
        """获取会话元数据"""
        return self._meta.get(session_id)

    def list_sessions(self) -> list[dict]:
        """列出所有会话，按更新时间倒序"""
        result = []
        for sid, meta in self._meta.items():
            result.append({
                "session_id": sid,
                **meta,
            })
        result.sort(key=lambda x: x["updated_at"], reverse=True)
        return result

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._meta[session_id]
            return True
        return False


# 全局会话存储实例
session_store = SessionStore()


class ChatService:
    """
    聊天服务 —— 编排 RAG 检索 + LLM 生成 + 流式输出
    RAG 检索为可选：Demo 模式下自动跳过，直接生成回复
    """

    def __init__(self) -> None:
        self._llm = LLMClient()

    def _build_messages(
        self,
        user_message: str,
        history: list[dict],
        knowledge_context: str,
    ) -> list[dict[str, str]]:
        """
        构建发送给 LLM 的完整消息列表
        结构: system_prompt + knowledge_context + history + current_message
        """
        messages: list[dict[str, str]] = []

        # 1. System Prompt（含知识库上下文）
        system_text = SYSTEM_PROMPT
        if knowledge_context:
            system_text += f"\n\n## 参考资料（请优先使用以下信息回答问题）\n\n{knowledge_context}"
        messages.append({"role": "system", "content": system_text})

        # 2. 历史对话
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 3. 当前用户消息
        messages.append({"role": "user", "content": user_message})

        return messages

    async def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        核心流式聊天方法

        处理流程:
        1. 会话管理（创建/续接）
        2. 知识库检索
        3. 构建 Prompt
        4. LLM 流式生成
        5. 保存对话历史

        Yields:
            dict: 流式数据块
                - {"type": "session", "session_id": "..."}
                - {"type": "token", "content": "..."}
                - {"type": "sources", "sources": [...]}
                - {"type": "thinking", "content": "正在检索知识库..."}
                - {"type": "done"}
                - {"type": "error", "content": "..."}
        """
        # 1. 会话管理
        if not session_id or not session_store.get_meta(session_id):
            session_id = session_store.create_session()
        yield {"type": "session", "session_id": session_id}

        # 2. 知识库检索（可选，Demo 模式自动跳过）
        knowledge_context = ""
        sources: list[dict] = []
        retrieval = _get_retrieval()
        if retrieval and retrieval.is_available:
            yield {"type": "thinking", "content": "🔍 正在检索知识库..."}
            knowledge_context, sources_raw = retrieval.build_context(message)
            sources = sources_raw
            if sources:
                yield {
                    "type": "sources",
                    "sources": [
                        SourceCitation(
                            document_name=s["document_name"],
                            snippet=s["snippet"],
                            score=s["score"],
                        ).model_dump()
                        for s in sources
                    ],
                }
        else:
            logger.debug("知识库未就绪，跳过检索步骤")

        # 3. 构建消息
        history = session_store.get_history(session_id)
        messages = self._build_messages(message, history, knowledge_context)

        # 4. 保存用户消息
        session_store.add_message(session_id, "user", message)

        # 5. LLM 流式生成
        full_response = ""
        try:
            async for token in self._llm.chat_stream(messages):
                full_response += token
                yield {"type": "token", "content": token}

            # 6. 保存 AI 回复
            session_store.add_message(session_id, "assistant", full_response)

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            yield {"type": "error", "content": f"AI 回复生成失败: {str(e)}"}
            # 仍然保存错误信息
            session_store.add_message(session_id, "assistant", full_response or "[回复生成失败]")

        # 7. 完成标记
        yield {"type": "done"}

    def get_session_list(self) -> list[dict]:
        """获取所有会话列表"""
        return session_store.list_sessions()

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取单个会话信息"""
        meta = session_store.get_meta(session_id)
        if meta:
            history = session_store.get_history(session_id, limit=1000)  # 获取全部历史
            return {"session_id": session_id, **meta, "messages": history}
        return None

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        return session_store.delete_session(session_id)

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return session_store.get_meta(session_id) is not None
