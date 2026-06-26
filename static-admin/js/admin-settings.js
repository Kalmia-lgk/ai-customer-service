/**
 * admin-settings.js - 系统设置：修改密码 + API 配置
 */

// Load current settings when tab is shown
async function loadSettings() {
  try {
    const res = await Auth.fetch('/api/admin/settings');
    const d = await res.json();
    document.getElementById('api-provider').value = d.llm_provider || 'openai';
    document.getElementById('api-openai-key').placeholder = d.openai_api_key || 'sk-...';
    document.getElementById('api-openai-model').placeholder = d.openai_model || 'gpt-4o-mini';
    document.getElementById('api-groq-key').placeholder = d.groq_api_key || 'gsk_...';
    document.getElementById('api-groq-model').placeholder = d.groq_model || 'llama-3.3-70b-versatile';
    document.getElementById('api-msg').textContent = d.demo_mode
      ? '当前: Demo 模式（无有效 API Key）'
      : '当前: ' + d.llm_provider.toUpperCase() + ' / ' + d.openai_model;
    document.getElementById('api-msg').style.color = d.demo_mode ? '#f59e0b' : '#10b981';
  } catch (e) {
    console.error('Load settings failed:', e);
  }
}

// Change password
async function doChangePassword() {
  const current = document.getElementById('current-password').value;
  const newPass = document.getElementById('new-password').value;
  const confirm = document.getElementById('confirm-password').value;
  const msg = document.getElementById('password-msg');

  if (newPass !== confirm) { msg.textContent = '两次密码不一致'; msg.style.color = '#ef4444'; return; }
  if (newPass.length < 6) { msg.textContent = '新密码至少6位'; msg.style.color = '#ef4444'; return; }

  try {
    const res = await Auth.fetch('/api/admin/settings/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: current, new_password: newPass }),
    });
    const d = await res.json();
    if (d.success) {
      msg.textContent = d.message;
      msg.style.color = '#10b981';
      document.getElementById('current-password').value = '';
      document.getElementById('new-password').value = '';
      document.getElementById('confirm-password').value = '';
    } else {
      msg.textContent = d.detail || '修改失败';
      msg.style.color = '#ef4444';
    }
  } catch (e) {
    msg.textContent = '请求失败: ' + e.message;
    msg.style.color = '#ef4444';
  }
}

// Save API config
async function doSaveApiConfig() {
  const msg = document.getElementById('api-msg');
  const config = {
    llm_provider: document.getElementById('api-provider').value,
    openai_api_key: document.getElementById('api-openai-key').value,
    openai_model: document.getElementById('api-openai-model').value,
    groq_api_key: document.getElementById('api-groq-key').value,
    groq_model: document.getElementById('api-groq-model').value,
  };

  try {
    msg.textContent = '保存中...';
    msg.style.color = 'var(--text3)';
    const res = await Auth.fetch('/api/admin/settings/api-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const d = await res.json();
    if (d.success) {
      msg.textContent = d.message + ' | ' + d.provider + ' / ' + d.model;
      msg.style.color = d.demo_mode ? '#f59e0b' : '#10b981';
      // Clear input fields
      document.getElementById('api-openai-key').value = '';
      document.getElementById('api-groq-key').value = '';
    }
  } catch (e) {
    msg.textContent = '保存失败: ' + e.message;
    msg.style.color = '#ef4444';
  }
}

// Update tab switching to load settings
const origTabClick = document.querySelectorAll('.nav-tab');
origTabClick.forEach(tab => {
  tab.addEventListener('click', function() {
    if (this.dataset.tab === 'settings') loadSettings();
  });
});
