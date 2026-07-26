// ============================================================
// API 封装：fetch + SSE 流式解析 + WebSocket（客户端）
// ============================================================

const VISITOR_KEY = "aicc_visitor_id";

export function visitorId() {
  let id = localStorage.getItem(VISITOR_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(VISITOR_KEY, id);
  }
  return id;
}

async function request(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    let detail = `请求失败 (${resp.status})`;
    try {
      const d = (await resp.json()).detail;
      if (typeof d === "string") detail = d;
      else if (Array.isArray(d)) detail = d.map((x) => x.msg || JSON.stringify(x)).join("；");
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return resp.json();
}

// ---------- 会话 ----------

export const listSessions = () =>
  request(`/api/sessions?visitor_id=${visitorId()}`);

export const listMessages = (sessionId) =>
  request(`/api/sessions/${sessionId}/messages?visitor_id=${visitorId()}`);

export const deleteSession = (sessionId) =>
  request(`/api/sessions/${sessionId}?visitor_id=${visitorId()}`, { method: "DELETE" });

// ---------- 聊天（SSE 流式） ----------

/**
 * 发送消息并逐事件回调。
 * handlers: { onSession, onStep, onSources, onTicket, onToken, onError, onDone }
 */
export async function chatStream(message, sessionId, handlers) {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, visitor_id: visitorId() }),
  });
  if (!resp.ok || !resp.body) throw new Error(`聊天请求失败 (${resp.status})`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (event, data) => {
    switch (event) {
      case "session": handlers.onSession?.(data.session_id); break;
      case "agent_step": handlers.onStep?.(data); break;
      case "sources": handlers.onSources?.(data.sources); break;
      case "ticket": handlers.onTicket?.(data); break;
      case "error": handlers.onError?.(data.message); break;
      case "done": handlers.onDone?.(); break;
      default: if (data.content) handlers.onToken?.(data.content);
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE 事件以空行分隔
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop();
    for (const block of blocks) {
      let event = null, data = null;
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data = JSON.parse(line.slice(5).trim());
      }
      if (data !== null) dispatch(event, data);
    }
  }
}

// ---------- 工单 ----------

export const escalate = (sessionId, reason = "") =>
  request("/api/customer/escalate", {
    method: "POST",
    body: JSON.stringify({ visitor_id: visitorId(), session_id: sessionId, reason }),
  });

export const activeTicket = (sessionId) =>
  request(`/api/customer/active-ticket?visitor_id=${visitorId()}&session_id=${sessionId}`);

export const ticketDetail = (ticketId) =>
  request(`/api/customer/tickets/${ticketId}?visitor_id=${visitorId()}`);

export const ticketReply = (ticketId, content) =>
  request(`/api/customer/tickets/${ticketId}/reply`, {
    method: "POST",
    body: JSON.stringify({ visitor_id: visitorId(), content }),
  });

/** 连接工单 WS（只收推送；发消息走 REST）。返回 close 函数。 */
export function connectTicketWS(ticketId, onEvent) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(
    `${proto}://${location.host}/ws/customer/${ticketId}?visitor_id=${visitorId()}`
  );
  ws.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch { /* ignore */ }
  };
  const timer = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) ws.send("ping");
  }, 25000);
  ws.onclose = () => clearInterval(timer);
  return () => { clearInterval(timer); ws.close(); };
}
