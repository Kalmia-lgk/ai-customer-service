"""FastAPI 应用入口：装配路由、静态资源，lifespan 中初始化全局单例。"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Windows 控制台 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.responses import RedirectResponse

from app.config import STATIC_ADMIN_DIR, STATIC_DIR, STATIC_SHARED_DIR, settings
from app.db import init_db
from app.llm import get_gateway
from app.rag.store import get_store
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.tickets import router as tickets_router
from app.routers.ws import router as ws_router
from app.services import settings_service

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings_service.seed_defaults()
    gateway = get_gateway()   # 全局唯一 LLM 出口
    store = get_store()       # 全局唯一 Chroma 客户端
    logger.info("=" * 50)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  LLM        : {gateway.chat_model} @ {gateway.base_url}")
    logger.info(f"  Configured : {gateway.is_configured}")
    logger.info(f"  Knowledge  : {store.chunk_count()} chunks")
    logger.info(f"  Customer UI: http://localhost:{settings.PORT}/")
    logger.info(f"  Admin UI   : http://localhost:{settings.PORT}/admin/")
    logger.info("=" * 50)
    yield
    logger.info("Server stopped.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 RAG + LangGraph Agent 的 AI 智能客服系统",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# 生产为同源部署（FastAPI 托管前端），仅开发调试时放开本地跨域
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000",
                       "http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(tickets_router)
app.include_router(admin_router)
app.include_router(ws_router)


@app.get("/api/health", tags=["系统"])
async def health():
    gateway = get_gateway()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "llm_configured": gateway.is_configured,
        "llm_model": gateway.chat_model,
        "chunks": get_store().chunk_count(),
    }


@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    return RedirectResponse(url="/admin/", status_code=302)


# 静态资源：/assets 与 /admin 必须先于 /
if STATIC_SHARED_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_SHARED_DIR)), name="shared")
if STATIC_ADMIN_DIR.exists():
    app.mount("/admin", StaticFiles(directory=str(STATIC_ADMIN_DIR), html=True), name="admin")
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="customer")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
