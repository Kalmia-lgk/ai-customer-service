// ============================================================
// 管理端入口：登录流程 + hash 路由 + 主题
// ============================================================
import * as api from "./api.js";
import { toast } from "./ui.js";
import * as overview from "./pages/overview.js";
import * as tickets from "./pages/tickets.js";
import * as knowledge from "./pages/knowledge.js";
import * as users from "./pages/users.js";
import * as settings from "./pages/settings.js";

const PAGES = { overview, tickets, knowledge, users, settings };

const loginView = document.getElementById("login-view");
const appView = document.getElementById("app-view");
const pageEl = document.getElementById("page");

// ---------- 主题 ----------

document.getElementById("btn-theme").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("aicc_theme", next);
});

// ---------- 登录 / 初始化注册 ----------

const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
let registerMode = false;

async function setupLoginView() {
  try {
    const { registration_open } = await api.authStatus();
    registerMode = registration_open;
  } catch { registerMode = false; }
  document.getElementById("field-name").hidden = !registerMode;
  document.getElementById("login-subtitle").textContent = registerMode
    ? "系统初始化：注册首个账号（将成为超级管理员）"
    : "使用管理员账号登录";
  document.getElementById("login-submit").textContent = registerMode ? "注册并登录" : "登 录";
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    const result = registerMode
      ? await api.register(email, document.getElementById("login-name").value.trim() || email.split("@")[0], password)
      : await api.login(email, password);
    api.saveAuth(result.token, result.user);
    enterApp();
  } catch (err) {
    loginError.textContent = err.message;
  }
});

// ---------- 退出 ----------

document.getElementById("btn-logout").addEventListener("click", () => {
  api.clearAuth();
  api.closeAdminWS();
  location.hash = "";
  location.reload();
});

// ---------- 路由 ----------

let currentPage = null;

async function route() {
  const name = (location.hash.replace(/^#\//, "") || "overview").split("/")[0];
  const page = PAGES[name] || PAGES.overview;
  document.querySelectorAll("#nav-menu a").forEach((a) =>
    a.classList.toggle("active", a.dataset.page === (PAGES[name] ? name : "overview"))
  );
  currentPage?.destroy?.();
  currentPage = page;
  pageEl.innerHTML = "";
  try {
    await page.render(pageEl);
  } catch (e) {
    toast(e.message, true);
  }
}

window.addEventListener("hashchange", route);

// ---------- 全局 WS 提示（新工单） ----------

window.addEventListener("admin-ws", (e) => {
  const data = e.detail;
  if (data.type === "new_ticket") toast("收到新的人工工单");
});

// ---------- 启动 ----------

function enterApp() {
  const user = api.getUser();
  loginView.hidden = true;
  appView.hidden = false;
  document.getElementById("nav-user-name").textContent = user?.name || "";
  document.getElementById("nav-user-role").textContent =
    user?.role === "super_admin" ? "超级管理员" : "客服";
  // 非超管隐藏「用户」入口（后端同样有权限校验，这里只是导航层面）
  document.querySelector('#nav-menu a[data-page="users"]').style.display =
    user?.role === "super_admin" ? "" : "none";
  api.connectAdminWS();
  route();
}

if (api.getToken()) {
  enterApp();
} else {
  loginView.hidden = false;
  setupLoginView();
}
