"""知识库文档路由（需登录）：上传 / 列表 / 删除 / 重建索引。"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from loguru import logger
from sqlmodel import Session, select

from app.config import UPLOAD_DIR, settings
from app.db import get_db
from app.models import KnowledgeDoc, User
from app.rag import pipeline
from app.rag.loader import SUPPORTED_EXTS
from app.rag.store import get_store
from app.security import get_current_user

router = APIRouter(prefix="/api/documents", tags=["知识库"])


@router.get("")
async def list_documents(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    stmt = select(KnowledgeDoc).order_by(KnowledgeDoc.created_at.desc())
    return db.exec(stmt).all()


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "unnamed"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTS:
        raise HTTPException(400, f"不支持的文件类型 {suffix}")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"文件超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")

    doc = KnowledgeDoc(
        filename=filename,
        stored_name=f"{uuid.uuid4().hex[:8]}_{filename}",
        size_bytes=len(content),
        status="processing",
    )
    (UPLOAD_DIR / doc.stored_name).write_bytes(content)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return await pipeline.ingest_document(db, doc)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = db.get(KnowledgeDoc, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    pipeline.delete_document(db, doc)
    return {"ok": True}


@router.post("/reindex")
async def reindex(
    _: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """清空向量库，对所有文档重新解析入库。"""
    get_store().reset()
    docs = db.exec(select(KnowledgeDoc)).all()
    ok = failed = 0
    for doc in docs:
        doc.status = "processing"
        result = await pipeline.ingest_document(db, doc)
        if result.status == "ready":
            ok += 1
        else:
            failed += 1
    logger.info(f"重建索引完成: 成功 {ok}, 失败 {failed}")
    return {"ok": ok, "failed": failed, "total_chunks": get_store().chunk_count()}
