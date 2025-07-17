"""API routes for the sandbox MCP server."""

import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings
from .models import (
    ExecuteRequest, 
    MessageType,
    TextOutput,
    ImageOutput,
    ErrorOutput
)
from .kernel_manager import kernel_manager

router = APIRouter()
security = HTTPBearer(auto_error=False)


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify API key if configured."""
    if not settings.api_key:
        return True
    
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    
    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True


@router.post("/execute")
async def execute_code(
    request: ExecuteRequest,
    _: bool = Depends(verify_api_key)
) -> StreamingResponse:
    """Execute Python code and stream results."""
    
    async def stream_results():
        """Stream execution results."""
        try:
            async for message in kernel_manager.execute_code(
                code=request.code,
                session_id=request.session_id,
                timeout=request.timeout
            ):
                # Convert message to appropriate output format
                output_data = await _process_message(message)
                if output_data:
                    yield json.dumps(output_data) + "\n"
                    
        except Exception as e:
            error_output = ErrorOutput(error=str(e), traceback=[])
            yield json.dumps(error_output.model_dump()) + "\n"
    
    return StreamingResponse(
        stream_results(),
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/sessions")
async def list_sessions(
    _: bool = Depends(verify_api_key)
) -> Dict[str, Any]:
    """List active kernel sessions."""
    return {
        "sessions": kernel_manager.get_session_info(),
        "total": len(kernel_manager.sessions)
    }


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    _: bool = Depends(verify_api_key)
) -> Dict[str, str]:
    """Terminate a specific kernel session."""
    if session_id not in kernel_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = kernel_manager.sessions.pop(session_id)
    await session.stop()
    
    return {"message": f"Session {session_id} terminated"}


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(
    session_id: str,
    _: bool = Depends(verify_api_key)
) -> Dict[str, str]:
    """Interrupt execution in a specific kernel session."""
    if session_id not in kernel_manager.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = kernel_manager.sessions[session_id]
    if session.kernel_manager:
        await session.kernel_manager.interrupt_kernel()
    
    return {"message": f"Session {session_id} interrupted"}


async def _process_message(message) -> Dict[str, Any]:
    """Process a kernel message and convert to appropriate output format."""
    msg_type = message.type
    content = message.content
    
    if msg_type == MessageType.STREAM:
        if 'text' in content:
            return TextOutput(text=content['text']).model_dump()
    
    elif msg_type == MessageType.DISPLAY_DATA:
        data = content.get('data', {})
        if 'image/png' in data:
            return ImageOutput(
                image=data['image/png'],
                format='png'
            ).model_dump()
        elif 'text/plain' in data:
            return TextOutput(text=data['text/plain']).model_dump()
    
    elif msg_type == MessageType.EXECUTE_RESULT:
        data = content.get('data', {})
        if 'text/plain' in data:
            return TextOutput(text=data['text/plain']).model_dump()
        elif 'image/png' in data:
            return ImageOutput(
                image=data['image/png'],
                format='png'
            ).model_dump()
    
    elif msg_type == MessageType.ERROR:
        traceback = content.get('traceback', [])
        error_text = '\n'.join(traceback) if traceback else content.get('evalue', 'Unknown error')
        return ErrorOutput(
            error=error_text,
            traceback=traceback
        ).model_dump()
    
    return None

