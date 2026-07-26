"""ChromaDB 封装：全局单例客户端 + 余弦相似度检索。"""
from __future__ import annotations

import chromadb
from loguru import logger

from app.config import CHROMA_DIR, settings

COLLECTION = "knowledge"


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine"},  # 余弦距离，分数可解释
        )
        logger.info(f"VectorStore ready: {self.chunk_count()} chunks")

    def chunk_count(self) -> int:
        return self._collection.count()

    def add_chunks(
        self,
        doc_id: str,
        filename: str,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        self._collection.add(
            ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {"doc_id": doc_id, "filename": filename, "chunk_index": i}
                for i in range(len(chunks))
            ],
        )

    def delete_doc(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def reset(self) -> None:
        """删除并重建 collection（重建索引用）。"""
        self._client.delete_collection(COLLECTION)
        self._collection = self._client.get_or_create_collection(
            COLLECTION, metadata={"hnsw:space": "cosine"},
        )

    def search(self, query_embedding: list[float], top_k: int | None = None) -> list[dict]:
        """返回 [{text, filename, doc_id, score}]，score = 1 - cosine_distance。"""
        if self.chunk_count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k or settings.RETRIEVAL_TOP_K, self.chunk_count()),
        )
        hits: list[dict] = []
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        ):
            score = 1.0 - distance
            if score < settings.RETRIEVAL_MIN_SCORE:
                continue
            hits.append({
                "text": text,
                "filename": meta.get("filename", ""),
                "doc_id": meta.get("doc_id", ""),
                "score": round(score, 3),
            })
        return hits


# 全局单例
store: VectorStore | None = None


def get_store() -> VectorStore:
    global store
    if store is None:
        store = VectorStore()
    return store
