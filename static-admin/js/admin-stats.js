/**
 * admin-stats.js - 统计仪表盘
 */
async function loadStats() {
  try {
    const res = await Auth.fetch('/api/admin/stats');
    const d = await res.json();
    const grid = document.getElementById('stats-grid');
    grid.innerHTML = [
      { label: '总会话数', value: d.total_conversations, icon: '💬' },
      { label: '待处理工单', value: d.active_escalations, icon: '🎫', color: d.active_escalations > 0 ? '#ef4444' : '' },
      { label: '今日解决', value: d.resolved_today, icon: '✅' },
      { label: '总工单数', value: d.total_tickets, icon: '📋' },
      { label: '知识库文档', value: d.kb_doc_count, icon: '📚' },
      { label: '知识片段', value: d.kb_chunk_count, icon: '🧩' },
      { label: '知识库大小', value: (d.kb_total_size_mb || 0) + ' MB', icon: '💾' },
    ].map(s => `
      <div class="stat-card">
        <div style="font-size:1.5rem;">${s.icon}</div>
        <div class="stat-value" style="${s.color ? 'color:' + s.color : ''}">${s.value}</div>
        <div class="stat-label">${s.label}</div>
      </div>
    `).join('');
  } catch(e) { console.error(e); }
}
