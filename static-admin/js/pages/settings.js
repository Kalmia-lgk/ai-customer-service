// 设置页：LLM 四元组（保存即热生效）+ 修改密码
import * as api from "../api.js";
import { esc, toast } from "../ui.js";

export async function render(root) {
  const me = api.getUser();
  const isSuper = me?.role === "super_admin";

  root.innerHTML = `
    <div class="page-head"><h2>设置</h2></div>
    <div class="settings-grid">
      <div class="card settings-card" ${isSuper ? "" : "hidden"}>
        <h3>LLM 接入配置</h3>
        <p class="desc">OpenAI 兼容接口（硅基流动 / OpenAI / DeepSeek 官方等），保存后立即生效，无需重启。</p>
        <div class="field"><label>Base URL</label><input class="input" id="s-base" placeholder="https://api.siliconflow.cn/v1" /></div>
        <div class="field"><label>API Key</label><input class="input" id="s-key" type="password" placeholder="sk-…" /></div>
        <div class="field"><label>对话模型</label><input class="input" id="s-chat" placeholder="deepseek-ai/DeepSeek-V4-Flash" /></div>
        <div class="field"><label>意图分类模型（可选，建议填快而便宜的小模型）</label><input class="input" id="s-intent" placeholder="留空则复用对话模型" /></div>
        <div class="field"><label>Embedding 模型</label><input class="input" id="s-embed" placeholder="BAAI/bge-m3" /></div>
        <div class="settings-actions">
          <button class="btn btn-primary" id="btn-save-llm">保存并生效</button>
          <button class="btn btn-outline" id="btn-test-llm">测试连接</button>
        </div>
      </div>
      <div class="card settings-card">
        <h3>修改密码</h3>
        <p class="desc">当前账号：${esc(me?.email || "")}</p>
        <div class="field"><label>原密码</label><input class="input" id="p-old" type="password" /></div>
        <div class="field"><label>新密码（至少 6 位）</label><input class="input" id="p-new" type="password" /></div>
        <div class="settings-actions">
          <button class="btn btn-primary" id="btn-save-pwd">修改密码</button>
        </div>
      </div>
    </div>`;

  if (isSuper) {
    try {
      const cfg = await api.getSettings();
      document.getElementById("s-base").value = cfg.llm_base_url || "";
      document.getElementById("s-key").value = cfg.llm_api_key || "";
      document.getElementById("s-chat").value = cfg.llm_chat_model || "";
      document.getElementById("s-intent").value = cfg.llm_intent_model || "";
      document.getElementById("s-embed").value = cfg.llm_embedding_model || "";
    } catch (e) { toast(e.message, true); }

    document.getElementById("btn-save-llm").addEventListener("click", async () => {
      try {
        await api.updateSettings({
          llm_base_url: document.getElementById("s-base").value.trim(),
          llm_api_key: document.getElementById("s-key").value.trim(),
          llm_chat_model: document.getElementById("s-chat").value.trim(),
          llm_intent_model: document.getElementById("s-intent").value.trim(),
          llm_embedding_model: document.getElementById("s-embed").value.trim(),
        });
        toast("已保存，下一条对话即用新配置");
      } catch (e) { toast(e.message, true); }
    });

    document.getElementById("btn-test-llm").addEventListener("click", async () => {
      const btn = document.getElementById("btn-test-llm");
      btn.disabled = true;
      btn.textContent = "测试中…";
      try {
        const r = await api.testSettings();
        toast(`连接成功：${r.reply || "OK"}`);
      } catch (e) {
        toast(e.message, true);
      } finally {
        btn.disabled = false;
        btn.textContent = "测试连接";
      }
    });
  }

  document.getElementById("btn-save-pwd").addEventListener("click", async () => {
    const oldPwd = document.getElementById("p-old").value;
    const newPwd = document.getElementById("p-new").value;
    if (newPwd.length < 6) { toast("新密码至少 6 位", true); return; }
    try {
      await api.changePassword(oldPwd, newPwd);
      toast("密码已修改");
      document.getElementById("p-old").value = "";
      document.getElementById("p-new").value = "";
    } catch (e) { toast(e.message, true); }
  });
}
