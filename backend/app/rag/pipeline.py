"""RAG 管道：解析 → 分块 → Embedding → 入 Chroma；以及语义检索。"""
from __future__ import annotations

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from sqlmodel import Session

from app.config import UPLOAD_DIR, settings
from app.llm import get_gateway
from app.models import KnowledgeDoc
from app.rag.loader import parse_file
from app.rag.store import get_store

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.CHUNK_SIZE,
    chunk_overlap=settings.CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],  # 中文友好
)

EMBED_BATCH = 16


async def ingest_document(db: Session, doc: KnowledgeDoc) -> KnowledgeDoc:
    """解析并向量化一个已保存到 uploads/ 的文档，更新其状态。"""
    path = UPLOAD_DIR / doc.stored_name
    try:
        text = parse_file(path)
        chunks = [c.strip() for c in _splitter.split_text(text) if c.strip()]
        if not chunks:
            raise ValueError("文档解析后没有可用文本（可能是扫描版 PDF 或空文件）")

        gateway = get_gateway()
        embeddings: list[list[float]] = []
        for i in range(0, len(chunks), EMBED_BATCH):
            embeddings.extend(await gateway.embed(chunks[i : i + EMBED_BATCH]))

        get_store().add_chunks(doc.id, doc.filename, chunks, embeddings)
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        doc.error = None
        logger.info(f"文档入库完成: {doc.filename} -> {len(chunks)} chunks")
    except Exception as e:
        doc.status = "failed"
        doc.error = str(e)[:500]
        logger.error(f"文档入库失败: {doc.filename}: {e}")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, doc: KnowledgeDoc) -> None:
    get_store().delete_doc(doc.id)
    path = UPLOAD_DIR / doc.stored_name
    path.unlink(missing_ok=True)
    db.delete(doc)
    db.commit()


async def search(query: str, top_k: int | None = None) -> list[dict]:
    """语义检索：query → embedding → 近邻查询。"""
    gateway = get_gateway()
    if not gateway.is_configured:
        return []
    embedding = (await gateway.embed([query]))[0]
    return get_store().search(embedding, top_k)
