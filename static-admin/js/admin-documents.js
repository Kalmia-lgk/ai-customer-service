/**
 * admin-documents.js - 知识库管理（从客户界面移植到管理端）
 */
const dropzone = document.getElementById('upload-dropzone');
const fileInput = document.getElementById('file-input');

dropzone?.addEventListener('click', () => fileInput?.click());
fileInput?.addEventListener('change', (e) => {
  if (e.target.files.length) uploadFiles(e.target.files);
  fileInput.value = '';
});
dropzone?.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone?.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone?.addEventListener('drop', (e) => {
  e.preventDefault(); dropzone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
});
document.getElementById('btn-reindex')?.addEventListener('click', reindexDocs);

async function uploadFiles(files) {
  const allowed = ['.pdf','.docx','.txt','.md','.csv'];
  for (const f of Array.from(files)) {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    if (!allowed.includes(ext)) { alert(`不支持的文件类型: ${f.name}`); return; }
  }
  for (const f of Array.from(files)) {
    const fd = new FormData(); fd.append('file', f);
    try {
      const res = await Auth.fetch('/api/documents/upload', { method: 'POST', body: fd });
      if (!res.ok) throw new Error((await res.json()).detail);
      showAdminToast(`✅ ${f.name} 上传成功`, 'success');
    } catch (e) { showAdminToast(`❌ ${f.name}: ${e.message}`, 'error'); }
  }
  loadDocuments();
}

async function loadDocuments() {
  try {
    const res = await Auth.fetch('/api/documents');
    const data = await res.json();
    const docs = data.documents || [];
    const list = document.getElementById('doc-list');
    if (!docs.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-text">暂无文档</div></div>';
    } else {
      list.innerHTML = docs.map(d => `
        <div class="doc-item">
          <span class="doc-icon">${getIcon(d.filename)}</span>
          <div class="doc-info">
            <div class="doc-name" title="${escapeHtml(d.filename)}">${escapeHtml(d.filename)}</div>
            <div class="doc-meta">${formatSize(d.file_size)} · ${d.chunk_count||0} 片段 · ${formatTime(d.uploaded_at)}</div>
          </div>
          <button class="doc-delete" onclick="delDoc(event,'${d.doc_id}','${escapeHtml(d.filename)}')">🗑️</button>
        </div>
      `).join('');
    }
    // Stats
    try {
      const r2 = await Auth.fetch('/api/documents/stats/summary');
      const s = await r2.json();
      document.getElementById('stat-docs').textContent = s.document_count || 0;
      document.getElementById('stat-chunks').textContent = s.total_chunks || 0;
    } catch(e){}
  } catch(e) { console.error(e); }
}

async function delDoc(e, docId, name) {
  e.stopPropagation();
  if (!confirm(`确定删除 "${name}" 吗？`)) return;
  try {
    await Auth.fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    showAdminToast('已删除', 'success');
    loadDocuments();
  } catch(e) { showAdminToast('删除失败', 'error'); }
}

async function reindexDocs() {
  if (!confirm('确定重建索引？将清空并重新索引所有文档。')) return;
  try {
    const res = await Auth.fetch('/api/documents/reindex', { method: 'POST' });
    const d = await res.json();
    showAdminToast(`重建完成: ${d.doc_count} 个文档, ${d.total_chunks} 片段`, 'success');
    loadDocuments();
  } catch(e) { showAdminToast('重建失败', 'error'); }
}

function getIcon(n) { const x=(n||'').toLowerCase(); if(x.endsWith('.pdf'))return'📕'; if(x.endsWith('.docx'))return'📘'; if(x.endsWith('.txt'))return'📄'; if(x.endsWith('.md'))return'📝'; if(x.endsWith('.csv'))return'📊'; return'📎'; }
function formatSize(b) { if(!b)return'0 B'; const k=1024; const s=['B','KB','MB']; const i=Math.floor(Math.log(b)/Math.log(k)); return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]; }
function escapeHtml(s) { const d=document.createElement('div'); d.textContent=s||''; return d.innerHTML; }
function formatTime(iso) { if(!iso)return''; const d=new Date(iso); return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`; }
function showAdminToast(msg,type) {
  const d=document.createElement('div');
  d.style.cssText=`position:fixed;top:1rem;right:1rem;z-index:9999;padding:0.6rem 1rem;border-radius:8px;font-size:0.8rem;font-weight:500;${type==='success'?'background:#d1fae5;color:#065f46':'background:#fee2e2;color:#991b1b'}`;
  d.textContent=msg; document.body.appendChild(d);
  setTimeout(()=>{d.style.opacity='0';d.style.transition='opacity 0.3s';setTimeout(()=>d.remove(),300);},3000);
}
