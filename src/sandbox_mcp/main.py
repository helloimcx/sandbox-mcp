"""Main application module for the sandbox MCP server."""

import logging
import asyncio
import contextlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import settings
from .api import router
from .kernel_manager import kernel_manager
from .mcp_server import mcp
from . import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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
        logger.info("MCP server mounted at /mcp")
        
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
    app.include_router(router, prefix="/api/v1")
    
    # Mount MCP server
    app.mount("/mcp", mcp_app)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Python Sandbox MCP Server",
            "version": __version__,
            "status": "running",
            "docs": "/docs" if settings.debug else "disabled",
            "mcp_endpoint": "/mcp",
            "api_endpoint": "/api/v1"
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