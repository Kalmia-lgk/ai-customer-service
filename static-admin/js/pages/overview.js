// 概览页：统计卡片 + 近 7 日会话量纯 CSS 柱状图
import * as api from "../api.js";
import { esc } from "../ui.js";

export async function render(root) {
  root.innerHTML = `<div class="page-head"><h2>概览</h2></div><div id="overview-body">加载中…</div>`;
  const s = await api.getStats();
  const t = s.tickets;

  const cards = [
    { label: "累计会话", value: s.sessions },
    { label: "累计消息", value: s.messages },
    { label: "知识库文档", value: s.documents, sub: `${s.chunks} 个向量分块` },
    { label: "待接入工单", value: t.waiting },
    { label: "处理中工单", value: t.in_progress },
    { label: "已解决工单", value: t.resolved },
  ];

  const max = Math.max(1, ...s.daily_sessions.map((d) => d.count));
  const bars = s.daily_sessions.map((d) => `
    <div class="bar-col">
      <span class="bar-value">${d.count}</span>
      <div class="bar" style="height:${Math.max(2, (d.count / max) * 100)}%"></div>
      <span class="bar-label">${esc(d.date)}</span>
    </div>`).join("");

  document.getElementById("overview-body").innerHTML = `
    <div class="stat-grid">
      ${cards.map((c) => `
        <div class="card stat-card">
          <div class="label">${c.label}</div>
          <div class="value">${c.value}</div>
          ${c.sub ? `<div class="sub">${c.sub}</div>` : ""}
        </div>`).join("")}
    </div>
    <div class="card chart-card">
      <h3>近 7 日会话量</h3>
      <div class="bar-chart">${bars}</div>
    </div>`;
}
