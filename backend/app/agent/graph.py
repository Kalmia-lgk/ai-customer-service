"""LangGraph 状态图：classify → retrieve / escalate / chitchat → generate。

与旧版"死代码 Agent"的三个本质区别：
1. /api/chat 的处理链路就是这张图，不存在第二条聊天路径；
2. 意图判断由 LLM 结构化输出完成（llm.classify_intent），不是关键词 if/else；
3. 生成在图内流式进行：节点内用 get_stream_writer 把 token 与 agent_step
   事件实时推出去，路由层原样转发为 SSE。
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from sqlmodel import Session

from app.agent import prompts
from app.db import engine
from app.llm import get_gateway
from app.rag import pipeline
from app.services import ticket_service


class AgentState(TypedDict, total=False):
    user_message: str
    history: list[dict]     # 最近几轮 [{role, content}]
    session_id: str
    visitor_id: str
    intent: str             # knowledge / escalation / chitchat
    context: str            # 检索到的资料拼接文本
    sources: list[dict]     # 引用（给前端展示并随消息落库）
    ticket_id: str | None


STEP_LABELS = {
    "classify": "识别意图",
    "retrieve": "检索知识库",
    "escalate": "创建人工工单",
    "generate": "生成回答",
}


def _emit_step(step: str, detail: str = "") -> None:
    get_stream_writer()(
        {"event": "agent_step", "step": step, "label": STEP_LABELS[step], "detail": detail}
    )


async def classify(state: AgentState) -> dict:
    _emit_step("classify")
    result = await get_gateway().classify_intent(state["user_message"], state["history"])
    return {"intent": result.intent}


async def retrieve(state: AgentState) -> dict:
    _emit_step("retrieve")
    hits = await pipeline.search(state["user_message"])
    sources = [
        {"filename": h["filename"], "snippet": h["text"][:160], "score": h["score"]}
        for h in hits
    ]
    context = "\n\n".join(
        f"【资料{i + 1} · {h['filename']}】\n{h['text']}" for i, h in enumerate(hits)
    )
    get_stream_writer()({"event": "sources", "sources": sources})
    return {"context": context, "sources": sources}


async def escalate(state: AgentState) -> dict:
    _emit_step("escalate")
    # 图节点独立开库会话（不复用请求级依赖，节点可能在任意时刻执行）
    with Session(engine) as db:
        ticket, created = await ticket_service.create_ticket(
            db, state["session_id"], state["visitor_id"], state["user_message"]
        )
    get_stream_writer()(
        {"event": "ticket", "ticket_id": ticket.id, "created": created}
    )
    return {"ticket_id": ticket.id}


async def generate(state: AgentState) -> dict:
    _emit_step("generate")
    intent = state.get("intent", "knowledge")

    if intent == "escalation":
        note = "已为其创建人工工单" if state.get("ticket_id") else "尝试创建工单时出现问题"
        system = prompts.ESCALATION_SYSTEM.format(ticket_note=note)
    elif intent == "chitchat":
        system = prompts.CHITCHAT_SYSTEM
    elif state.get("context"):
        system = prompts.KNOWLEDGE_SYSTEM.format(context=state["context"])
    else:
        system = prompts.NO_CONTEXT_SYSTEM

    messages = (
        [{"role": "system", "content": system}]
        + state["history"]
        + [{"role": "user", "content": state["user_message"]}]
    )
    writer = get_stream_writer()
    async for token in get_gateway().chat_stream(messages):
        writer({"event": "token", "content": token})
    return {}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("classify", classify)
    g.add_node("retrieve", retrieve)
    g.add_node("escalate", escalate)
    g.add_node("generate", generate)
    g.add_edge(START, "classify")
    g.add_conditional_edges(
        "classify",
        lambda s: s["intent"],
        {"knowledge": "retrieve", "escalation": "escalate", "chitchat": "generate"},
    )
    g.add_edge("retrieve", "generate")
    g.add_edge("escalate", "generate")  # 建单后仍生成一句安抚话术
    g.add_edge("generate", END)
    return g.compile()


graph = build_graph()
