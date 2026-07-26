// 用户页：列表 + 创建 / 删除（仅超管可操作，后端双重校验）
import * as api from "../api.js";
import { confirmDialog, esc, fmtTime, formDialog, toast } from "../ui.js";

const ROLE_LABEL = { super_admin: "超级管理员", agent: "客服" };

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h2>用户</h2>
      <div class="actions"><button class="btn btn-primary" id="btn-add-user">新建账号</button></div>
    </div>
    <div class="card" style="overflow:hidden">
      <table class="table">
        <thead><tr><th>姓名</th><th>邮箱</th><th>角色</th><th>创建时间</th><th></th></tr></thead>
        <tbody id="user-rows"></tbody>
      </table>
    </div>`;

  document.getElementById("btn-add-user").addEventListener("click", async () => {
    const values = await formDialog("新建账号", [
      { key: "name", label: "姓名" },
      { key: "email", label: "邮箱", type: "email" },
      { key: "password", label: "初始密码（至少 6 位）", type: "password" },
      { key: "role", label: "角色", type: "select",
        options: [{ value: "agent", label: "客服" }, { value: "super_admin", label: "超级管理员" }] },
    ]);
    if (!values) return;
    try {
      await api.createUser(values);
      toast("账号已创建");
      loadUsers();
    } catch (e) { toast(e.message, true); }
  });

  await loadUsers();
}

async function loadUsers() {
  const users = await api.listUsers();
  const me = api.getUser();
  const tbody = document.getElementById("user-rows");
  if (!tbody) return;
  tbody.innerHTML = users.map((u) => `
    <tr>
      <td>${esc(u.name)}</td>
      <td>${esc(u.email)}</td>
      <td><span class="badge ${u.role === "super_admin" ? "badge-accent" : ""}">${ROLE_LABEL[u.role] || u.role}</span></td>
      <td>${fmtTime(u.created_at)}</td>
      <td style="text-align:right">
        ${u.id === me?.id ? '<span class="badge">当前账号</span>'
          : `<button class="btn btn-danger btn-sm" data-id="${u.id}" data-name="${esc(u.name)}">删除</button>`}
      </td>
    </tr>`).join("");
  tbody.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!(await confirmDialog("删除账号", `确定删除「${btn.dataset.name}」？`))) return;
      try {
        await api.deleteUser(btn.dataset.id);
        toast("已删除");
        loadUsers();
      } catch (e) { toast(e.message, true); }
    });
  });
}
