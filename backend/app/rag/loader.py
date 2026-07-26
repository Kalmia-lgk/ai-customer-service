"""文档解析：按扩展名把文件转成纯文本（pypdf / python-docx / 直接读）。"""
from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTS = {".pdf", ".docx", ".txt", ".md", ".csv"}


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix in (".txt", ".md", ".csv"):
        return path.read_text("utf-8", errors="replace")
    raise ValueError(f"不支持的文件类型: {suffix}（支持 {', '.join(sorted(SUPPORTED_EXTS))}）")
