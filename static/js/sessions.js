// ============================================================
// 会话侧栏：列表渲染 / 切换 / 删除（数据在服务端 SQLite）
// ============================================================
import * as api from "./api.js";

const listEl = document.getElementById("session-list");
const titleEl = document.getElementById("topbar-title");

let currentId = null;
let onSelect = () => {};

export function currentSessionId() {
  return currentId;
}

export function setCurrentSession(id, title) {
  currentId = id;
  titleEl.textContent = title || "新会话";
  [...listEl.children].forEach((el) =>
    el.classList.toggle("active", el.dataset.id === id)
  );
}

export function bindSelect(fn) {
  onSelect = fn;
}

export async function refresh() {
  let sessions = [];
  try {
    sessions = await api.listSessions();
  } catch { /* 服务未就绪时静默 */ }
  listEl.innerHTML = "";
  for (const s of sessions) {
    const el = document.createElement("div");
    el.className = "session-item" + (s.id === currentId ? " active" : "");
    el.dataset.id = s.id;
    el.innerHTML = `
      <span class="title"></span>
      <button class="del" title="删除会话">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4h8v2m1 0v14a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V6"/></svg>
      </button>`;
    el.querySelector(".title").textContent = s.title;
    el.addEventListener("click", () => onSelect(s));
    el.querySelector(".del").addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await api.deleteSession(s.id);
        if (s.id === currentId) onSelect(null);
      } catch (err) {
        console.error("删除会话失败:", err);
        alert(`删除会话失败：${err.message}`);
      }
      refresh();
    });
    listEl.appendChild(el);
  }
}
