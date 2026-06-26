/**
 * admin-auth.js - Login & Register (no social login, no default account)
 */
const Auth = {
  token: localStorage.getItem('admin_token') || null,
  staffId: localStorage.getItem('admin_staff_id') || null,
  staffName: localStorage.getItem('admin_staff_name') || null,
  role: localStorage.getItem('admin_role') || '',
  avatar: localStorage.getItem('admin_avatar') || '',

  async login(email, password) {
    const res = await fetch('/api/admin/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    return this._save(data);
  },

  async register(email, password, name) {
    const res = await fetch('/api/admin/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    return await this.login(email, password);
  },

  _save(data) {
    this.token = data.access_token;
    this.staffId = data.user_id || data.staff_id;
    this.staffName = data.name || data.staff_name;
    this.role = data.role || '';
    this.avatar = data.avatar || '';
    localStorage.setItem('admin_token', this.token);
    localStorage.setItem('admin_staff_id', this.staffId);
    localStorage.setItem('admin_staff_name', this.staffName);
    localStorage.setItem('admin_role', this.role);
    localStorage.setItem('admin_avatar', this.avatar);
    return data;
  },

  logout() {
    this.token = null; this.staffId = null; this.staffName = null; this.role = ''; this.avatar = '';
    ['admin_token','admin_staff_id','admin_staff_name','admin_role','admin_avatar'].forEach(k => localStorage.removeItem(k));
    document.getElementById('login-page').style.display = 'flex';
    document.getElementById('dashboard-page').style.display = 'none';
  },

  async fetch(url, options = {}) {
    const headers = { ...options.headers, 'Authorization': `Bearer ${this.token}` };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) { this.logout(); throw new Error('Session expired'); }
    return res;
  },

  isLoggedIn() { return !!this.token; }
};

// Login form
document.getElementById('login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const el = document.getElementById('login-error');
  try {
    await Auth.login(document.getElementById('login-email').value, document.getElementById('login-password').value);
    showDashboard();
  } catch (err) { el.textContent = err.message; }
});

// Register form
document.getElementById('register-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const el = document.getElementById('register-error');
  const pw = document.getElementById('reg-password').value;
  if (pw !== document.getElementById('reg-password2').value) { el.textContent = 'Passwords do not match'; return; }
  try {
    await Auth.register(document.getElementById('reg-email').value, pw, document.getElementById('reg-name').value);
    showDashboard();
  } catch (err) { el.textContent = err.message; }
});

// Tab switching
document.getElementById('tab-login-btn')?.addEventListener('click', () => {
  document.getElementById('tab-login-btn').classList.add('active');
  document.getElementById('tab-register-btn').classList.remove('active');
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('register-form').style.display = 'none';
});
document.getElementById('tab-register-btn')?.addEventListener('click', () => {
  document.getElementById('tab-register-btn').classList.add('active');
  document.getElementById('tab-login-btn').classList.remove('active');
  document.getElementById('login-form').style.display = 'none';
  document.getElementById('register-form').style.display = 'block';
});

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-logout')?.addEventListener('click', () => Auth.logout());
  if (Auth.isLoggedIn()) showDashboard();
});
