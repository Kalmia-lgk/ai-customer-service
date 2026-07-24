# ============================================================
# 文档摄取模块 - 负责文档加载、分块、Embedding 与入库
# Embedding 通过 app.rag.embedding 走 OpenAI 兼容接口
# （支持 OpenAI / 硅基流动等），chromadb / llama_index 按需加载
# ============================================================
from __future__ import annotations

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.rag.embedding import EmbeddingClient


class DocumentIngestion:
    """
    文档摄取管道
    流程: 读取文件 → 解析为 Document → 分块 → Embedding → 存入 Chroma
    """

    def __init__(self) -> None:
        """初始化 Chroma 客户端和元数据存储"""
        self._available = False
        self._init_error: str = ""

        # 按需导入 chromadb
        try:
            import chromadb as _chromadb
        except ImportError as e:
            self._init_error = f"chromadb 未安装: {e}"
            logger.warning(f"⚠️ {self._init_error}，知识库功能不可用。Demo 模式不受影响。")
            self._init_meta_only()
            return

        # 按需导入 LlamaIndex（仅用于文档解析和分块）
        try:
            from llama_index.core import SimpleDirectoryReader as _Reader
            from llama_index.core.node_parser import SentenceSplitter as _Splitter
            self._SimpleDirectoryReader = _Reader
            self._SentenceSplitter = _Splitter
        except ImportError as e:
            self._init_error = f"llama-index 未安装: {e}"
            logger.warning(f"⚠️ {self._init_error}，知识库功能不可用。Demo 模式不受影响。")
            self._init_meta_only()
            return

        # Embedding 客户端（自动选择硅基流动 / OpenAI）
        self._embedding = EmbeddingClient()
        if not self._embedding.is_available:
            self._init_error = "未配置可用的 Embedding API Key（硅基流动或 OpenAI）"
            logger.warning(f"⚠️ {self._init_error}，知识库功能不可用。")
            self._init_meta_only()
            return

        # 初始化 Chroma 客户端
        try:
            self._chroma_client = _chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
            )
        except TypeError:
            from chromadb.config import Settings as _Cs
            self._chroma_client = _chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=_Cs(anonymized_telemetry=False),
            )

        self._collection = self._chroma_client.get_or_create_collection(
            name="customer_service_knowledge",
            metadata={"description": "AI 客服知识库"},
        )

        self._splitter = self._SentenceSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        self._meta_path = Path(settings.UPLOAD_DIR) / "_documents_meta.json"
        self._ensure_meta_file()
        self._available = True
        logger.info(
            f"✅ Chroma 知识库就绪, collection: {self._collection.name}, "
            f"embedding: {self._embedding.model}"
        )

    def _init_meta_only(self) -> None:
        """仅初始化元数据（降级模式，无向量检索能力）"""
        self._meta_path = Path(settings.UPLOAD_DIR) / "_documents_meta.json"
        self._ensure_meta_file()
        self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    # ==================== 公共接口 ====================

    def index_file(self, file_path: str, filename: str) -> Optional[dict]:
        """索引单个文件，返回文档元数据 dict，失败返回 None"""
        if not self._available:
            logger.warning(f"知识库不可用 ({self._init_error})，跳过索引: {filename}")
            return None

        doc_id = str(uuid.uuid4())
        logger.info(f"开始索引文件: {filename} (id={doc_id})")

        try:
            documents = self._SimpleDirectoryReader(
                input_files=[file_path],
            ).load_data()
            if not documents:
                logger.warning(f"文件解析为空: {filename}")
                return None

            nodes = self._splitter.get_nodes_from_documents(documents)
            logger.info(f"文档分块完成: {filename}, 共 {len(nodes)} 块")

            # 批量 Embedding（每批 32 条，减少 API 调用次数）
            texts = [node.get_content() for node in nodes]
            batch_size = 32
            for start in range(0, len(texts), batch_size):
                batch = texts[start:start + batch_size]
                embeddings = self._embedding.embed_batch(batch)
                if embeddings is None:
                    raise RuntimeError("Embedding 服务不可用")
                ids = [f"{doc_id}_chunk_{start + j}" for j in range(len(batch))]
                metadatas = [{
                    "doc_id": doc_id, "filename": filename,
                    "chunk_index": start + j, "total_chunks": len(texts),
                } for j in range(len(batch))]
                self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=batch,
                    metadatas=metadatas,
                )

            file_size = os.path.getsize(file_path)
            meta = {
                "doc_id": doc_id, "filename": filename,
                "file_type": Path(filename).suffix.lower(),
                "file_size": file_size, "chunk_count": len(nodes),
                "uploaded_at": datetime.now().isoformat(), "status": "active",
            }
            self._save_meta(meta)
            logger.info(f"文件索引完成: {filename} → {len(nodes)} 向量块")
            return meta

        except Exception as e:
            logger.error(f"文件索引失败 {filename}: {e}")
            meta = {
                "doc_id": doc_id, "filename": filename,
                "file_type": Path(filename).suffix.lower(),
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "chunk_count": 0, "uploaded_at": datetime.now().isoformat(),
                "status": "error",
            }
            self._save_meta(meta)
            return meta

    def delete_document(self, doc_id: str) -> bool:
        if not self._available:
            self._remove_meta(doc_id)
            return True
        try:
            results = self._collection.get(where={"doc_id": doc_id})
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"已从 Chroma 删除 {len(results['ids'])} 块: {doc_id}")
            self._remove_meta(doc_id)
            return True
        except Exception as e:
            logger.error(f"删除文档失败 {doc_id}: {e}")
            return False

    def rebuild_index(self) -> dict:
        logger.info("开始重建全量索引...")
        if self._available:
            try:
                self._chroma_client.delete_collection("customer_service_knowledge")
                self._collection = self._chroma_client.get_or_create_collection(
                    name="customer_service_knowledge",
                    metadata={"description": "AI 客服知识库"},
                )
            except Exception as e:
                logger.warning(f"清空 collection 失败: {e}")
        self._write_meta_file([])

        upload_dir = Path(settings.UPLOAD_DIR)
        supported_exts = {".pdf", ".docx", ".txt", ".md", ".csv"}
        doc_count = 0
        total_chunks = 0

        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                meta = self.index_file(str(file_path), file_path.name)
                if meta and meta["status"] == "active":
                    doc_count += 1
                    total_chunks += meta["chunk_count"]

        logger.info(f"重建索引完成: {doc_count} 个文档, {total_chunks} 个向量块")
        return {"doc_count": doc_count, "total_chunks": total_chunks}

    def get_all_documents(self) -> list[dict]:
        return self._read_meta_file()

    def get_document(self, doc_id: str) -> Optional[dict]:
        for m in self._read_meta_file():
            if m["doc_id"] == doc_id:
                return m
        return None

    # ==================== 元数据持久化 ====================

    def _ensure_meta_file(self) -> None:
        if not self._meta_path.exists():
            self._write_meta_file([])

    def _read_meta_file(self) -> list[dict]:
        try:
            with open(self._meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_meta_file(self, data: list[dict]) -> None:
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_meta(self, meta: dict) -> None:
        metas = self._read_meta_file()
        for i, m in enumerate(metas):
            if m["doc_id"] == meta["doc_id"]:
                metas[i] = meta
                self._write_meta_file(metas)
                return
        metas.append(meta)
        self._write_meta_file(metas)

    def _remove_meta(self, doc_id: str) -> None:
        metas = [m for m in self._read_meta_file() if m["doc_id"] != doc_id]
        self._write_meta_file(metas)
