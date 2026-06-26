/**
 * ============================================================
 * documents.js - 知识库管理：文件上传、文档列表、重建索引
 * ============================================================
 */

// ==================== 文档事件初始化 ====================
function initDocumentEvents() {
  const dropzone = DOM.uploadDropzone;
  const fileInput = DOM.fileInput;
  const btnReindex = DOM.btnReindex;

  // 点击上传区域
  dropzone?.addEventListener('click', () => fileInput?.click());

  // 文件选择
  fileInput?.addEventListener('change', (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      uploadFiles(files);
      fileInput.value = ''; // 重置以允许重复上传同一文件
    }
  });

  // 拖拽上传
  dropzone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  dropzone?.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-over');
  });

  dropzone?.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadFiles(files);
    }
  });

  // 重建索引
  btnReindex?.addEventListener('click', reindexDocuments);
}

// ==================== 文件上传 ====================
async function uploadFiles(files) {
  const allowedExts = ['.pdf', '.docx', '.txt', '.md', '.csv'];
  const fileList = Array.from(files);

  // 客户端预校验
  for (const file of fileList) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExts.includes(ext)) {
      showToast(`不支持的文件类型: ${file.name}`, 'error');
      return;
    }
    const maxSize = 20 * 1024 * 1024; // 20MB
    if (file.size > maxSize) {
      showToast(`文件过大: ${file.name} (最大 20MB)`, 'error');
      return;
    }
  }

  // 逐一上传
  let successCount = 0;
  let failCount = 0;

  for (const file of fileList) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      showToast(`正在上传: ${file.name}...`, 'info', 2000);

      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '上传失败');
      }

      const data = await res.json();
      if (data.success) {
        successCount++;
        showToast(`✅ ${file.name} 上传成功`, 'success');
      } else {
        failCount++;
        showToast(`⚠️ ${file.name}: ${data.message}`, 'error');
      }
    } catch (error) {
      failCount++;
      showToast(`❌ ${file.name}: ${error.message}`, 'error');
    }
  }

  // 刷新文档列表
  await loadDocuments();

  if (successCount > 0) {
    showToast(`成功上传 ${successCount} 个文件${failCount > 0 ? `，${failCount} 个失败` : ''}`, 'success');
  }
}

// ==================== 文档列表 ====================
async function loadDocuments() {
  try {
    const res = await fetch('/api/documents');
    if (!res.ok) throw new Error('加载失败');
    const data = await res.json();

    const docs = data.documents || [];
    renderDocumentList(docs);

    // 加载统计
    await loadStats();
  } catch (e) {
    console.error('加载文档列表失败:', e);
  }
}

function renderDocumentList(docs) {
  const list = DOM.docList;
  const emptyState = DOM.docEmptyState;

  if (!list) return;

  // 过滤掉错误状态的文档前的空状态
  const activeDocs = docs.filter(d => d.status !== 'error');

  if (docs.length === 0) {
    list.innerHTML = '';
    list.appendChild(createEmptyState());
    return;
  }

  // 渲染文档列表
  let html = '';
  docs.forEach(doc => {
    const icon = getFileIcon(doc.file_type || doc.filename);
    const size = formatFileSize(doc.file_size || 0);
    const time = formatTime(doc.uploaded_at);
    const statusBadge = doc.status === 'error'
      ? '<span style="color:#ef4444;font-size:0.65rem;">⚠️ 索引失败</span>'
      : doc.status === 'processing'
        ? '<span style="color:#f59e0b;font-size:0.65rem;">⏳ 处理中</span>'
        : '';

    html += `
      <div class="doc-item" data-doc-id="${escapeHtml(doc.doc_id)}">
        <span class="doc-icon">${icon}</span>
        <div class="doc-info">
          <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
          <div class="doc-meta">${size} · ${doc.chunk_count || 0} 片段 · ${time} ${statusBadge}</div>
        </div>
        <button class="doc-delete" onclick="deleteDocument(event, '${escapeHtml(doc.doc_id)}', '${escapeHtml(doc.filename)}')" title="删除文档">
          🗑️
        </button>
      </div>
    `;
  });

  list.innerHTML = html;
}

function createEmptyState() {
  DOM.docEmptyState.style.display = 'flex';
  return DOM.docEmptyState;
}

async function deleteDocument(event, docId, filename) {
  event.stopPropagation();

  if (!confirm(`确定删除文档 "${filename}" 吗？\n此操作将同时删除向量数据和原始文件。`)) return;

  try {
    const res = await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('删除失败');

    showToast(`已删除: ${filename}`, 'success');
    await loadDocuments();
  } catch (e) {
    showToast(`删除失败: ${e.message}`, 'error');
  }
}

// ==================== 重建索引 ====================
async function reindexDocuments() {
  if (!confirm('确定要重建所有索引吗？\n\n这将清空当前向量数据库，然后重新索引 uploads 目录下的所有文件。操作期间可能暂时无法检索。')) return;

  try {
    showToast('正在重建索引，请稍候...', 'info', 5000);

    const res = await fetch('/api/documents/reindex', { method: 'POST' });
    if (!res.ok) throw new Error('重建失败');

    const data = await res.json();
    showToast(`索引重建完成！${data.doc_count} 个文档，${data.total_chunks} 个片段`, 'success');
    await loadDocuments();
  } catch (e) {
    showToast(`重建索引失败: ${e.message}`, 'error');
  }
}

// ==================== 统计信息 ====================
async function loadStats() {
  try {
    const res = await fetch('/api/documents/stats/summary');
    if (!res.ok) return;
    const stats = await res.json();

    AppState.kbStats = stats;

    const statDocs = document.getElementById('stat-docs');
    const statChunks = document.getElementById('stat-chunks');
    if (statDocs) statDocs.textContent = stats.document_count || 0;
    if (statChunks) statChunks.textContent = stats.total_chunks || 0;
  } catch (e) {
    console.error('加载统计失败:', e);
  }
}

// ==================== 工具函数 ====================
function getFileIcon(filename) {
  const name = (filename || '').toLowerCase();
  if (name.endsWith('.pdf')) return '📕';
  if (name.endsWith('.docx')) return '📘';
  if (name.endsWith('.txt')) return '📄';
  if (name.endsWith('.md')) return '📝';
  if (name.endsWith('.csv')) return '📊';
  return '📎';
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// 导出到全局
window.uploadFiles = uploadFiles;
window.loadDocuments = loadDocuments;
window.deleteDocument = deleteDocument;
window.reindexDocuments = reindexDocuments;
window.initDocumentEvents = initDocumentEvents;
