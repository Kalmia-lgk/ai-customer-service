/**
 * admin-conversations.js - 会话监控
 */
async function loadConversations() {
  try {
    const res = await Auth.fetch('/api/admin/conversations');
    const data = await res.json();
    const sessions = data.sessions || [];
    const list = document.getElementById('conv-list');
    if (!sessions.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">💬</div><div class="empty-text">暂无会话记录</div></div>';
      return;
    }
    list.innerHTML = sessions.map(s => `
      <div class="conv-item" onclick="viewConversation('${s.session_id}')">
        <div class="conv-title">${escapeHtml(s.title || '新会话')}</div>
        <div class="conv-meta">${s.message_count || 0} 条消息 · ${formatTime(s.updated_at)}</div>
        <div class="conv-detail" id="conv-${s.session_id}" style="display:none;"></div>
      </div>
    `).join('');
  } catch(e) { console.error(e); }
}

async function viewConversation(sid) {
  const detailEl = document.getElementById('conv-' + sid);
  if (detailEl.style.display === 'block') {
    detailEl.style.display = 'none';
    return;
  }
  // Hide all others
  document.querySelectorAll('.conv-detail').forEach(el => el.style.display = 'none');
  detailEl.style.display = 'block';

  if (detailEl.innerHTML) return; // Already loaded
  try {
    const res = await Auth.fetch(`/api/admin/conversations/${sid}`);
    const data = await res.json();
    const msgs = data.messages || [];
    detailEl.innerHTML = msgs.length === 0
      ? '<div style="color:var(--text3);padding:0.5rem;">无消息记录</div>'
      : msgs.map(m => {
        const role = m.role === 'user' ? '👤 客户' : '🤖 AI';
        return `<div style="margin-bottom:0.5rem;"><strong style="font-size:0.7rem;color:var(--text3);">${role}</strong><div style="font-size:0.82rem;color:var(--text);background:var(--bg);padding:0.4rem 0.6rem;border-radius:8px;margin-top:0.15rem;">${escapeHtml(m.content).substring(0, 200)}${m.content.length>200?'...':''}</div></div>`;
      }).join('');
  } catch(e) { detailEl.innerHTML = '<div style="color:red;">加载失败</div>'; }
}

function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
function formatTime(iso) {
  if (!iso) return ''; const d = new Date(iso); const now = new Date(); const diff = now - d;
  if (diff < 60000) return '刚刚'; if (diff < 3600000) return Math.floor(diff/60000)+'分钟前'; if (diff < 86400000) return Math.floor(diff/3600000)+'小时前';
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
}
