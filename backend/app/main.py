# ============================================================
# FastAPI 应用主入口
# AI 智能客服系统 - 应用启动、中间件、路由注册
# ============================================================
from __future__ import annotations

import sys
import os
from pathlib import Path

# Windows 控制台 UTF-8 编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 确保 backend 目录在 Python 路径中
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.routers.chat import router as chat_router
from app.routers.documents import router as doc_router
from app.routers.customer import router as customer_router
from app.routers.admin import router as admin_router
from app.routers.ws import router as ws_router

# 配置 loguru 日志
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO" if not settings.DEBUG else "DEBUG",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 50)
    logger.info(f"AI Customer Service v{settings.APP_VERSION} starting...")
    logger.info(f"  LLM Provider : {settings.LLM_PROVIDER}")
    logger.info(f"  LLM Model    : {settings.get_llm_model()}")
    logger.info(f"  Listen       : http://{settings.HOST}:{settings.PORT}")
    logger.info(f"  Customer UI  : http://localhost:{settings.PORT}/")
    logger.info(f"  Admin UI     : http://localhost:{settings.PORT}/admin")
    logger.info(f"  Admin Login  : {settings.ADMIN_EMAIL}")
    logger.info("=" * 50)
    yield
    logger.info("Server stopped.")


# ==================== 创建 FastAPI 应用 ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 RAG + Agent 的现代化 AI 智能客服系统",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ==================== CORS 中间件 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ==================== 注册路由 ====================
# API 路由必须先注册，再挂载静态文件

app.include_router(chat_router)       # /api/chat, /api/sessions/*
app.include_router(doc_router)        # /api/documents/*
app.include_router(customer_router)   # /api/customer/chat, /api/customer/escalate
app.include_router(admin_router)      # /api/admin/login, /api/admin/escalations/*
app.include_router(ws_router)         # /ws/customer/*, /ws/admin/*


# ==================== 健康检查 ====================

@app.get("/api/health", tags=["系统"])
async def health_check():
    """服务健康检查"""
    chroma_chunks = 0
    rag_available = False
    try:
        from app.rag.retrieval import DocumentRetrieval
        retrieval = DocumentRetrieval()
        rag_available = retrieval.is_available
        if rag_available:
            chroma_chunks = retrieval.get_collection_stats().get("total_chunks", 0)
    except Exception:
        pass

    # 检测 Demo 模式
    import os
    demo_mode = os.getenv("DEMO_MODE", "").lower() == "true"

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.get_llm_model(),
        "demo_mode": demo_mode,
        "rag_available": rag_available,
        "chroma_chunks": chroma_chunks,
    }


# ==================== 静态文件服务 ====================

PROJECT_ROOT = BACKEND_DIR.parent

# 重定向 /admin -> /admin/ （StaticFiles 需要斜杠，否则 404）
from starlette.responses import RedirectResponse

@app.get("/admin", include_in_schema=False)
async def admin_slash_redirect():
    return RedirectResponse(url="/admin/", status_code=302)

# Static file mounts - /admin MUST be before /
ADMIN_STATIC_DIR = PROJECT_ROOT / "static-admin"
if ADMIN_STATIC_DIR.exists():
    app.mount("/admin", StaticFiles(directory=str(ADMIN_STATIC_DIR), html=True), name="admin-static")
    logger.info(f"Admin UI mounted: {ADMIN_STATIC_DIR}")

STATIC_DIR = PROJECT_ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="customer-static")
    logger.info(f"Customer UI mounted: {STATIC_DIR}")


# ==================== 直接启动 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
