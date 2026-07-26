// ============================================================
// 管理端 API：JWT 存取 + fetch 封装 + 管理端 WebSocket
// ============================================================

const TOKEN_KEY = "aicc_admin_token";
const USER_KEY = "aicc_admin_user";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const getUser = () => JSON.parse(localStorage.getItem(USER_KEY) || "null");

export function saveAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(path, { ...options, headers });
  if (resp.status === 401) {
    clearAuth();
    location.reload();
    throw new Error("登录已过期");
  }
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

// ---------- 认证 ----------

export const authStatus = () => request("/api/auth/status");
export const login = (email, password) =>
  request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const register = (email, name, password) =>
  request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, name, password }) });
export const changePassword = (oldPwd, newPwd) =>
  request("/api/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
  });

// ---------- 各资源 ----------

export const getStats = () => request("/api/admin/stats");

export const listTickets = (status) =>
  request("/api/tickets" + (status ? `?status=${status}` : ""));
export const ticketMessages = (id) => request(`/api/tickets/${id}/messages`);
export const ticketContext = (id) => request(`/api/tickets/${id}/context`);
export const claimTicket = (id) => request(`/api/tickets/${id}/claim`, { method: "POST" });
export const replyTicket = (id, content) =>
  request(`/api/tickets/${id}/reply`, { method: "POST", body: JSON.stringify({ content }) });
export const resolveTicket = (id) => request(`/api/tickets/${id}/resolve`, { method: "POST" });

export const listDocuments = () => request("/api/documents");
export const deleteDocument = (id) => request(`/api/documents/${id}`, { method: "DELETE" });
export const reindexDocuments = () => request("/api/documents/reindex", { method: "POST" });
export function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/api/documents/upload", { method: "POST", body: form });
}

export const listUsers = () => request("/api/admin/users");
export const createUser = (data) =>
  request("/api/admin/users", { method: "POST", body: JSON.stringify(data) });
export const deleteUser = (id) => request(`/api/admin/users/${id}`, { method: "DELETE" });

export const getSettings = () => request("/api/admin/settings");
export const updateSettings = (data) =>
  request("/api/admin/settings", { method: "PUT", body: JSON.stringify(data) });
export const testSettings = () => request("/api/admin/settings/test", { method: "POST" });

// ---------- 管理端 WS（全局事件广播到 window） ----------

let ws = null;
let wsTimer = null;

export function connectAdminWS() {
  const token = getToken();
  if (!token || ws) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws/admin?token=${token}`);
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      window.dispatchEvent(new CustomEvent("admin-ws", { detail: data }));
    } catch { /* ignore */ }
  };
  wsTimer = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
  }, 25000);
  ws.onclose = () => {
    clearInterval(wsTimer);
    ws = null;
    // 5 秒后自动重连（登录态还在时）
    if (getToken()) setTimeout(connectAdminWS, 5000);
  };
}

export function closeAdminWS() {
  clearInterval(wsTimer);
  ws?.close();
  ws = null;
}
