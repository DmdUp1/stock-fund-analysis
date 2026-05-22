"""金融分析平台 —— FastAPI 应用入口"""
# uvicorn app.main:app --reload
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.utils.config import settings
from app.utils.logger import logger
from app.db.database import init_db
from app.api.routes import analysis, portfolio, auto_analysis, warehouse, transactions
from app.services.auto_task_manager import run_daily_analysis, backup_database

scheduler = AsyncIOScheduler()


def _static_dir() -> Path:
    """前端构建产物目录"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend_dist"
    return Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 & 启动后台任务"""
    logger.info(f"{settings.APP_NAME} 启动中...")
    # 确保数据目录存在
    settings.FILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 初始化数据库
    await init_db()
    logger.info("[main] 数据库表已就绪")

    # 启动定时任务
    scheduler.add_job(
        run_daily_analysis,
        "cron",
        hour=settings.AUTO_ANALYSIS_HOUR,
        minute=settings.AUTO_ANALYSIS_MINUTE,
        id="daily_analysis",
        replace_existing=True,
    )
    scheduler.add_job(
        backup_database,
        "cron",
        hour=23,
        minute=0,
        id="daily_backup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"[main] 定时任务已启动（分析: {settings.AUTO_ANALYSIS_HOUR}:{settings.AUTO_ANALYSIS_MINUTE}，备份: 23:00）")

    yield

    # 关闭
    scheduler.shutdown()
    logger.info("[main] 应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS —— 允许前端 dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(analysis.router)
app.include_router(portfolio.router)
app.include_router(auto_analysis.router)
app.include_router(warehouse.router)
app.include_router(transactions.router)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

# ── SPA 静态文件服务 ─────────────────────────────────
_static_root = _static_dir()


@app.get("/api/client-config")
async def client_config():
    """前端运行时配置（API Key 等不固定值，免重新编译）"""
    return {
        "apiKey": settings.API_KEY,
        "appName": settings.APP_NAME,
    }


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):
    """提供前端静态文件 + SPA 回退（注入运行时配置）"""
    # 1) 尝试精确匹配文件
    if full_path:
        file_path = _static_root / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))

    # 2) SPA 回退 —— 非 API 路由返回 index.html
    if not full_path.startswith("api/"):
        index_path = _static_root / "index.html"
        if index_path.is_file():
            content = index_path.read_text(encoding="utf-8")
            # 注入运行时配置（API Key 等）
            inject = (
                f'<script>window.__RUNTIME_CONFIG__={{"apiKey":"{settings.API_KEY}"}}</script>'
            )
            content = content.replace("</head>", f"{inject}</head>")
            return HTMLResponse(content)

    return JSONResponse({"detail": "Not Found"}, status_code=404)