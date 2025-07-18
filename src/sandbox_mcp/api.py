"""API routes for the sandbox MCP server."""

import json
import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .config import settings
from .models import (
    ExecuteRequest,
    MessageType,
    TextOutput,
    ImageOutput,
    ErrorOutput,
    ApiResponse,
    ExecuteSyncResponse
)
from .kernel_manager import kernel_manager

router = APIRouter()
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


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


@router.post("/execute_sync", response_model=ApiResponse)
async def execute_code_sync(
    request: ExecuteRequest,
    _: bool = Depends(verify_api_key)
) -> ApiResponse:
    """同步执行 Python 代码，返回统一结构。"""
    outputs = []
    try:
        # 获取 session 并执行代码，收集所有输出
        session = await kernel_manager.get_or_create_session(request.session_id)
        if not session.kernel_client:
            logger.error(f"Kernel client not available for session_id={request.session_id}")
            raise RuntimeError("Kernel client not available")
        session.is_busy = True
        session.execution_count += 1
        logger.info(f"Executing code in session_id={session.session_id}, code={request.code}")
        session.kernel_client.execute(request.code)
        start_time = time.time()
        execution_timeout = request.timeout or settings.max_execution_time
        while True:
            try:
                reply = await asyncio.wait_for(
                    session.kernel_client.get_iopub_msg(),
                    timeout=1.0
                )
                msg_type = reply["msg_type"]
                content = reply["content"]
                logger.debug(f"Received msg_type={msg_type} for session_id={session.session_id}")
                output_data = await _process_message(
                    type("Msg", (), {"type": MessageType(msg_type), "content": content})()
                )
                if output_data:
                    outputs.append(output_data)
                if msg_type == "status" and content.get("execution_state") == "idle":
                    logger.info(f"Execution finished for session_id={session.session_id}")
                    break
                if time.time() - start_time > execution_timeout:
                    await session.kernel_manager.interrupt_kernel()
                    logger.warning(f"Execution timeout for session_id={session.session_id}")
                    break
            except asyncio.TimeoutError:
                if time.time() - start_time > execution_timeout:
                    await session.kernel_manager.interrupt_kernel()
                    logger.warning(f"Execution timeout (asyncio.TimeoutError) for session_id={session.session_id}")
                    break
                continue
    except Exception as exc:
        logger.error(f"Exception during code execution: {exc}")
    finally:
        session.is_busy = False
        session.update_activity()
        logger.info(f"Session {session.session_id} activity updated, is_busy={session.is_busy}")
    outputs_text = []
    outputs_image = []
    outputs_error = []
    for output in outputs:
        if "text" in output:
            outputs_text.append(output["text"])
        if "image" in output:
            outputs_image.append(output["image"])
        if "error" in output:
            outputs_error.append({
                "error": output["error"],
                "traceback": output.get("traceback", [])
            })
    logger.info(f"Execution result for session_id={session.session_id}:  texts={len(outputs_text)}, images={len(outputs_image)}, errors={len(outputs_error)}")
    return ApiResponse(
        data=ExecuteSyncResponse(
            texts=outputs_text,
            images=outputs_image,
            errors=outputs_error
        )
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

