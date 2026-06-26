/**
 * chat.js - 客户聊天：SSE 流式 + 转人工 + WebSocket 实时通信
 */

// ==================== 状态 ====================
let currentSessionId = null;
let isStreaming = false;
let activeTicketId = null;
let wsConnection = null;
let pollingTimer = null;

// ==================== 初始化 ====================
function initChatEvents() {
  const input = document.getElementById('message-input');
  const sendBtn = document.getElementById('btn-send');
  const escalateBtn = document.getElementById('btn-escalate');

  sendBtn?.addEventListener('click', sendMessage);
  escalateBtn?.addEventListener('click', () => {
    document.getElementById('escalate-modal').style.display = 'flex';
  });

  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input?.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
  });

  document.getElementById('btn-escalate-cancel')?.addEventListener('click', () => {
    document.getElementById('escalate-modal').style.display = 'none';
  });
  document.getElementById('btn-escalate-confirm')?.addEventListener('click', doEscalate);

  document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
}

// ==================== 消息发送 ====================
async function sendMessage() {
  const input = document.getElementById('message-input');
  const message = input.value.trim();
  if (!message || isStreaming) return;

  input.value = ''; input.style.height = 'auto';
  document.getElementById('welcome-screen').style.display = 'none';

  // ★ 关键修复1：输入"转人工"等关键词自动触发转人工
  const escalateKeywords = ['转人工', '人工客服', '人工服务', '找人工', '真人', '我要投诉', '转接'];
  if (escalateKeywords.some(kw => message.includes(kw))) {
    appendMessage('user', message);
    doEscalate();
    return;
  }

  // ★ 关键修复2：如果已有活跃工单（人工已接入），消息发给人工通道，不走AI
  if (activeTicketId) {
    appendMessage('user', message);
    await sendToHumanChannel(message);
    return;
  }

  if (!currentSessionId) currentSessionId = generateUUID();

  appendMessage('user', message);
  const aiMsg = appendMessage('assistant', '', true);
  const bubble = aiMsg.querySelector('.bubble');

  isStreaming = true;
  document.getElementById('btn-send').disabled = true;

  let fullContent = '';
  let sources = [];

  try {
    const res = await fetch('/api/customer/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, message, stream: true }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;
        let eventType = 'message', dataStr = '';
        for (const line of block.split('\n')) {
          if (line.startsWith('event: ')) eventType = line.substring(7).trim();
          else if (line.startsWith('data: ')) dataStr = line.substring(6);
        }
        if (!dataStr) continue;
        try {
          const payload = JSON.parse(dataStr);
          switch (eventType) {
            case 'session': currentSessionId = payload.session_id; break;
            case 'sources': sources = payload.sources || []; break;
            case 'error': fullContent += `\n\n❌ ${payload.content || ''}`; bubble.innerHTML = renderMarkdown(fullContent); break;
            case 'done': break;
            default:
              if (payload.content) { fullContent += payload.content; bubble.innerHTML = renderMarkdown(fullContent); scrollToBottom(); }
          }
        } catch (e) { /* skip */ }
      }
    }
  } catch (e) {
    fullContent += `\n\n❌ 网络错误: ${e.message}`;
    bubble.innerHTML = renderMarkdown(fullContent);
  }

  aiMsg.classList.remove('streaming');
  const typing = aiMsg.querySelector('.typing-indicator');
  if (typing) typing.remove();
  if (!fullContent) { fullContent = '抱歉，回复生成失败，请重试。'; bubble.innerHTML = renderMarkdown(fullContent); }
  if (sources.length > 0) addSources(aiMsg, sources);

  // Demo 检测
  if (fullContent.includes('Demo 模式') || fullContent.includes('演示模式')) {
    const badge = document.getElementById('status-badge');
    if (badge) { badge.style.display = 'inline-block'; badge.textContent = '🎮 Demo'; badge.className = 'status-badge demo'; }
  }

  isStreaming = false;
  document.getElementById('btn-send').disabled = false;
  scrollToBottom();
}

