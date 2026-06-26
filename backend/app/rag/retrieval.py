# ============================================================
# 文档检索模块 - 负责语义搜索与上下文组装
# 所有重型依赖 (chromadb, llama_index) 均为按需加载
# ============================================================
from __future__ import annotations

from typing import Optional, Tuple

from loguru import logger

from app.core.config import settings


class DocumentRetrieval:
    """
    知识库检索器
    查询 → Embedding → Chroma 向量搜索 → 返回相关文档片段

    注意: chromadb / llama_index 在首次实例化时按需导入，
    Demo 模式下不会触发导入。
    """

    def __init__(self) -> None:
        self._available = False
        self._top_k = settings.RETRIEVAL_TOP_K

        # 按需导入 chromadb
        try:
            import chromadb as _chromadb
            self._chromadb = _chromadb
        except ImportError as e:
            logger.warning(f"⚠️ chromadb 未安装 ({e})，检索功能不可用。Demo 模式不受影响。")
            return

        # 按需导入 embedding
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding as _Embedding
            self._OpenAIEmbedding = _Embedding
        except ImportError as e:
            logger.warning(f"⚠️ llama-index 未安装 ({e})，检索功能不可用。Demo 模式不受影响。")
            return

        # 初始化 Chroma
        try:
            self._chroma_client = self._chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
            )
        except TypeError:
            from chromadb.config import Settings as _Cs
            self._chroma_client = self._chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=_Cs(anonymized_telemetry=False),
            )

        self._collection = self._chroma_client.get_or_create_collection(
            name="customer_service_knowledge",
        )
        self._embedding = self._OpenAIEmbedding(
            model=settings.OPENAI_EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )
        self._available = True
        logger.info(f"✅ 检索器就绪, top_k={self._top_k}")

    @property
    def is_available(self) -> bool:
        return self._available

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: float = 0.3,
    ) -> list[dict]:
        """
        向量检索，返回相关文档片段列表
        """
        if not self._available:
            return []

        k = top_k or self._top_k
        try:
            query_embedding = self._embedding.get_query_embedding(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )

            retrieved: list[dict] = []
            if not results["ids"] or not results["ids"][0]:
                return retrieved

            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = 1.0 / (1.0 + distance)
                if score < score_threshold:
                    continue
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                document_text = results["documents"][0][i] if results.get("documents") else ""
                retrieved.append({
                    "document_name": metadata.get("filename", "未知文档"),
                    "snippet": document_text[:300] + "..." if len(document_text) > 300 else document_text,
                    "full_text": document_text,
                    "score": round(score, 4),
                    "chunk_index": metadata.get("chunk_index", 0),
                })

            logger.info(f"检索完成: '{query[:30]}...' → {len(retrieved)} 条")
            return retrieved
        except Exception as e:
            logger.error(f"检索出错: {e}")
            return []

    def build_context(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> Tuple[str, list[dict]]:
        """检索并构建上下文文本块 + 来源引用"""
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return "", []

        context_parts: list[str] = []
        sources: list[dict] = []
        for i, r in enumerate(results):
            context_parts.append(
                f"【参考资料 {i + 1}】来源: {r['document_name']}\n{r['full_text']}"
            )
            sources.append({
                "document_name": r["document_name"],
                "snippet": r["snippet"],
                "score": r["score"],
            })

        return "\n\n---\n\n".join(context_parts), sources

    def get_collection_stats(self) -> dict:
        if not self._available:
            return {"total_chunks": 0}
        try:
            return {"total_chunks": self._collection.count()}
        except Exception:
            return {"total_chunks": 0}
