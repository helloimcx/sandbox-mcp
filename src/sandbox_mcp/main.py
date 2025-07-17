"""Main application module for the sandbox MCP server."""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .models import HealthCheck
from .kernel_manager import kernel_manager
from . import __version__ as MCP_VERSION
from .config import settings
from .api import router
from .mcp_server import mcp
from .logger_config import setup_logger  # 日志初始化

setup_logger()

logger = logging.getLogger(__name__)


def health_check() -> HealthCheck:
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version=MCP_VERSION,
        active_sessions=len(kernel_manager.sessions),
        uptime=time.time() - getattr(health_check, '_start_time', time.time())
    )
health_check._start_time = time.time()


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
        version=MCP_VERSION,
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
    # 只为非 /health 路径加前缀，/health 直接挂载
    app.include_router(router, prefix=api_prefix, tags=["API"])

    app.add_api_route("/health", health_check, methods=["GET"], response_model=HealthCheck)
    
    # Mount MCP server
    mcp_prefix = "/ai/sandbox/v1/mcp"
    app.mount(mcp_prefix, mcp_app)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Python Sandbox MCP Server",
            "version": MCP_VERSION,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
            "mcp_endpoint": mcp_prefix,
            "api_endpoint": api_prefix,
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "sandbox_mcp.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )