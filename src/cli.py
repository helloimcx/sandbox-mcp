"""Command line interface for the sandbox MCP server."""

import argparse
import sys
import uvicorn
from config.config import settings
from sandbox_mcp import __version__


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Python Sandbox MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sandbox-mcp                          # Start server with default settings
  sandbox-mcp --host 0.0.0.0 --port 8080  # Custom host and port
  sandbox-mcp --debug                  # Enable debug mode
  sandbox-mcp --api-key secret123      # Enable API key authentication
"""
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"sandbox-mcp {__version__}"
    )
    
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        default=settings.debug,
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--api-key",
        default=settings.api_key,
        help="API key for authentication (optional)"
    )
    
    parser.add_argument(
        "--max-kernels",
        type=int,
        default=settings.max_kernels,
        help=f"Maximum number of concurrent kernels (default: {settings.max_kernels})"
    )
    
    parser.add_argument(
        "--kernel-timeout",
        type=int,
        default=settings.kernel_timeout,
        help=f"Kernel idle timeout in seconds (default: {settings.kernel_timeout})"
    )
    
    parser.add_argument(
        "--max-execution-time",
        type=int,
        default=settings.max_execution_time,
        help=f"Maximum execution time per request in seconds (default: {settings.max_execution_time})"
    )
    
    args = parser.parse_args()
    
    # Update settings with CLI arguments
    settings.host = args.host
    settings.port = args.port
    settings.debug = args.debug
    settings.api_key = args.api_key
    settings.max_kernels = args.max_kernels
    settings.kernel_timeout = args.kernel_timeout
    settings.max_execution_time = args.max_execution_time
    
    print(f"Starting Python Sandbox MCP Server v{__version__}")
    print(f"Server will be available at http://{args.host}:{args.port}")
    
    if args.debug:
        print("Debug mode enabled")
        print(f"API documentation: http://{args.host}:{args.port}/docs")
    
    if args.api_key:
        print("API key authentication enabled")
    
    try:
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=args.debug,
            reload_dirs=["src"] if args.debug else None,
            log_level="info" if not args.debug else "debug",
            access_log=args.debug
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()