// ==================== 转人工 ====================
async function doEscalate() {
  document.getElementById('escalate-modal').style.display = 'none';
  if (!currentSessionId) { showToast('请先发送一条消息', 'error'); return; }

  const bar = document.getElementById('escalation-bar');
  bar.style.display = 'block';
  bar.style.background = 'var(--accent-light)';
  bar.style.color = 'var(--accent)';
  bar.textContent = '⏳ 正在为您转接人工客服...';

  try {
    const res = await fetch('/api/customer/escalate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: currentSessionId, reason: '用户请求转人工客服' }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.message || '转接失败');

    activeTicketId = data.ticket_id;
    bar.textContent = '⏳ 正在等待人工客服接入...';

    // 尝试 WebSocket，失败则轮询
    connectWebSocket(activeTicketId);
  } catch (e) {
    bar.style.background = '#fee2e2';
    bar.style.color = '#991b1b';
    bar.textContent = `❌ 转接失败: ${e.message}`;
    showToast('转人工失败，请重试', 'error');
  }
}

// ==================== 人工通道消息 ====================
async function sendToHumanChannel(message) {
  // 尝试通过 WebSocket 发送
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(JSON.stringify({ type: 'customer_message', message }));
    return;
  }
  // 降级：通过 HTTP API 发送
  try {
    await fetch(`/api/customer/ticket/${activeTicketId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
  } catch (e) {
    showToast('消息发送失败，请重试', 'error');
  }
}

// ==================== WebSocket ====================
function connectWebSocket(ticketId) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${window.location.host}/ws/customer/${ticketId}`;

  try {
    wsConnection = new WebSocket(url);
  } catch (e) {
    console.warn('WebSocket 不可用，降级为轮询');
    startPolling(ticketId);
    return;
  }

  wsConnection.onopen = () => {
    console.log('WebSocket 已连接');
    if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null; }
  };

  wsConnection.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEscalationEvent(data);
    } catch (e) { console.error('WS 消息解析失败', e); }
  };

  wsConnection.onerror = () => {
    console.warn('WebSocket 连接失败，降级为轮询');
    wsConnection = null;
    startPolling(ticketId);
  };

  wsConnection.onclose = () => {
    wsConnection = null;
    if (!pollingTimer) startPolling(ticketId);
  };
}

function startPolling(ticketId) {
  if (pollingTimer) return;
  pollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/customer/ticket/${ticketId}/status`);
      if (!res.ok) return;
      const data = await res.json();
      handleEscalationEvent({ type: 'status', ticket: data });
      if (data.status === 'resolved') { clearInterval(pollingTimer); pollingTimer = null; }
    } catch (e) { /* ignore */ }
  }, 5000);
}

function handleEscalationEvent(data) {
  const bar = document.getElementById('escalation-bar');
  switch (data.type) {
    case 'human_joined':
      bar.style.display = 'block';
      bar.style.background = '#d1fae5';
      bar.style.color = '#065f46';
      bar.textContent = `✅ 人工客服 ${data.staff_name || ''} 已接入，正在为您服务`;
      showToast('人工客服已接入！', 'success');
      appendSystemMessage(`👨‍💼 人工客服 **${data.staff_name || ''}** 已接入，正在为您服务`);
      break;
    case 'human_reply':
      appendMessage('assistant', data.message, false, data.staff_name);
      scrollToBottom();
      break;
    case 'escalation_resolved':
      bar.style.display = 'block';
      bar.style.background = 'var(--bg-tertiary)';
      bar.style.color = 'var(--text-secondary)';
      bar.textContent = '👋 人工服务已结束，感谢您的反馈';
      appendSystemMessage('👋 人工服务已结束，感谢您的反馈！如有需要可再次转接。');
      activeTicketId = null;
      if (wsConnection) { wsConnection.close(); wsConnection = null; }
      if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null; }
      break;
    case 'status':
      // 轮询状态更新
      if (data.ticket) {
        const t = data.ticket;
        if (t.status === 'in_progress' && bar.textContent.includes('等待')) {
          bar.style.background = '#d1fae5';
          bar.style.color = '#065f46';
          bar.textContent = `✅ 人工客服 ${t.assigned_staff_name || ''} 已接入`;
          appendSystemMessage(`👨‍💼 人工客服 **${t.assigned_staff_name || ''}** 已接入`);
        }
        // 检查新消息
        if (t.messages && t.messages.length > 0) {
          const lastMsg = t.messages[t.messages.length - 1];
          if (lastMsg.role === 'assistant' && lastMsg.content && lastMsg.timestamp) {
            const existing = document.querySelectorAll('.message.assistant .bubble');
            let found = false;
            existing.forEach(el => { if (el.textContent.includes(lastMsg.content.substring(0, 20))) found = true; });
            if (!found) appendMessage('assistant', lastMsg.content, false, lastMsg.staff_name);
          }
        }
        if (t.status === 'resolved') {
          bar.textContent = '👋 人工服务已结束';
          activeTicketId = null;
          if (pollingTimer) { clearInterval(pollingTimer); pollingTimer = null; }
        }
      }
      break;
  }
}

// ==================== 消息渲染 ====================
function appendMessage(role, content, streaming = false, staffName = null) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${role}${streaming ? ' streaming' : ''}`;
  const avatar = role === 'user' ? '👤' : (staffName ? '👨‍💼' : '🤖');
  msgDiv.innerHTML = `
    <div class="avatar">${avatar}</div>
    <div class="bubble">${content ? renderMarkdown(content) : '<div class="typing-indicator"><span></span><span></span><span></span></div>'}</div>
  `;
  if (staffName) {
    const label = document.createElement('div');
    label.style.cssText = 'font-size:0.7rem;color:var(--text-muted);margin-bottom:0.15rem;';
    label.textContent = staffName;
    msgDiv.querySelector('.bubble').prepend(label);
  }
  document.getElementById('messages-container').appendChild(msgDiv);
  scrollToBottom();
  return msgDiv;
}

