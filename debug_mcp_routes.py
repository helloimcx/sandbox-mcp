#!/usr/bin/env python3
"""Debug MCP routes."""

from src.sandbox_mcp.mcp_server import mcp

def debug_mcp_routes():
    """Debug MCP routes and app structure."""
    print("🔍 Debugging MCP Routes\n")
    
    # Get the streamable HTTP app
    mcp_app = mcp.streamable_http_app()
    
    print(f"MCP App type: {type(mcp_app)}")
    print(f"MCP App: {mcp_app}")
    print()
    
    # Check if app has routes
    if hasattr(mcp_app, 'routes'):
        print(f"Routes: {mcp_app.routes}")
        for route in mcp_app.routes:
            print(f"  Route: {route}")
            if hasattr(route, 'path'):
                print(f"    Path: {route.path}")
            if hasattr(route, 'methods'):
                print(f"    Methods: {route.methods}")
    else:
        print("No routes attribute found")
    print()
    
    # Check if app has router
    if hasattr(mcp_app, 'router'):
        print(f"Router: {mcp_app.router}")
        if hasattr(mcp_app.router, 'routes'):
            print(f"Router routes: {mcp_app.router.routes}")
            for route in mcp_app.router.routes:
                print(f"  Router Route: {route}")
                if hasattr(route, 'path'):
                    print(f"    Path: {route.path}")
                if hasattr(route, 'methods'):
                    print(f"    Methods: {route.methods}")
    else:
        print("No router attribute found")
    print()
    
    # Check MCP instance
    print(f"MCP instance: {mcp}")
    print(f"MCP name: {mcp.name}")
    print(f"MCP stateless_http: {getattr(mcp, 'stateless_http', 'Not found')}")
    print(f"MCP json_response: {getattr(mcp, 'json_response', 'Not found')}")
    print()
    
    # Check session manager
    print(f"Session manager: {mcp.session_manager}")
    print(f"Session manager type: {type(mcp.session_manager)}")
    print()
    
    # Check tools
    print("Tools:")
    if hasattr(mcp, '_tools'):
        for tool_name, tool in mcp._tools.items():
            print(f"  {tool_name}: {tool}")
    else:
        print("  No _tools attribute found")
    print()
    
    # Check resources
    print("Resources:")
    if hasattr(mcp, '_resources'):
        for resource_name, resource in mcp._resources.items():
            print(f"  {resource_name}: {resource}")
    else:
        print("  No _resources attribute found")
    print()
    
    # Check prompts
    print("Prompts:")
    if hasattr(mcp, '_prompts'):
        for prompt_name, prompt in mcp._prompts.items():
            print(f"  {prompt_name}: {prompt}")
    else:
        print("  No _prompts attribute found")
    print()

if __name__ == "__main__":
    debug_mcp_routes()