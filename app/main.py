"""FastAPI 主应用"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from app.config import get_settings
from app.db.database import init_database
from app.api.routes import router
from app.logger import setup_logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("=" * 60)
    logger.info("AI Judge System 正在启动...")
    logger.info("=" * 60)
    
    # 初始化数据库
    try:
        await init_database()
        logger.success("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    
    logger.success("系统启动完成！")
    logger.info(f"API 文档地址: http://{settings.server_host}:{settings.server_port}/docs")
    
    yield
    
    # 关闭时
    logger.info("AI Judge System 正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Judge System",
    description="基于多模态 AI 的娱乐评分系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api", tags=["评委系统"])

# 挂载前端静态文件
frontend_path = Path(__file__).parent.parent / "frontend"
logos_path = Path(__file__).parent.parent / "logos"

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# 挂载 logos 文件夹
if logos_path.exists():
    app.mount("/logos", StaticFiles(directory=str(logos_path)), name="logos")

if frontend_path.exists():
    
    @app.get("/")
    async def root():
        """根路径 - 返回前端页面"""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {
            "message": "欢迎使用 AI Judge System",
            "version": "1.0.0",
            "docs": "/docs",
            "api_prefix": "/api",
            "frontend": "/static/index.html"
        }
    
    @app.get("/debug.html")
    async def debug_page():
        """调试页面"""
        debug_file = frontend_path / "debug.html"
        if debug_file.exists():
            return FileResponse(str(debug_file))
        return {"error": "调试页面不存在"}
    
    @app.get("/config.html")
    async def config_page():
        """配置检查页面"""
        config_file = frontend_path / "config.html"
        if config_file.exists():
            return FileResponse(str(config_file))
        return {"error": "配置页面不存在"}

    @app.get("/results.html")
    async def results_page_html():
        """结果展示页面 (.html)"""
        results_file = frontend_path / "results.html"
        if results_file.exists():
            return FileResponse(str(results_file))
        return {"error": "结果页面不存在"}

    @app.get("/results")
    async def results_page():
        """结果展示页面"""
        results_file = frontend_path / "results.html"
        if results_file.exists():
            return FileResponse(str(results_file))
        return {"error": "结果页面不存在"}
else:
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "欢迎使用 AI Judge System",
            "version": "1.0.0",
            "docs": "/docs",
            "api_prefix": "/api",
        }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_level="info",
    )

