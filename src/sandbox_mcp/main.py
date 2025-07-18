"""Main application module for the sandbox MCP server."""

import logging
from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .api import router
from .kernel_manager import kernel_manager
from .mcp_server import mcp
from . import __version__
from .logger_config import setup_logger, request_id_ctx_var  # 日志初始化

setup_logger()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Combined lifespan manager for both kernel manager and MCP."""
    # Startup
    logger.info("Starting Python Sandbox MCP Server")
    await kernel_manager.start()
    
    # Start MCP session manager
    async with mcp.session_manager.run():
        logger.info(f"Server started on {settings.host}:{settings.port}")
        logger.info("MCP server mounted at /ai/sandbox/v1/mcp")
        
        yield
    
    # Shutdown
    logger.info("Shutting down Python Sandbox MCP Server")
    await kernel_manager.stop()
    logger.info("Server shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Get MCP app and its lifespan
    mcp_app = mcp.streamable_http_app()
    
    app = FastAPI(
        title="Python Sandbox MCP Server",
        description="A secure Python code execution sandbox with MCP support",
        version=__version__,
        lifespan=combined_lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware
    if settings.allowed_hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Include API routes
    api_prefix = "/ai/sandbox/v1/api"
    app.include_router(router, prefix=api_prefix, tags=["API"])
    
    # Mount MCP server
    mcp_prefix = "/ai/sandbox/v1/mcp"
    app.mount(mcp_prefix, mcp_app)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Python Sandbox MCP Server",
            "version": __version__,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
            "mcp_endpoint": mcp_prefix,
            "api_endpoint": api_prefix,
        }
    
    return app


app = create_app()

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    # 获取 request_id，或者生成一个新的 UUID
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx_var.set(request_id)  # 设置 request_id 到 contextvars

    start_time = time.time()
    logging.info(f"Start request {request_id}")  # 日志记录请求开始

    # 处理请求
    response = await call_next(request)

    process_time = time.time() - start_time
    formatted_process_time = f"{process_time:.4f}"  # 格式化为4位小数

    logging.info(
        f"End request {request_id} - Duration: {formatted_process_time} seconds"
    )

    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "sandbox_mcp.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )