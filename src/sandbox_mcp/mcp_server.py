"""MCP server implementation for Python sandbox."""

import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from mcp.server.fastmcp import FastMCP
from .kernel_manager import kernel_manager
from .models import ExecuteRequest, TextOutput, ImageOutput, ErrorOutput


# Create MCP server instance
mcp = FastMCP(
    name="PythonSandboxMCP",
    description="A secure Python code execution sandbox with MCP support",
    stateless_http=True,
    streamable_http_path="/"
)


@mcp.tool()
async def execute_python_code(
    code: str,
    session_id: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """Execute Python code in a secure sandbox environment.
    
    Args:
        code: The Python code to execute
        session_id: Optional session ID for persistent execution context
        timeout: Optional timeout in seconds (default: 30)
    
    Returns:
        Dictionary containing execution results with text output, images, or errors
    """
    try:
        return await _execute_code_async(code, session_id, timeout)
    except Exception as e:
        return {
            "error": str(e),
            "traceback": []
        }


async def _execute_code_async(
    code: str,
    session_id: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """Async helper for code execution."""
    try:
        from .models import MessageType
        
        # Collect all output
        output_parts = []
        images = []
        
        async for message in kernel_manager.execute_code(code, session_id, timeout or 30):
            if message.type == MessageType.STREAM:
                if message.content.get("name") == "stdout":
                    output_parts.append(message.content.get("text", ""))
                elif message.content.get("name") == "stderr":
                    output_parts.append(message.content.get("text", ""))
            elif message.type == MessageType.EXECUTE_RESULT:
                # Handle execution results
                data = message.content.get("data", {})
                if "text/plain" in data:
                    output_parts.append(data["text/plain"])
            elif message.type == MessageType.DISPLAY_DATA:
                # Handle images and other display data
                data = message.content.get("data", {})
                if "image/png" in data:
                    images.append({
                        "type": "image",
                        "format": "png",
                        "data": data["image/png"]
                    })
                elif "text/plain" in data:
                    output_parts.append(data["text/plain"])
            elif message.type == MessageType.ERROR:
                return {
                    "error": message.content.get("ename", "Unknown error"),
                    "traceback": message.content.get("traceback", [])
                }
        
        result = {
            "output": "".join(output_parts),
            "images": images,
            "session_id": session_id or "default"
        }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Execution failed: {str(e)}",
            "traceback": []
        }


@mcp.tool()
def list_active_sessions() -> Dict[str, Any]:
    """List all active Python execution sessions.
    
    Returns:
        Dictionary containing session information
    """
    try:
        sessions_info = {}
        for session_id, session in kernel_manager.sessions.items():
            sessions_info[session_id] = {
                "execution_count": getattr(session, 'execution_count', 0),
                "last_activity": getattr(session, 'last_activity', None),
                "status": "active"
            }
        
        return {
            "total": len(sessions_info),
            "sessions": sessions_info
        }
    except Exception as e:
        return {
            "error": f"Failed to list sessions: {str(e)}",
            "total": 0,
            "sessions": {}
        }


@mcp.tool()
def terminate_session(session_id: str) -> Dict[str, str]:
    """Terminate a specific Python execution session.
    
    Args:
        session_id: The ID of the session to terminate
    
    Returns:
        Dictionary containing the operation result
    """
    try:
        # Check if session exists and remove it
        if hasattr(kernel_manager, 'sessions') and session_id in kernel_manager.sessions:
            del kernel_manager.sessions[session_id]
            return {"status": "success", "message": f"Session {session_id} terminated"}
        else:
            return {"status": "warning", "message": f"Session {session_id} not found or already terminated"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to terminate session: {str(e)}"}


@mcp.resource("session://{session_id}")
def get_session_info(session_id: str) -> str:
    """Get detailed information about a specific session.
    
    Args:
        session_id: The ID of the session to query
    
    Returns:
        JSON string containing session details
    """
    try:
        if session_id in kernel_manager.sessions:
            session = kernel_manager.sessions[session_id]
            info = {
                "session_id": session_id,
                "execution_count": getattr(session, 'execution_count', 0),
                "last_activity": getattr(session, 'last_activity', None),
                "status": "active",
                "kernel_info": getattr(session, 'kernel_info', {})
            }
            return json.dumps(info, indent=2)
        else:
            return json.dumps({"error": f"Session {session_id} not found"})
    except Exception as e:
        return json.dumps({"error": f"Failed to get session info: {str(e)}"})


@mcp.prompt()
def code_execution_prompt(
    task_description: str,
    code_style: str = "clean",
    include_comments: str = "true"
) -> str:
    """Generate a prompt for Python code execution tasks.
    
    Args:
        task_description: Description of what the code should accomplish
        code_style: Style of code to generate (clean, verbose, minimal)
        include_comments: Whether to include explanatory comments ("true" or "false")
    
    Returns:
        A formatted prompt for code generation
    """
    style_instructions = {
        "clean": "Write clean, readable Python code with proper formatting",
        "verbose": "Write detailed Python code with extensive explanations",
        "minimal": "Write concise, minimal Python code without extra explanations"
    }
    
    base_prompt = f"Please write Python code to accomplish the following task: {task_description}"
    
    style_instruction = style_instructions.get(code_style, style_instructions["clean"])
    prompt = f"{base_prompt}\n\n{style_instruction}."
    
    if include_comments.lower() == "true":
        prompt += " Include helpful comments to explain the code logic."
    
    prompt += "\n\nThe code will be executed in a secure sandbox environment with access to common Python libraries like numpy, matplotlib, etc."
    
    return prompt