"""Kernel management for the sandbox MCP server."""

import asyncio
import time
import uuid
from typing import Dict, Optional, AsyncGenerator
from jupyter_client.manager import AsyncKernelManager
from jupyter_client import AsyncKernelClient
import logging

from .config import settings
from .models import StreamMessage, MessageType

logger = logging.getLogger(__name__)


class KernelSession:
    """Represents a kernel session."""
    
    def __init__(self, session_id: str, kernel_manager: AsyncKernelManager):
        self.session_id = session_id
        self.kernel_manager = kernel_manager
        self.kernel_client: Optional[AsyncKernelClient] = None
        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_busy = False
        self.execution_count = 0
    
    async def start(self) -> None:
        """Start the kernel and client."""
        await self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        await self.kernel_client.wait_for_ready()
        
        # 重新实现字体配置，确保matplotlib图片能被正确捕获
        font_setup_code = """import matplotlib.pyplot as plt
from mplfonts import use_font

# 配置中文字体支持
try:
    use_font('Noto Sans CJK SC')
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
"""
        
        try:
            # 执行字体配置代码（静默执行）并等待完成
            msg_id = self.kernel_client.execute(font_setup_code, silent=True)
            while True:
                reply = await self.kernel_client.get_iopub_msg()
                if reply['msg_type'] == 'status' and reply['content'].get('execution_state') == 'idle':
                    break
            logger.info(f"Font configuration executed for kernel session {self.session_id}")
        except Exception as e:
            logger.warning(f"Failed to execute font configuration for session {self.session_id}: {e}")
        
        logger.info(f"Kernel session {self.session_id} started")
    
    async def stop(self) -> None:
        """Stop the kernel and client."""
        if self.kernel_client:
            self.kernel_client.stop_channels()
        await self.kernel_manager.shutdown_kernel()
        logger.info(f"Kernel session {self.session_id} stopped")
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def is_idle_timeout(self) -> bool:
        """Check if session has timed out."""
        return time.time() - self.last_activity > settings.kernel_timeout


class KernelManagerService:
    """Service for managing multiple kernel sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, KernelSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the kernel manager service."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Kernel manager service started")
    
    async def stop(self) -> None:
        """Stop the kernel manager service."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Stop all sessions
        for session in list(self.sessions.values()):
            await session.stop()
        self.sessions.clear()
        logger.info("Kernel manager service stopped")
    
    async def get_or_create_session(self, session_id: Optional[str] = None) -> KernelSession:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.update_activity()
            return session
        
        # Check if we've reached the maximum number of kernels
        if len(self.sessions) >= settings.max_kernels:
            # Remove the oldest idle session
            await self._cleanup_oldest_session()
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        kernel_manager = AsyncKernelManager()
        session = KernelSession(new_session_id, kernel_manager)
        
        try:
            await session.start()
            self.sessions[new_session_id] = session
            logger.info(f"Created new kernel session: {new_session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to create kernel session: {e}")
            await session.stop()
            raise
    
    async def execute_code(
        self, 
        code: str, 
        session_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> AsyncGenerator[StreamMessage, None]:
        """Execute code in a kernel session."""
        session = await self.get_or_create_session(session_id)
        
        if not session.kernel_client:
            raise RuntimeError("Kernel client not available")
        
        session.is_busy = True
        session.execution_count += 1
        execution_timeout = timeout or settings.max_execution_time
        
        try:
            msg_id = session.kernel_client.execute(code)
            start_time = time.time()
            
            while True:
                try:
                    # Wait for message with timeout
                    reply = await asyncio.wait_for(
                        session.kernel_client.get_iopub_msg(),
                        timeout=1.0
                    )
                    
                    msg_type = reply["msg_type"]
                    content = reply["content"]
                    
                    # Create stream message
                    stream_msg = StreamMessage(
                        type=MessageType(msg_type),
                        content=content,
                        timestamp=time.time(),
                        execution_count=session.execution_count
                    )
                    
                    yield stream_msg
                    
                    # Check for completion
                    if msg_type == "status" and content.get("execution_state") == "idle":
                        break
                    
                    # Check for timeout
                    if time.time() - start_time > execution_timeout:
                        # Interrupt the kernel
                        await session.kernel_manager.interrupt_kernel()
                        yield StreamMessage(
                            type=MessageType.ERROR,
                            content={"error": "Execution timeout"},
                            timestamp=time.time(),
                            execution_count=session.execution_count
                        )
                        break
                        
                except asyncio.TimeoutError:
                    # Check if execution has timed out
                    if time.time() - start_time > execution_timeout:
                        await session.kernel_manager.interrupt_kernel()
                        yield StreamMessage(
                            type=MessageType.ERROR,
                            content={"error": "Execution timeout"},
                            timestamp=time.time(),
                            execution_count=session.execution_count
                        )
                        break
                    continue
                    
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            yield StreamMessage(
                type=MessageType.ERROR,
                content={"error": str(e)},
                timestamp=time.time(),
                execution_count=session.execution_count
            )
        finally:
            session.is_busy = False
            session.update_activity()
    
    async def _cleanup_loop(self) -> None:
        """Cleanup loop for idle sessions."""
        while True:
            try:
                await asyncio.sleep(settings.kernel_cleanup_interval)
                await self._cleanup_idle_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_idle_sessions(self) -> None:
        """Remove idle sessions that have timed out."""
        sessions_to_remove = []
        
        for session_id, session in self.sessions.items():
            if not session.is_busy and session.is_idle_timeout():
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            session = self.sessions.pop(session_id)
            await session.stop()
            logger.info(f"Cleaned up idle session: {session_id}")
    
    async def _cleanup_oldest_session(self) -> None:
        """Remove the oldest idle session."""
        idle_sessions = [
            (session_id, session) for session_id, session in self.sessions.items()
            if not session.is_busy
        ]
        
        if idle_sessions:
            # Sort by creation time and remove the oldest
            oldest_session_id, oldest_session = min(
                idle_sessions, key=lambda x: x[1].created_at
            )
            self.sessions.pop(oldest_session_id)
            await oldest_session.stop()
            logger.info(f"Removed oldest session: {oldest_session_id}")
    
    def get_session_info(self) -> Dict[str, Dict]:
        """Get information about all active sessions."""
        return {
            session_id: {
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "is_busy": session.is_busy,
                "execution_count": session.execution_count
            }
            for session_id, session in self.sessions.items()
        }


# Global kernel manager instance
kernel_manager = KernelManagerService()