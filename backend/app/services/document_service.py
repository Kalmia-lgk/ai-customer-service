# ============================================================
# 文档管理服务 - 处理文件上传、校验、列表管理、重建索引
# ============================================================
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from loguru import logger

from app.core.config import settings
from app.rag.ingestion import DocumentIngestion


# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}

# 允许的 MIME 类型
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/csv",
    "application/octet-stream",  # 部分系统对 docx 可能报此类型
}


class DocumentService:
    """
    文档管理服务
    负责: 文件校验 → 持久化存储 → 触发索引 → 元数据管理
    """

    def __init__(self) -> None:
        self._ingestion = DocumentIngestion()
        self._upload_dir = Path(settings.UPLOAD_DIR)

    # ==================== 文件校验 ====================

    def validate_file(self, file: UploadFile) -> tuple[bool, str]:
        """
        校验上传文件
        返回: (是否合法, 错误信息)
        """
        # 检查文件名
        if not file.filename:
            return False, "文件名为空"

        # 检查扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"不支持的文件类型: {ext}。支持的类型: {', '.join(ALLOWED_EXTENSIONS)}"

        # 检查 MIME 类型（非严格模式，仅警告）
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            logger.warning(f"MIME 类型可能不匹配: {file.content_type} (文件: {file.filename})")

        return True, ""

    def validate_size(self, size: int) -> tuple[bool, str]:
        """校验文件大小"""
        max_bytes = settings.max_upload_bytes
        if size > max_bytes:
            return False, f"文件过大: {size / 1024 / 1024:.1f}MB。限制: {settings.MAX_UPLOAD_SIZE_MB}MB"
        return True, ""

    # ==================== 文件操作 ====================

    async def upload_file(self, file: UploadFile) -> dict:
        """
        处理文件上传全流程
        1. 校验 → 2. 保存到磁盘 → 3. 触发向量索引 → 4. 返回文档信息
        """
        # 1. 校验文件名
        valid, err = self.validate_file(file)
        if not valid:
            raise ValueError(err)

        # 2. 读取内容并校验大小
        content = await file.read()

        # 检查空文件
        if not content:
            raise ValueError("文件内容为空")

        valid, err = self.validate_size(len(content))
        if not valid:
            raise ValueError(err)

        # 3. 保存文件到磁盘
        file_path = self._upload_dir / file.filename

        # 如果已存在同名文件，加时间戳后缀
        if file_path.exists():
            stem = file_path.stem
            ext = file_path.suffix
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self._upload_dir / f"{stem}_{ts}{ext}"

        # 写入文件
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"文件已保存: {file_path} ({len(content) / 1024:.1f} KB)")

        # 4. 触发向量索引
        meta = self._ingestion.index_file(str(file_path), file_path.name)

        if meta is None:
            # 索引失败，但文件已保存
            return {
                "success": True,
                "message": "文件已保存，但向量索引失败，请检查文件格式",
                "document": {
                    "doc_id": file_path.stem,
                    "filename": file_path.name,
                    "file_type": file_path.suffix.lower(),
                    "file_size": len(content),
                    "chunk_count": 0,
                    "uploaded_at": "",
                    "status": "error",
                },
            }

        return {
            "success": True,
            "message": f"文件 '{file_path.name}' 上传并索引成功",
            "document": meta,
        }

    def list_documents(self) -> list[dict]:
        """获取所有文档列表"""
        return self._ingestion.get_all_documents()

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档（元数据 + 向量 + 原始文件）
        """
        # 通过 doc_id 查找对应的文件信息
        doc = self._ingestion.get_document(doc_id)
        if not doc:
            logger.warning(f"文档不存在: {doc_id}")
            return False

        # 删除原始文件
        file_path = self._upload_dir / doc["filename"]
        if file_path.exists():
            file_path.unlink()
            logger.info(f"已删除原始文件: {file_path}")

        # 同时尝试匹配带时间戳的文件名
        for f in self._upload_dir.iterdir():
            if f.is_file() and f.stem.startswith(doc["filename"].rsplit(".", 1)[0]):
                if f != file_path and f.exists():
                    f.unlink()

        # 删除向量和元数据
        return self._ingestion.delete_document(doc_id)

    def reindex(self) -> dict:
        """重建全量索引"""
        return self._ingestion.rebuild_index()

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        docs = self._ingestion.get_all_documents()
        active = [d for d in docs if d["status"] == "active"]
        total_chunks = sum(d.get("chunk_count", 0) for d in active)
        total_size = sum(d.get("file_size", 0) for d in active)
        return {
            "document_count": len(active),
            "total_chunks": total_chunks,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
        }
