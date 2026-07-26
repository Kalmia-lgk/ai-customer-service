// 工单页：列表-详情双栏 + WS 实时插入/更新
import * as api from "../api.js";
import { esc, fmtTime, statusDot, toast } from "../ui.js";

let tickets = [];
let filter = "";
let current = null; // 当前选中的工单对象
let wsHandler = null;

export async function render(root) {
  root.innerHTML = `
    <div class="page-head"><h2>工单</h2></div>
    <div class="tickets-layout">
      <div class="ticket-list-pane">
        <div class="ticket-filters">
          <button class="btn btn-outline btn-sm active" data-f="">全部</button>
          <button class="btn btn-outline btn-sm" data-f="waiting">待接入</button>
          <button class="btn btn-outline btn-sm" data-f="in_progress">处理中</button>
          <button class="btn btn-outline btn-sm" data-f="resolved">已解决</button>
        </div>
        <div class="ticket-items" id="ticket-items"></div>
      </div>
      <div class="ticket-detail-pane card" id="ticket-detail">
        <div class="ticket-detail-empty">从左侧选择一个工单</div>
      </div>
    </div>`;

  root.querySelectorAll("[data-f]").forEach((btn) => {
    btn.addEventListener("click", () => {
      filter = btn.dataset.f;
      root.querySelectorAll("[data-f]").forEach((b) => b.classList.toggle("active", b === btn));
      loadList();
    });
  });

  wsHandler = (e) => handleWS(e.detail);
  window.addEventListener("admin-ws", wsHandler);

  await loadList();
}

export function destroy() {
  window.removeEventListener("admin-ws", wsHandler);
  current = null;
}

async function loadList(flashId = null) {
  tickets = await api.listTickets(filter || undefined);
  const box = document.getElementById("ticket-items");
  if (!box) return;
  if (!tickets.length) {
    box.innerHTML = `<div class="empty-hint">暂无工单</div>`;
    return;
  }
  box.innerHTML = tickets.map((t) => `
    <div class="ticket-item card ${t.id === current?.id ? "active" : ""} ${t.id === flashId ? "flash" : ""}" data-id="${t.id}">
      <div class="t-row">${statusDot(t.status)}<span class="t-time">${fmtTime(t.created_at)}</span></div>
      <div class="t-reason">${esc(t.reason || "（无说明）")}</div>
    </div>`).join("");
  box.querySelectorAll(".ticket-item").forEach((el) => {
    el.addEventListener("click", () => openDetail(el.dataset.id));
  });
}

async function openDetail(id) {
  const { ticket, messages } = await api.ticketMessages(id);
  current = ticket;
  document.querySelectorAll(".ticket-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.id === id)
  );

  const pane = document.getElementById("ticket-detail");
  const canReply = ticket.status === "in_progress";
  pane.innerHTML = `
    <div class="ticket-detail-head">
      <div class="info">
        <div class="reason">${esc(ticket.reason || "（无说明）")}</div>
        <div class="meta">访客 ${esc(ticket.visitor_id.slice(0, 8))} · 创建于 ${fmtTime(ticket.created_at)} · ${statusDot(ticket.status)}</div>
      </div>
      <div class="actions" style="display:flex;gap:8px">
        ${ticket.status === "waiting" ? `<button class="btn btn-primary btn-sm" id="btn-claim">接管工单</button>` : ""}
        ${ticket.status === "in_progress" ? `<button class="btn btn-outline btn-sm" id="btn-resolve">标记解决</button>` : ""}
      </div>
    </div>
    <details class="ai-context" id="ai-context">
      <summary>查看转人工前的 AI 对话记录</summary>
      <div class="ctx-body" id="ctx-body">加载中…</div>
    </details>
    <div class="ticket-msgs" id="ticket-msgs">
      ${messages.map(msgHtml).join("")}
    </div>
    <div class="ticket-reply">
      <textarea class="input" id="reply-input" rows="2" ${canReply ? "" : "disabled"}
        placeholder="${canReply ? "输入回复，Ctrl+Enter 发送" : ticket.status === "waiting" ? "接管工单后可回复" : "工单已关闭"}"></textarea>
      <button class="btn btn-primary" id="btn-reply" ${canReply ? "" : "disabled"}>发送</button>
    </div>`;

  scrollMsgs();

  document.getElementById("btn-claim")?.addEventListener("click", async () => {
    await api.claimTicket(ticket.id);
    toast("已接管，开始对话");
    openDetail(ticket.id);
    loadList();
  });
  document.getElementById("btn-resolve")?.addEventListener("click", async () => {
    await api.resolveTicket(ticket.id);
    toast("工单已解决");
    openDetail(ticket.id);
    loadList();
  });

  const input = document.getElementById("reply-input");
  const send = async () => {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    try {
      await api.replyTicket(ticket.id, text); // 消息经 WS 推回并渲染
    } catch (e) { toast(e.message, true); }
  };
  document.getElementById("btn-reply")?.addEventListener("click", send);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.ctrlKey) { e.preventDefault(); send(); }
  });

  // 懒加载 AI 前情
  document.getElementById("ai-context").addEventListener("toggle", async function () {
    if (!this.open || this.dataset.loaded) return;
    this.dataset.loaded = "1";
    try {
      const ctx = await api.ticketContext(ticket.id);
      document.getElementById("ctx-body").innerHTML = ctx.length
        ? ctx.map((m) => `<div class="ctx-line"><b>${m.role === "user" ? "访客" : "AI"}：</b>${esc(m.content)}</div>`).join("")
        : `<div class="ctx-line">无 AI 对话记录</div>`;
    } catch { /* ignore */ }
  }, { once: false });
}

function msgHtml(m) {
  if (m.sender === "system") return `<div class="tmsg tmsg-system">${esc(m.content)}</div>`;
  const cls = m.sender === "agent" ? "tmsg-agent" : "tmsg-customer";
  const who = m.sender === "agent" ? esc(m.sender_name) : "访客";
  return `
    <div class="tmsg ${cls}">
      <div class="who">${who} · ${fmtTime(m.created_at)}</div>
      <div class="body">${esc(m.content)}</div>
    </div>`;
}

function scrollMsgs() {
  const box = document.getElementById("ticket-msgs");
  if (box) box.scrollTop = box.scrollHeight;
}

function handleWS(data) {
  if (data.type === "new_ticket") {
    loadList(data.ticket?.id);
  } else if (data.type === "ticket_update") {
    loadList();
    if (data.ticket?.id === current?.id) openDetail(current.id);
  } else if (data.type === "ticket_message") {
    const m = data.message;
    if (m.ticket_id === current?.id) {
      const box = document.getElementById("ticket-msgs");
      if (box) {
        box.insertAdjacentHTML("beforeend", msgHtml(m));
        scrollMsgs();
      }
    }
  }
}