function appendSystemMessage(text) {
  const div = document.createElement('div');
  div.style.cssText = 'text-align:center;padding:0.5rem 0;font-size:0.8rem;color:var(--text-muted);';
  div.innerHTML = renderMarkdown(text);
  document.getElementById('messages-container').appendChild(div);
  scrollToBottom();
}

function addSources(msgEl, sources) {
  const div = document.createElement('div');
  div.className = 'sources-container';
  div.innerHTML = `<div class="sources-title">📎 参考来源</div>${sources.map(s => `<div class="source-item"><span>📄</span><span class="source-doc">${escapeHtml(s.document_name || '未知')}</span><span>${Math.round((s.score||0)*100)}%</span></div>`).join('')}`;
  msgEl.querySelector('.bubble').appendChild(div);
}

function renderMarkdown(text) {
  if (!text) return '';
  if (typeof marked !== 'undefined') return marked.parse(text);
  return escapeHtml(text).replace(/\n/g, '<br>');
}

function scrollToBottom() {
  const c = document.getElementById('messages-container');
  if (c) requestAnimationFrame(() => { c.scrollTop = c.scrollHeight; });
}

function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function generateUUID() { return crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r = Math.random()*16|0; return (c==='x'?r:r&0x3|0x8).toString(16); }); }
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  document.getElementById('theme-toggle').textContent = next === 'dark' ? '☀️' : '🌙';
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
  document.getElementById('theme-toggle').textContent = (localStorage.getItem('theme') || 'light') === 'dark' ? '☀️' : '🌙';
  if (typeof marked !== 'undefined') marked.setOptions({ breaks: true, gfm: true });
  initChatEvents();
  checkServerStatus();
});

async function checkServerStatus() {
  try {
    const res = await fetch('/api/health');
    const d = await res.json();
    const badge = document.getElementById('status-badge');
    if (badge) {
      badge.style.display = 'inline-block';
      if (d.demo_mode) { badge.textContent = '🎮 Demo'; badge.className = 'status-badge demo'; }
      else { badge.textContent = '🟢 在线'; badge.className = 'status-badge online'; }
    }
  } catch (e) {
    const badge = document.getElementById('status-badge');
    if (badge) { badge.style.display = 'inline-block'; badge.textContent = '🔴 离线'; badge.className = 'status-badge offline'; }
  }
}
