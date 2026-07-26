// ============================================================
// 通用 UI 组件：toast / 确认弹层 / 转义 / 时间格式化 / 状态点
// ============================================================

export function toast(message, isError = false) {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " toast-error" : "");
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

export function esc(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

export function confirmDialog(title, message) {
  return new Promise((resolve) => {
    const root = document.getElementById("modal-root");
    const mask = document.createElement("div");
    mask.className = "modal-mask";
    mask.innerHTML = `
      <div class="modal">
        <h3>${esc(title)}</h3>
        <p style="color:var(--text-2);font-size:14px">${esc(message)}</p>
        <div class="modal-actions">
          <button class="btn btn-outline" data-act="cancel">取消</button>
          <button class="btn btn-primary" data-act="ok">确定</button>
        </div>
      </div>`;
    const done = (val) => { mask.remove(); resolve(val); };
    mask.querySelector('[data-act="cancel"]').onclick = () => done(false);
    mask.querySelector('[data-act="ok"]').onclick = () => done(true);
    mask.onclick = (e) => { if (e.target === mask) done(false); };
    root.appendChild(mask);
  });
}

/** 简单表单弹层：fields = [{key,label,type,placeholder,options}] */
export function formDialog(title, fields) {
  return new Promise((resolve) => {
    const root = document.getElementById("modal-root");
    const mask = document.createElement("div");
    mask.className = "modal-mask";
    const fieldHtml = fields.map((f) => {
      if (f.type === "select") {
        const opts = f.options.map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("");
        return `<div class="field"><label>${esc(f.label)}</label><select class="select" data-key="${f.key}">${opts}</select></div>`;
      }
      return `<div class="field"><label>${esc(f.label)}</label>
        <input class="input" data-key="${f.key}" type="${f.type || "text"}" placeholder="${esc(f.placeholder || "")}" /></div>`;
    }).join("");
    mask.innerHTML = `
      <div class="modal">
        <h3>${esc(title)}</h3>
        ${fieldHtml}
        <div class="modal-actions">
          <button class="btn btn-outline" data-act="cancel">取消</button>
          <button class="btn btn-primary" data-act="ok">确定</button>
        </div>
      </div>`;
    const done = (val) => { mask.remove(); resolve(val); };
    mask.querySelector('[data-act="cancel"]').onclick = () => done(null);
    mask.querySelector('[data-act="ok"]').onclick = () => {
      const values = {};
      mask.querySelectorAll("[data-key]").forEach((el) => { values[el.dataset.key] = el.value.trim(); });
      done(values);
    };
    root.appendChild(mask);
    mask.querySelector("[data-key]")?.focus();
  });
}

export function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export const TICKET_STATUS = {
  waiting: { label: "待接入", dot: "dot-warning" },
  in_progress: { label: "处理中", dot: "dot-accent" },
  resolved: { label: "已解决", dot: "dot-success" },
};

export function statusDot(status) {
  const s = TICKET_STATUS[status] || { label: status, dot: "" };
  return `<span class="dot ${s.dot}">${s.label}</span>`;
}
