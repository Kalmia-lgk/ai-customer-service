// ============================================================
// 客户端入口：主题 / 布局 / 发送流程（AI 模式 ↔ 人工工单模式）
// ============================================================
import * as api from "./api.js";
import * as chat from "./chat.js";
import * as sessions from "./sessions.js";

// ---------- 小工具 ----------

function toast(message, isError = false) {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " toast-error" : "");
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

// ---------- 主题 ----------

document.getElementById("btn-theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("aicc_theme", next);
});

// ---------- 侧栏收起/展开 ----------

const sidebar = document.getElementById("sidebar");
const btnExpand = document.getElementById("btn-expand");
document.getElementById("btn-collapse").addEventListener("click", () => {
  sidebar.classList.add("collapsed");
  btnExpand.hidden = false;
});
btnExpand.addEventListener("click", () => {
  sidebar.classList.remove("collapsed");
  btnExpand.hidden = true;
});

// ---------- 状态 ----------

const input = document.getElementById("input");
const btnSend = document.getElementById("btn-send");
const banner = document.getElementById("ticket-banner");
const bannerText = document.getElementById("ticket-status-text");
const btnBackAI = document.getElementById("btn-back-ai");

let sending = false;
let ticket = null;      // 当前工单 {id, status}
let closeWS = null;     // 工单 WS 关闭函数

// ---------- 人工工单模式 ----------

const BANNER_TEXT = {
  waiting: "已提交人工工单，客服接入后将在此对话",
  in_progress: "人工客服已接入，当前由人工为您服务",
  resolved: "工单已解决，感谢您的耐心等待",
};

function updateBanner() {
  if (!ticket) { banner.hidden = true; return; }
  banner.hidden = false;
  banner.className = ticket.status === "in_progress" ? "human"
    : ticket.status === "resolved" ? "resolved" : "";
  bannerText.className = "dot " + (
    ticket.status === "in_progress" ? "dot-accent"
    : ticket.status === "resolved" ? "dot-success" : "dot-warning");
  bannerText.textContent = BANNER_TEXT[ticket.status] || ticket.status;
  btnBackAI.hidden = ticket.status !== "resolved";
  input.placeholder = ticket.status === "resolved" || !ticket
    ? "输入你的问题，Enter 发送，Shift+Enter 换行"
    : "人工客服对话中，输入消息…";
}

function exitTicketMode() {
  closeWS?.();
  closeWS = null;
  ticket = null;
  updateBanner();
}

btnBackAI.addEventListener("click", exitTicketMode);

function handleTicketEvent(evt) {
  if (evt.type === "ticket_message") {
    const m = evt.message;
    if (m.sender === "agent") chat.addHumanMessage(m.sender_name, m.content);
    else if (m.sender === "system") chat.addSystemMessage(m.content);
    // sender === customer 的回显跳过（本端发送时已本地渲染）
  } else if (evt.type === "ticket_update" && evt.ticket?.id === ticket?.id) {
    ticket.status = evt.ticket.status;
    updateBanner();
    if (ticket.status === "resolved") { closeWS?.(); closeWS = null; }
  }
}

async function enterTicketMode(t, { renderHistory = false } = {}) {
  exitTicketMode();
  ticket = { id: t.id, status: t.status };
  if (renderHistory) {
    try {
      const detail = await api.ticketDetail(t.id);
      for (const m of detail.messages) {
        if (m.sender === "agent") chat.addHumanMessage(m.sender_name, m.content);
        else if (m.sender === "system") chat.addSystemMessage(m.content);
        else chat.addUserMessage(m.content);
      }
      ticket.status = detail.ticket.status;
    } catch { /* ignore */ }
  }
  if (ticket.status !== "resolved") {
    closeWS = api.connectTicketWS(ticket.id, handleTicketEvent);
  }
  updateBanner();
  chat.scrollToBottom(true);
}

// ---------- 转人工按钮 ----------

document.getElementById("btn-escalate").addEventListener("click", async () => {
  const sid = sessions.currentSessionId();
  if (!sid) { toast("请先发送一条消息，再申请转人工"); return; }
  if (ticket && ticket.status !== "resolved") { toast("已在人工服务流程中"); return; }
  try {
    const { ticket: t, created } = await api.escalate(sid, "访客手动请求人工客服");
    chat.addSystemMessage(created ? "已为您创建人工工单，请稍候…" : "您已有处理中的工单");
    await enterTicketMode(t);
  } catch (e) {
    toast(e.message, true);
  }
});

// ---------- 发送 ----------

function autoResize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
}
input.addEventListener("input", autoResize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send();
  }
});
btnSend.addEventListener("click", send);

async function send() {
  const text = input.value.trim();
  if (!text || sending) return;
  input.value = "";
  autoResize();

  // 人工模式：走工单频道
  if (ticket && ticket.status !== "resolved") {
    chat.addUserMessage(text);
    try {
      await api.ticketReply(ticket.id, text);
    } catch (e) {
      toast(e.message, true);
    }
    return;
  }

  // AI 模式：SSE 流式
  sending = true;
  btnSend.disabled = true;
  chat.addUserMessage(text);
  const stream = chat.createStreamingMessage();
  let escalatedTicketId = null;

  try {
    await api.chatStream(text, sessions.currentSessionId(), {
      onSession(id) {
        if (!sessions.currentSessionId()) {
          sessions.setCurrentSession(id, text.slice(0, 30));
          sessions.refresh();
        }
      },
      onStep(step) { stream.addStep(step.step); },
      onSources(list) { stream.setSources(list); },
      onTicket(data) { escalatedTicketId = data.ticket_id; },
      onToken(t) { stream.addToken(t); },
      onError(msg) { stream.fail(msg); },
    });
    stream.finish();
  } catch (e) {
    stream.fail(e.message);
  } finally {
    sending = false;
    btnSend.disabled = false;
    input.focus();
  }

  sessions.refresh();
  // Agent 自动建单 → 进入人工模式
  if (escalatedTicketId) {
    try {
      const detail = await api.ticketDetail(escalatedTicketId);
      chat.addSystemMessage("人工工单已创建，客服接入后将在此对话");
      await enterTicketMode(detail.ticket);
    } catch { /* ignore */ }
  }
}

// ---------- 会话切换 ----------

async function selectSession(s) {
  exitTicketMode();
  chat.clearMessages();
  if (!s) {
    sessions.setCurrentSession(null, "新会话");
    return;
  }
  sessions.setCurrentSession(s.id, s.title);
  try {
    const msgs = await api.listMessages(s.id);
    for (const m of msgs) {
      if (m.role === "user") chat.addUserMessage(m.content);
      else chat.addAssistantMessage(m.content, m.sources);
    }
    chat.scrollToBottom(true);
    // 恢复未关闭的工单状态
    const { ticket: t } = await api.activeTicket(s.id);
    if (t) await enterTicketMode(t, { renderHistory: true });
  } catch (e) {
    toast(e.message, true);
  }
}

sessions.bindSelect(selectSession);

document.getElementById("btn-new-session").addEventListener("click", () => selectSession(null));

// ---------- 空状态示例问题 ----------

document.querySelectorAll(".example-card").forEach((card) => {
  card.addEventListener("click", () => {
    input.value = card.dataset.q;
    send();
  });
});

// ---------- 启动 ----------

sessions.refresh();
input.focus();
