"""端到端冒烟测试：对运行中的服务验证 RAG / Agent 三分支 / 工单全流程。

用法：先启动服务，再在项目根目录执行 python scripts/smoke_test.py
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

BASE = "http://127.0.0.1:8000"
VISITOR = f"test-{uuid.uuid4().hex[:12]}"


def make_token() -> str:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import User
    from app.security import create_token

    with Session(engine) as db:
        user = db.exec(select(User).where(User.role == "super_admin")).first()
        assert user, "无超管用户"
        return create_token(user)


def sse_chat(message: str, session_id: str | None = None) -> dict:
    """发送一条聊天消息，收集全部 SSE 事件。"""
    resp = requests.post(
        f"{BASE}/api/chat",
        json={"message": message, "visitor_id": VISITOR, "session_id": session_id},
        stream=True, timeout=120,
    )
    resp.raise_for_status()
    result = {"steps": [], "tokens": [], "sources": [], "ticket": None, "session_id": None}
    event = None
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None or raw == "":
            continue
        if raw.startswith("event:"):
            event = raw.split(":", 1)[1].strip()
        elif raw.startswith("data:"):
            data = json.loads(raw.split(":", 1)[1].strip())
            if event == "session":
                result["session_id"] = data["session_id"]
            elif event == "agent_step":
                result["steps"].append(data["step"])
            elif event == "sources":
                result["sources"] = data["sources"]
            elif event == "ticket":
                result["ticket"] = data
            elif event == "error":
                result["error"] = data
            elif event is None:
                result["tokens"].append(data.get("content", ""))
            event = None
    result["answer"] = "".join(result["tokens"])
    return result


def main() -> None:
    token = make_token()
    headers = {"Authorization": f"Bearer {token}"}
    passed, failed = [], []

    def check(name: str, cond: bool, detail: str = ""):
        (passed if cond else failed).append(name)
        mark = "PASS" if cond else "FAIL"
        print(f"[{mark}] {name} {detail}")

    # 1. 上传知识库文档
    doc_text = (
        "产品退款政策\n\n本产品支持 7 天无理由退款。购买后 7 天内，联系客服提供订单号即可申请，"
        "退款将在 3 个工作日内原路退回。超过 7 天但在 30 天内，若产品存在质量问题，"
        "凭检测报告可申请全额退款。\n\n会员服务\n\n年费会员可享受专属客服通道和 9 折续费优惠。"
    )
    tmp = PROJECT_ROOT / "scripts" / "_test_policy.txt"
    tmp.write_text(doc_text, encoding="utf-8")
    with open(tmp, "rb") as f:
        r = requests.post(
            f"{BASE}/api/documents/upload", headers=headers,
            files={"file": ("测试退款政策.txt", f, "text/plain")}, timeout=120,
        )
    doc = r.json()
    check("文档上传入库", r.ok and doc.get("status") == "ready", f"chunks={doc.get('chunk_count')}")
    doc_id = doc.get("id")

    # 2. knowledge 分支
    r1 = sse_chat("你们支持退款吗？")
    check("knowledge 走 retrieve 分支", r1["steps"][:2] == ["classify", "retrieve"], str(r1["steps"]))
    check("knowledge 有引用", len(r1["sources"]) > 0, f"{len(r1['sources'])} 条")
    check("knowledge 回答提到退款", "退款" in r1["answer"], r1["answer"][:60].replace("\n", " "))
    session_id = r1["session_id"]

    # 3. escalation 分支（不含"人工"等关键词，考验 LLM 语义判断）
    r2 = sse_chat("说了半天也没解决，给我个活人来处理！", session_id)
    check("escalation 走 escalate 分支", "escalate" in r2["steps"], str(r2["steps"]))
    check("escalation 自动建工单", bool(r2["ticket"] and r2["ticket"].get("ticket_id")), str(r2["ticket"]))
    ticket_id = (r2["ticket"] or {}).get("ticket_id")

    # 4. chitchat 分支
    r3 = sse_chat("你好呀")
    check("chitchat 不做检索", r3["steps"] == ["classify", "generate"], str(r3["steps"]))

    # 5. 工单流转：接管 → 回复 → 解决
    if ticket_id:
        r = requests.post(f"{BASE}/api/tickets/{ticket_id}/claim", headers=headers, timeout=30)
        check("工单接管", r.ok and r.json()["status"] == "in_progress")
        r = requests.post(f"{BASE}/api/tickets/{ticket_id}/reply", headers=headers,
                          json={"content": "您好，我是人工客服，请问有什么可以帮您？"}, timeout=30)
        check("客服回复", r.ok)
        r = requests.post(f"{BASE}/api/customer/tickets/{ticket_id}/reply",
                          json={"visitor_id": VISITOR, "content": "我要申请退款"}, timeout=30)
        check("访客回复", r.ok)
        r = requests.get(f"{BASE}/api/customer/tickets/{ticket_id}", params={"visitor_id": VISITOR}, timeout=30)
        msgs = r.json()["messages"]
        check("工单消息落库", len(msgs) >= 3, f"{len(msgs)} 条")
        r = requests.post(f"{BASE}/api/tickets/{ticket_id}/resolve", headers=headers, timeout=30)
        check("工单解决", r.ok and r.json()["status"] == "resolved")

    # 6. 会话隔离
    r = requests.get(f"{BASE}/api/sessions", params={"visitor_id": VISITOR}, timeout=30)
    check("本访客能看到会话", r.ok and len(r.json()) >= 1, f"{len(r.json())} 个")
    r = requests.get(f"{BASE}/api/sessions", params={"visitor_id": "other-visitor-xx"}, timeout=30)
    check("其他访客看不到会话", r.ok and len(r.json()) == 0)
    r = requests.get(f"{BASE}/api/sessions/{session_id}/messages",
                     params={"visitor_id": "other-visitor-xx"}, timeout=30)
    check("跨访客读消息被拒", r.status_code == 404)

    # 7. 历史消息持久化（含 sources 快照）
    r = requests.get(f"{BASE}/api/sessions/{session_id}/messages", params={"visitor_id": VISITOR}, timeout=30)
    msgs = r.json()
    assistant_with_sources = [m for m in msgs if m["role"] == "assistant" and m["sources"]]
    check("消息与引用快照落库", len(msgs) >= 4 and len(assistant_with_sources) >= 1, f"{len(msgs)} 条消息")

    # 8. 清理测试文档
    if doc_id:
        r = requests.delete(f"{BASE}/api/documents/{doc_id}", headers=headers, timeout=30)
        check("删除文档", r.ok)
    tmp.unlink(missing_ok=True)

    print(f"\n结果: {len(passed)} 通过, {len(failed)} 失败")
    if failed:
        print("失败项:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
