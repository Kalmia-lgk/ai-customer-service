/**
 * admin-escalations.js - 工单队列管理 + 实时聊天接管 + 自动刷新
 */
let currentTicketId = null;
let ticketsData = [];
let escalationsPollTimer = null;

// Filter change → reload
document.getElementById('filter-status')?.addEventListener('change', () => loadEscalations());

async function loadEscalations() {
  const filter = document.getElementById('filter-status')?.value || 'pending';
  const list = document.getElementById('ticket-list');
  try {
    const res = await Auth.fetch(`/api/admin/escalations?status_filter=${filter}`);
    if (!res.ok) {
      if (res.status === 401) return; // Auth.fetch handles logout
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    ticketsData = data.tickets || [];
    renderTicketList(ticketsData);
    updateBadge(data.waiting_count || 0);
  } catch (e) {
    console.error('加载工单失败:', e);
    if (list && !ticketsData.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-text">加载失败: ${e.message}<br><button onclick="loadEscalations()" style="margin-top:0.5rem;padding:0.3rem 1rem;border-radius:6px;border:1px solid var(--border);cursor:pointer;background:var(--bg);">🔄 重试</button></div></div>`;
    }
  }
}

function renderTicketList(tickets) {
  const list = document.getElementById('ticket-list');
  if (!tickets.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-text">暂无待处理工单</div><div style="font-size:0.7rem;color:var(--text3);margin-top:0.25rem;">工单将自动刷新（每5秒）</div></div>`;
    return;
  }
  list.innerHTML = tickets.map(t => `
    <div class="ticket-card${t.ticket_id === currentTicketId ? ' active' : ''}" data-id="${t.ticket_id}" onclick="selectTicket('${t.ticket_id}')">
      <div class="ticket-header">
        <span class="ticket-id">#${t.ticket_id.substring(0, 8)}</span>
        <span class="ticket-status status-${t.status}">${statusLabel(t.status)}</span>
      </div>
      <div class="ticket-reason">${escHtml(t.reason || '转人工请求')}</div>
      <div class="ticket-time">${fmtTime(t.created_at)}${t.assigned_staff_name ? ' · ' + t.assigned_staff_name : ''}</div>
    </div>
  `).join('');
}

function statusLabel(s) {
  const map = { waiting: '⏳ 等待中', in_progress: '🔵 处理中', resolved: '✅ 已解决' };
  return map[s] || s;
}

function selectTicket(ticketId) {
  currentTicketId = ticketId;
  document.querySelectorAll('.ticket-card').forEach(c => c.classList.remove('active'));
  document.querySelector(`.ticket-card[data-id="${ticketId}"]`)?.classList.add('active');
  renderTicketDetail(ticketId);
}

function renderTicketDetail(ticketId) {
  const ticket = ticketsData.find(t => t.ticket_id === ticketId);
  if (!ticket) return;

  const detail = document.getElementById('ticket-detail');
  const allMsgs = [...(ticket.conversation_snapshot || []), ...(ticket.messages || [])];

  detail.innerHTML = `
    <div class="ticket-detail-header">
      <div>
        <strong>工单 #${ticketId.substring(0, 8)}</strong>
        <span style="font-size:0.75rem;color:var(--text3);margin-left:0.5rem;">${escHtml(ticket.reason || '')}</span>
      </div>
      <div style="display:flex;gap:0.5rem;">
        ${ticket.status === 'waiting' ? `<button class="btn-take" onclick="takeTicket('${ticketId}')">🎧 接管</button>` : ''}
        ${ticket.status === 'in_progress' ? `<button class="btn-resolve" onclick="resolveTicket('${ticketId}')">✅ 解决</button>` : ''}
        ${ticket.status === 'resolved' ? `<span style="font-size:0.8rem;color:var(--text3);">已解决 · ${fmtTime(ticket.resolved_at)}</span>` : ''}
      </div>
    </div>
    <div class="ticket-chat" id="ticket-chat">
      ${allMsgs.length === 0 ? '<div class="empty-state"><div class="empty-text">暂无消息</div></div>' : ''}
      ${allMsgs.map(m => renderMsg(m)).join('')}
    </div>
    ${ticket.status === 'in_progress' ? `
    <div class="ticket-input-row">
      <input type="text" id="reply-input" placeholder="输入回复..." onkeydown="if(event.key==='Enter')sendReply('${ticketId}')">
      <button onclick="sendReply('${ticketId}')">发送</button>
    </div>` : ''}
  `;
}

function renderMsg(m) {
  const roleClass = m.role === 'user' ? 'user' : m.role === 'system' ? 'system' : 'assistant';
  const sender = m.staff_name ? `👨‍💼 ${m.staff_name}` : (m.role === 'user' ? '👤 客户' : '🤖 AI');
  return `<div class="msg ${roleClass}"><div class="meta">${sender} · ${fmtTime(m.timestamp)}</div><div class="body">${escHtml(m.content || '')}</div></div>`;
}

async function takeTicket(ticketId) {
  try {
    const res = await Auth.fetch(`/api/admin/escalations/${ticketId}/take`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('✅ 工单已接管', 'success');
      await loadEscalations();
      selectTicket(ticketId);
    }
  } catch (e) { showToast('接管失败: ' + e.message, 'error'); }
}

async function sendReply(ticketId) {
  const input = document.getElementById('reply-input');
  const msg = input?.value?.trim();
  if (!msg) return;
  try {
    const res = await Auth.fetch(`/api/admin/escalations/${ticketId}/reply`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg }),
    });
    const data = await res.json();
    if (data.success) {
      input.value = '';
      // Refresh ticket
      const idx = ticketsData.findIndex(t => t.ticket_id === ticketId);
      if (idx >= 0 && data.ticket) { ticketsData[idx] = data.ticket; }
      renderTicketDetail(ticketId);
    }
  } catch (e) { showToast('发送失败: ' + e.message, 'error'); }
}

