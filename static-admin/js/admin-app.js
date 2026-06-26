/**
 * admin-app.js - Dashboard, navigation, role-based UI, WebSocket
 */
let ws = null;

// Logout
document.getElementById('btn-logout')?.addEventListener('click', () => Auth.logout());

// Tab switching
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    const panelId = 'tab-' + tab.dataset.tab;
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(panelId)?.classList.add('active');
    if (tab.dataset.tab === 'escalations') loadEscalations();
    if (tab.dataset.tab === 'knowledge') loadDocuments();
    if (tab.dataset.tab === 'conversations') loadConversations();
    if (tab.dataset.tab === 'stats') loadStats();
    if (tab.dataset.tab === 'settings') loadSettings();
    if (tab.dataset.tab === 'users') loadUsers();
  });
});

function showDashboard() {
  document.getElementById('login-page').style.display = 'none';
  document.getElementById('dashboard-page').style.display = 'block';
  document.getElementById('nav-staff-name').textContent = Auth.staffName;

  // Role badge
  const badge = document.getElementById('nav-role-badge');
  const roleLabels = { super_admin: 'S.Admin', admin: 'Admin', agent: 'Agent' };
  badge.textContent = roleLabels[Auth.role] || Auth.role;
  badge.className = 'role-badge ' + (Auth.role === 'super_admin' ? 'super-admin' : Auth.role === 'admin' ? 'admin' : 'agent');

  // Super admin sees everything
  if (Auth.role === 'super_admin') {
    document.getElementById('nav-settings').style.display = '';
    document.getElementById('nav-users').style.display = '';
  } else if (Auth.role === 'admin') {
    document.getElementById('nav-settings').style.display = '';
    document.getElementById('nav-users').style.display = 'none';
  } else {
    // Agent: only escalations + knowledge
    document.getElementById('nav-settings').style.display = 'none';
    document.getElementById('nav-users').style.display = 'none';
    document.querySelectorAll('[data-tab="conversations"]')[0].style.display = 'none';
    document.querySelectorAll('[data-tab="stats"]')[0].style.display = 'none';
  }

  loadEscalations();
  connectAdminWS();
  if (typeof startEscalationsPolling === 'function') startEscalationsPolling();
}

function connectAdminWS() {
  if (!Auth.token) return;
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${window.location.host}/ws/admin/${Auth.staffId}?token=${encodeURIComponent(Auth.token)}`;
  try {
    ws = new WebSocket(url);
    ws.onopen = () => updateWSIndicator(true);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'new_escalation') { if (typeof onNewEscalation === 'function') onNewEscalation(data.ticket); }
        if (data.type === 'ticket_updated') { if (typeof onTicketUpdated === 'function') onTicketUpdated(data.ticket); }
        if (data.type === 'ticket_message') { if (typeof onTicketMessage === 'function') onTicketMessage(data.ticket_id, data.message); }
      } catch (ex) {}
    };
    ws.onclose = () => { updateWSIndicator(false); setTimeout(() => { if (Auth.isLoggedIn()) connectAdminWS(); }, 5000); };
    ws.onerror = () => { ws?.close(); };
  } catch (e) { updateWSIndicator(false); }
}

function updateWSIndicator(connected) {
  const el = document.getElementById('ws-indicator');
  if (!el) return;
  el.textContent = connected ? '🟢' : '🔴';
  el.className = 'ws-indicator ' + (connected ? 'connected' : 'disconnected');
}

// ==================== User management (super_admin only) ====================

async function loadUsers() {
  try {
    const res = await Auth.fetch('/api/admin/users');
    const data = await res.json();
    const list = document.getElementById('user-list');
    list.innerHTML = data.users.map(u => {
      const isMe = u.email === Auth.staffName; // Auth.staffName is actually email
      const isSuperAdmin = Auth.role === 'super_admin';
      const roleClass = u.role === 'super_admin' ? 'super-admin' : u.role === 'admin' ? 'admin' : 'agent';
      return `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:0.5rem 0;border-bottom:1px solid var(--border);font-size:0.82rem;">
        <div>
          <strong>${escHtml(u.name)}</strong> ${isMe ? '<span style="font-size:0.6rem;color:var(--emerald);">(You)</span>' : ''}
          <span style="color:var(--text-muted);margin-left:0.5rem;">${escHtml(u.email)}</span>
          <span class="role-badge ${roleClass}" style="margin-left:0.5rem;">${u.role}</span>
        </div>
        ${isSuperAdmin ? `
        <div style="display:flex;gap:0.3rem;align-items:center;">
          ${u.role !== 'super_admin' ? `
            <select onchange="changeUserRole('${escHtml(u.email)}', this.value)" style="font-size:0.7rem;padding:0.15rem;border-radius:4px;border:1px solid var(--border);">
              <option value="">Role...</option>
              <option value="super_admin">Promote to S.Admin</option>
              <option value="admin" ${u.role==='admin'?'selected':''}>Admin</option>
              <option value="agent" ${u.role==='agent'?'selected':''}>Agent</option>
            </select>
            <button onclick="deleteUser('${escHtml(u.email)}')" style="border:none;background:none;cursor:pointer;color:var(--red);font-size:0.8rem;">Del</button>
          ` : (isMe ? `
            <select onchange="demoteMyself(this.value)" style="font-size:0.7rem;padding:0.15rem;border-radius:4px;border:1px solid var(--border);">
              <option value="">Demote self...</option>
              <option value="admin">Become Admin</option>
              <option value="agent">Become Agent</option>
            </select>
          ` : '<span style="font-size:0.65rem;color:var(--text-muted);">S.Admin</span>')}
        </div>` : `<span style="font-size:0.65rem;color:var(--text-muted);">${u.role}</span>`}
      </div>
    `}).join('');
  } catch (e) { console.error(e); }
}

async function createUser() {
  const el = document.getElementById('create-user-msg');
  try {
    const res = await Auth.fetch('/api/admin/users', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: document.getElementById('new-user-email').value,
        name: document.getElementById('new-user-name').value,
        password: document.getElementById('new-user-password').value,
        role: document.getElementById('new-user-role').value,
      }),
    });
    const d = await res.json();
    if (d.success) {
      el.textContent = d.message; el.style.color = '#10b981';
      document.getElementById('new-user-email').value = '';
      document.getElementById('new-user-name').value = '';
      document.getElementById('new-user-password').value = '';
      loadUsers();
    }
  } catch (e) { el.textContent = e.message; el.style.color = '#ef4444'; }
}

async function changeUserRole(email, role) {
  if (!role) return;
  try {
    await Auth.fetch(`/api/admin/users/${encodeURIComponent(email)}/role`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    loadUsers();
  } catch (e) { alert(e.message); }
}

async function demoteMyself(newRole) {
  if (!newRole) return;
  if (!confirm(`Demote yourself to ${newRole}? You will lose Super Admin privileges.`)) return;
  try {
    await Auth.fetch(`/api/admin/users/${encodeURIComponent(Auth.staffName)}/role`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: newRole }),
    });
    // Re-login to refresh role
    alert('Role changed. You will be redirected to login.');
    Auth.logout();
  } catch (e) { alert(e.message); }
}

async function deleteUser(email) {
  if (!confirm(`Delete user ${email}?`)) return;
  try {
    await Auth.fetch(`/api/admin/users/${encodeURIComponent(email)}`, { method: 'DELETE' });
    loadUsers();
  } catch (e) { alert(e.message); }
}

function escHtml(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

document.addEventListener('DOMContentLoaded', () => {
  if (Auth.isLoggedIn()) showDashboard();
});
