// 知识库页：拖拽上传 + 文档表格 + 重建索引
import * as api from "../api.js";
import { confirmDialog, esc, fmtSize, fmtTime, toast } from "../ui.js";

const STATUS = {
  ready: '<span class="dot dot-success">已就绪</span>',
  processing: '<span class="dot dot-warning">处理中</span>',
  failed: '<span class="dot dot-danger">失败</span>',
};

export async function render(root) {
  root.innerHTML = `
    <div class="page-head">
      <h2>知识库</h2>
      <div class="actions">
        <button class="btn btn-outline" id="btn-reindex">重建全部索引</button>
      </div>
    </div>
    <div class="dropzone" id="dropzone">
      点击或拖拽文件到此处上传
      <div class="hint">支持 PDF / DOCX / TXT / Markdown / CSV，上传后自动分块并向量化</div>
    </div>
    <input type="file" id="file-input" multiple accept=".pdf,.docx,.txt,.md,.csv" hidden />
    <div class="card" style="overflow:hidden">
      <table class="table">
        <thead><tr><th>文件名</th><th>大小</th><th>分块数</th><th>状态</th><th>上传时间</th><th></th></tr></thead>
        <tbody id="doc-rows"></tbody>
      </table>
    </div>`;

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => uploadFiles([...fileInput.files]));
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("over"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("over"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("over");
    uploadFiles([...e.dataTransfer.files]);
  });

  document.getElementById("btn-reindex").addEventListener("click", async () => {
    if (!(await confirmDialog("重建索引", "将清空向量库并重新解析全部文档（会调用 Embedding API），确定继续？"))) return;
    toast("正在重建索引，请稍候…");
    try {
      const r = await api.reindexDocuments();
      toast(`重建完成：成功 ${r.ok}，失败 ${r.failed}，共 ${r.total_chunks} 个分块`);
      loadDocs();
    } catch (e) { toast(e.message, true); }
  });

  await loadDocs();
}

async function uploadFiles(files) {
  for (const file of files) {
    toast(`正在上传 ${file.name}…`);
    try {
      const doc = await api.uploadDocument(file);
      if (doc.status === "ready") toast(`${file.name} 入库成功（${doc.chunk_count} 个分块）`);
      else toast(`${file.name} 处理失败：${doc.error || "未知错误"}`, true);
    } catch (e) {
      toast(`${file.name} 上传失败：${e.message}`, true);
    }
  }
  loadDocs();
}

async function loadDocs() {
  const docs = await api.listDocuments();
  const tbody = document.getElementById("doc-rows");
  if (!tbody) return;
  if (!docs.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-hint">还没有文档，上传第一个知识库文件吧</div></td></tr>`;
    return;
  }
  tbody.innerHTML = docs.map((d) => `
    <tr>
      <td title="${esc(d.error || "")}">${esc(d.filename)}</td>
      <td>${fmtSize(d.size_bytes)}</td>
      <td>${d.chunk_count}</td>
      <td>${STATUS[d.status] || esc(d.status)}</td>
      <td>${fmtTime(d.created_at)}</td>
      <td style="text-align:right">
        <button class="btn btn-danger btn-sm" data-id="${d.id}" data-name="${esc(d.filename)}">删除</button>
      </td>
    </tr>`).join("");
  tbody.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!(await confirmDialog("删除文档", `将删除「${btn.dataset.name}」及其全部向量分块，确定？`))) return;
      await api.deleteDocument(btn.dataset.id);
      toast("已删除");
      loadDocs();
    });
  });
}