async function resolveTicket(ticketId) {
  if (!confirm('确定要解决此工单吗？')) return;
  try {
    const res = await Auth.fetch(`/api/admin/escalations/${ticketId}/resolve`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast('✅ 工单已解决', 'success');
      currentTicketId = null;
      await loadEscalations();
    }
  } catch (e) { showToast('操作失败: ' + e.message, 'error'); }
}

// ==================== WebSocket 事件处理 ====================

function onNewEscalation(ticket) {
  showToast(`🔔 新工单: ${ticket.reason || '转人工请求'}`, 'info');
  loadEscalations();
  // 闪烁标签页标题
  let count = 0;
  const origTitle = document.title;
  const blink = setInterval(() => {
    document.title = (count++ % 2 === 0) ? '🔔 新工单! - 管理端' : origTitle;
    if (count > 6) { clearInterval(blink); document.title = origTitle; }
  }, 800);
}

function onTicketUpdated(ticket) {
  const idx = ticketsData.findIndex(t => t.ticket_id === ticket.ticket_id);
  if (idx >= 0) ticketsData[idx] = ticket;
  else { ticketsData.unshift(ticket); renderTicketList(ticketsData); }
  if (currentTicketId === ticket.ticket_id) renderTicketDetail(ticket.ticket_id);
  updateBadgeFromData();
}

function onTicketMessage(ticketId, message) {
  if (currentTicketId === ticketId) {
    const chat = document.getElementById('ticket-chat');
    if (chat) {
      const div = document.createElement('div');
      div.className = `msg ${message.role}`;
      div.innerHTML = `<div class="meta">${message.role === 'user' ? '👤 客户' : '👨‍💼 客服'} · 刚刚</div><div class="body">${escHtml(message.content || '')}</div>`;
      chat.appendChild(div);
      chat.scrollTop = chat.scrollHeight;
    }
  }
  // Also refresh list to update message counts
  loadEscalations();
}

function updateBadge(count) {
  const badge = document.getElementById('badge-escalations');
  if (!badge) return;
  if (count > 0) { badge.textContent = count; badge.classList.add('show'); }
  else { badge.classList.remove('show'); }
}

function updateBadgeFromData() {
  const waiting = ticketsData.filter(t => t.status === 'waiting').length;
  updateBadge(waiting);
}

// ==================== Auto-refresh ====================

function startEscalationsPolling() {
  if (escalationsPollTimer) clearInterval(escalationsPollTimer);
  escalationsPollTimer = setInterval(() => {
    // Only poll when the escalations tab is visible
    const tab = document.getElementById('tab-escalations');
    if (tab && tab.classList.contains('active')) {
      loadEscalations();
    }
  }, 5000); // 每5秒刷新
}

// Start polling when admin logs in
const origShowDashboard = window._showDashboard;
document.addEventListener('admin-logged-in', () => {
  startEscalationsPolling();
});

// ==================== Utilities ====================

function showToast(msg, type) {
  const div = document.createElement('div');
  div.style.cssText = `position:fixed;top:1rem;right:1rem;z-index:9999;padding:0.6rem 1rem;border-radius:8px;font-size:0.85rem;font-weight:500;animation:toastIn 0.3s;box-shadow:0 2px 8px rgba(0,0,0,0.15);${type==='success'?'background:#d1fae5;color:#065f46':type==='error'?'background:#fee2e2;color:#991b1b':'background:#eef2ff;color:#4f46e5'}`;
  div.textContent = msg;
  document.body.appendChild(div);
  setTimeout(() => { div.style.opacity = '0'; div.style.transition = 'opacity 0.3s'; setTimeout(() => div.remove(), 300); }, 3000);
}

function escHtml(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso); const now = new Date(); const diff = now - d;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return Math.floor(diff/60000) + '分钟前';
  if (diff < 86400000) return Math.floor(diff/3600000) + '小时前';
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}
