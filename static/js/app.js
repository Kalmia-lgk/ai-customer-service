/**
 * ============================================================
 * app.js - 应用主入口：初始化、主题管理、全局状态、工具函数
 * ============================================================
 */

// ==================== 全局应用状态 ====================
const AppState = {
  /** 当前会话 ID */
  currentSessionId: null,
  /** 所有会话列表 */
  sessions: [],
  /** 知识库统计 */
  kbStats: { document_count: 0, total_chunks: 0 },
  /** 当前主题 */
  theme: localStorage.getItem('theme') || 'light',
  /** 是否正在等待 AI 回复 */
  isStreaming: false,
  /** 知识库面板是否展开 */
  kbPanelOpen: true,
};

// ==================== 主题管理 ====================
function initTheme() {
  const html = document.documentElement;
  html.setAttribute('data-theme', AppState.theme);
  updateThemeIcons();
}

function toggleTheme() {
  AppState.theme = AppState.theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', AppState.theme);
  localStorage.setItem('theme', AppState.theme);
  updateThemeIcons();
}

function updateThemeIcons() {
  const isDark = AppState.theme === 'dark';
  const icons = document.querySelectorAll('#theme-toggle, #theme-toggle-2');
  icons.forEach(btn => { btn.textContent = isDark ? '☀️' : '🌙'; });
}

// ==================== Toast 通知 ====================
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ==================== DOM 元素引用 ====================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const DOM = {
  sidebar: $('#sidebar'),
  chatArea: $('#chat-area'),
  kbPanel: $('#kb-panel'),
  sessionList: $('#session-list'),
  messagesContainer: $('#messages-container'),
  welcomeScreen: $('#welcome-screen'),
  messageInput: $('#message-input'),
  btnSend: $('#btn-send'),
  btnEscalate: $('#btn-escalate'),
  btnNewChat: $('#btn-new-chat'),
  btnToggleKb: $('#btn-toggle-kb'),
  btnCloseKb: $('#btn-close-kb'),
  mobileOverlay: $('#mobile-overlay'),
  escalateModal: $('#escalate-modal'),
  docList: $('#doc-list'),
  docEmptyState: $('#doc-empty-state'),
  uploadDropzone: $('#upload-dropzone'),
  fileInput: $('#file-input'),
  kbStats: $('#kb-stats'),
  btnReindex: $('#btn-reindex'),
};

// ==================== 移动端适配 ====================
function closeMobilePanels() {
  DOM.sidebar?.classList.remove('mobile-open');
  DOM.kbPanel?.classList.remove('mobile-open');
  DOM.mobileOverlay?.classList.remove('active');
}

// ==================== 知识库面板切换 ====================
function toggleKbPanel() {
  if (window.innerWidth < 769) {
    DOM.kbPanel.classList.toggle('mobile-open');
    DOM.mobileOverlay.classList.toggle('active');
  } else {
    AppState.kbPanelOpen = !AppState.kbPanelOpen;
    DOM.kbPanel.classList.toggle('collapsed', !AppState.kbPanelOpen);
  }
}

// ==================== 初始化 ====================
async function initApp() {
  initTheme();
  initMarked();
  initChatEvents();
  initDocumentEvents();
  loadSessions();
  loadDocuments();

  // 如果屏幕较宽，默认展开知识库
  if (window.innerWidth >= 1200) {
    AppState.kbPanelOpen = true;
    DOM.kbPanel?.classList.remove('collapsed');
  }

  // 检测服务器状态（Demo 模式？）
  await checkServerStatus();

  console.log('🚀 AI 智能客服系统已就绪');
  console.log(`   主题: ${AppState.theme}`);
  console.log(`   API 地址: ${window.location.origin}/api`);
}

async function checkServerStatus() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return;
    const data = await res.json();

    // 判断是否 Demo 模式（API key 为占位符时后端自动降级）
    const badge = document.getElementById('status-badge');
    if (badge && data.llm_provider) {
      // 简单判断: 如果 chroma_chunks 为 0 且无真实 key，则为 Demo
      // 实际 Demo 检测在首次聊天时才准确，这里先显示 online
      badge.style.display = 'inline-block';
      badge.textContent = '🟢 在线';
      badge.className = 'status-badge online';
    }
  } catch (e) {
    const badge = document.getElementById('status-badge');
    if (badge) {
      badge.style.display = 'inline-block';
      badge.textContent = '🔴 离线';
      badge.className = 'status-badge offline';
    }
  }
}

// 配置 marked.js
function initMarked() {
  if (typeof marked === 'undefined') return;
  marked.setOptions({
    breaks: true,
    gfm: true,
  });
  // 配置 highlight.js
  if (typeof hljs !== 'undefined') {
    marked.setOptions({
      highlight: function (code, lang) {
        if (lang && hljs.getLanguage(lang)) {
          return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
      },
    });
  }
}

// ==================== 工具函数导出到全局 ====================
window.showToast = showToast;
window.toggleTheme = toggleTheme;
window.toggleKbPanel = toggleKbPanel;
window.closeMobilePanels = closeMobilePanels;
window.AppState = AppState;
window.DOM = DOM;

// ==================== 事件监听 ====================
document.addEventListener('DOMContentLoaded', initApp);

// 主题切换按钮
document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
document.getElementById('theme-toggle-2')?.addEventListener('click', toggleTheme);

// 移动端菜单
document.getElementById('btn-mobile-menu')?.addEventListener('click', () => {
  DOM.sidebar.classList.toggle('mobile-open');
  DOM.mobileOverlay.classList.toggle('active');
});

document.getElementById('btn-mobile-kb')?.addEventListener('click', toggleKbPanel);

// 知识库面板切换
DOM.btnToggleKb?.addEventListener('click', toggleKbPanel);
DOM.btnCloseKb?.addEventListener('click', toggleKbPanel);
DOM.mobileOverlay?.addEventListener('click', closeMobilePanels);

// 转人工弹窗
DOM.btnEscalate?.addEventListener('click', () => {
  DOM.escalateModal.style.display = 'flex';
});
document.getElementById('btn-escalate-cancel')?.addEventListener('click', () => {
  DOM.escalateModal.style.display = 'none';
});
document.getElementById('btn-escalate-confirm')?.addEventListener('click', () => {
  DOM.escalateModal.style.display = 'none';
  sendEscalateMessage();
});

// 窗口大小变化
window.addEventListener('resize', () => {
  if (window.innerWidth >= 769) {
    DOM.sidebar?.classList.remove('mobile-open');
    DOM.kbPanel?.classList.remove('mobile-open');
    DOM.mobileOverlay?.classList.remove('active');
  }
});
