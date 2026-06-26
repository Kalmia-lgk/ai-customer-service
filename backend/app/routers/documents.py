# ============================================================
# 文档管理路由 - 处理知识库相关 API
# POST   /api/documents/upload   上传文件
# GET    /api/documents           文档列表
# GET    /api/documents/{id}      文档详情
# DELETE /api/documents/{id}      删除文档
# POST   /api/documents/reindex   重建索引
# GET    /api/documents/stats     知识库统计
# ============================================================
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from loguru import logger

from app.schemas.models import (
    DocumentListResponse,
    DocumentInfo,
    UploadResponse,
    ReindexResponse,
    ErrorResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["文档管理"])

# 全局服务实例
doc_service = DocumentService()


@router.post("/upload", summary="上传文档")
async def upload_document(file: UploadFile = File(...)):
    """
    上传知识库文档

    支持格式: PDF, DOCX, TXT, Markdown, CSV
    大小限制: 由 MAX_UPLOAD_SIZE_MB 环境变量控制（默认 20MB）

    上传后自动进行向量化索引
    """
    try:
        result = await doc_service.upload_file(file)
        logger.info(f"文件上传成功: {file.filename}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传处理失败: {str(e)}")


@router.get("", summary="获取文档列表")
async def list_documents():
    """获取所有已上传的文档列表"""
    docs = doc_service.list_documents()
    return {"documents": docs}


@router.get("/{doc_id}", summary="获取文档详情")
async def get_document(doc_id: str):
    """获取指定文档的详细信息"""
    from app.rag.ingestion import DocumentIngestion
    ingestion = DocumentIngestion()
    doc = ingestion.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.delete("/{doc_id}", summary="删除文档")
async def delete_document(doc_id: str):
    """
    删除指定文档
    会同时删除: 原始文件、向量数据、元数据
    """
    ok = doc_service.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文档不存在或删除失败")
    return {"success": True, "message": "文档已删除"}


@router.post("/reindex", summary="重建索引")
async def reindex_documents():
    """
    一键重建向量索引
    会清空当前 ChromaDB 中的所有向量数据，然后重新读取 uploads 目录下的所有文件并索引
    注意: 操作不可逆，索引期间可能暂时无法检索
    """
    try:
        result = doc_service.reindex()
        return {
            "success": True,
            "message": "索引重建完成",
            "doc_count": result.get("doc_count", 0),
            "total_chunks": result.get("total_chunks", 0),
        }
    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.get("/stats/summary", summary="知识库统计")
async def get_knowledge_stats():
    """获取知识库的统计摘要"""
    stats = doc_service.get_stats()
    return stats
