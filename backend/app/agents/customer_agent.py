# ============================================================
# LangGraph 智能客服 Agent
# 使用状态图编排: 意图识别 → 知识检索 → 回复生成 → 人工转接
# ============================================================
from __future__ import annotations

import json
from typing import Literal, Optional

from loguru import logger

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator


# ==================== Agent 状态定义 ====================

class AgentState(TypedDict):
    """Agent 工作流的状态定义"""
    # 用户原始输入
    user_message: str
    # 对话历史（最近几轮）
    history: Annotated[list[dict], operator.add]
    # 识别的意图类型
    intent: str
    # 知识库检索结果（纯文本上下文）
    knowledge_context: str
    # 知识来源引用列表
    sources: list[dict]
    # 是否需要转人工
    should_escalate: bool
    # 转人工原因
    escalate_reason: str
    # 生成的最终回复
    final_response: str
    # 当前步骤
    current_step: str


# ==================== 意图分类 ====================

# 预定义意图类型
IntentType = Literal[
    "greeting",           # 问候寒暄
    "knowledge_query",    # 需要知识库回答的问题
    "complaint",          # 投诉建议
    "escalation",         # 明确要求转人工
    "general_chat",       # 一般闲聊
]

# 转人工触发关键词
ESCALATION_KEYWORDS = [
    "转人工", "人工客服", "人工服务", "找人工", "真人",
    "我要投诉", "投诉你们", "找经理", "找领导", "客服电话",
]


def classify_intent(state: AgentState) -> AgentState:
    """
    意图分类节点
    使用关键词匹配 + 规则进行意图分类
    """
    message = state["user_message"].strip().lower()
    logger.info(f"[Agent] 分类意图: '{message[:50]}...'")

    # 规则1: 转人工关键词
    for kw in ESCALATION_KEYWORDS:
        if kw in message:
            state["intent"] = "escalation"
            state["current_step"] = "intent_classified"
            logger.info(f"[Agent] 意图 → escalation (关键词: {kw})")
            return state

    # 规则2: 问候语
    greeting_words = ["你好", "您好", "hi", "hello", "嗨", "在吗", "早上好", "下午好", "晚上好"]
    if any(message == w or message.startswith(w) for w in greeting_words) and len(message) < 15:
        state["intent"] = "greeting"
        state["current_step"] = "intent_classified"
        logger.info("[Agent] 意图 → greeting")
        return state

    # 规则3: 投诉类
    complaint_words = ["投诉", "不满", "太差", "失望", "退款", "赔偿", "举报"]
    if any(w in message for w in complaint_words):
        state["intent"] = "complaint"
        state["current_step"] = "intent_classified"
        logger.info("[Agent] 意图 → complaint")
        return state

    # 默认: 知识库查询
    state["intent"] = "knowledge_query"
    state["current_step"] = "intent_classified"
    logger.info("[Agent] 意图 → knowledge_query (默认)")
    return state


# ==================== 知识检索节点 ====================

def retrieve_knowledge(state: AgentState) -> AgentState:
    """
    知识检索节点
    从向量数据库中检索与用户问题相关的文档片段
    """
    logger.info(f"[Agent] 开始知识检索: '{state['user_message'][:50]}...'")

    try:
        from app.rag.retrieval import DocumentRetrieval
        retrieval = DocumentRetrieval()
        context, sources = retrieval.build_context(state["user_message"])

        state["knowledge_context"] = context
        state["sources"] = sources
        state["current_step"] = "knowledge_retrieved"

        logger.info(f"[Agent] 检索完成: {len(sources)} 条结果")
    except Exception as e:
        logger.error(f"[Agent] 检索失败: {e}")
        state["knowledge_context"] = ""
        state["sources"] = []

    return state


# ==================== 转人工处理 ====================

def handle_escalation(state: AgentState) -> AgentState:
    """
    转人工节点
    标记需要转接并提供模拟转接信息
    """
    logger.info(f"[Agent] 触发转人工")
    state["should_escalate"] = True
    state["escalate_reason"] = "用户请求转人工" if state["intent"] == "escalation" else "系统判定需人工介入"
    state["current_step"] = "escalated"
    state["final_response"] = (
        "🔔 **已收到您的转人工请求**\n\n"
        "我们将为您转接人工客服，请稍等...\n\n"
        "⏰ 预计等待时间: **2-5 分钟**\n"
        "📞 您也可以直接拨打客服热线: **400-XXX-XXXX**\n\n"
        "*在此期间，您可以继续向我提问，我会尽力为您解答。*"
    )
    return state


# ==================== 路由决策 ====================

def route_after_classification(state: AgentState) -> str:
    """
    意图分类后的路由
    根据意图类型决定下一步执行哪个节点
    """
    intent = state["intent"]
    if intent == "escalation":
        return "escalate"
    elif intent == "greeting" or intent == "general_chat":
        return "generate_direct"
    else:
        # knowledge_query, complaint → 先检索再生成
        return "retrieve"


# ==================== 构建 LangGraph 工作流 ====================

def build_customer_service_graph() -> StateGraph:
    """
    构建智能客服 Agent 的有向图
    节点: classify_intent → route → [retrieve / escalate / generate_direct]
                                   ↓
                               generate → END
    """
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("retrieve", retrieve_knowledge)
    workflow.add_node("handle_escalation", handle_escalation)

    # 设置入口
    workflow.set_entry_point("classify_intent")

    # 添加条件边: 意图分类后路由
    workflow.add_conditional_edges(
        "classify_intent",
        route_after_classification,
        {
            "retrieve": "retrieve",       # 知识查询: 先检索
            "escalate": "handle_escalation",  # 转人工
            "generate_direct": END,       # 问候/闲聊: 直接结束（在服务层处理）
        },
    )

    # 检索完成后也结束（生成由服务层的 LLM 完成）
    workflow.add_edge("retrieve", END)
    workflow.add_edge("handle_escalation", END)

    return workflow.compile()


# ==================== Agent 封装类 ====================

class CustomerAgent:
    """
    智能客服 Agent 封装
    对外提供统一的 process() 接口
    """

    def __init__(self) -> None:
        self._graph = build_customer_service_graph()
        logger.info("[Agent] LangGraph 工作流初始化完成")

    def process(self, user_message: str, history: Optional[list[dict]] = None) -> AgentState:
        """
        处理用户消息，返回 Agent 状态

        Args:
            user_message: 用户输入文本
            history: 历史对话记录

        Returns:
            AgentState: 包含意图、检索结果、是否需要转人工等信息
        """
        initial_state: AgentState = {
            "user_message": user_message,
            "history": history or [],
            "intent": "",
            "knowledge_context": "",
            "sources": [],
            "should_escalate": False,
            "escalate_reason": "",
            "final_response": "",
            "current_step": "start",
        }

        try:
            result = self._graph.invoke(initial_state)
            logger.info(
                f"[Agent] 处理完成: intent={result.get('intent')}, "
                f"escalate={result.get('should_escalate')}, "
                f"sources={len(result.get('sources', []))}"
            )
            return result  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"[Agent] 处理出错: {e}")
            # 返回降级结果
            return {
                **initial_state,
                "intent": "knowledge_query",
                "should_escalate": False,
                "current_step": "error_fallback",
            }
