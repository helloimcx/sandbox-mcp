"""Kernel management for the sandbox MCP server."""

import asyncio
import time
import uuid
import os
from typing import Dict, Optional, AsyncGenerator, List, Tuple
from jupyter_client.manager import AsyncKernelManager
from .kernel_session import KernelSession
import logging

from config.config import settings
from schema.models import StreamMessage, MessageType, FileItem
from utils.file_utils import download_file
from utils.session_config import SessionFileConfig

logger = logging.getLogger(__name__)


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
    

    
    async def create_session_with_files(
        self, 
        session_id: Optional[str] = None,
        file_urls: Optional[List[str]] = None,
        files: Optional[List[FileItem]] = None,
        timeout: int = 30
    ) -> Tuple[KernelSession, List[str], List[str]]:
        """Create a new session and download files.
        
        Args:
            session_id: Optional session ID
            file_urls: List of file URLs to download
            timeout: Download timeout in seconds
            
        Returns:
            Tuple of (session, downloaded_files, errors)
        """
        # Check if we've reached the maximum number of kernels
        if len(self.sessions) >= settings.max_kernels:
            # Remove the oldest idle session
            await self._cleanup_oldest_session()
        
        # Create new session
        new_session_id = session_id or str(uuid.uuid4())
        # Create unique working directory for the session
        session_dir = os.path.join('/tmp/sandbox_sessions', new_session_id)
        os.makedirs(session_dir, exist_ok=True)
        kernel_manager = AsyncKernelManager()
        kernel_manager.cwd = session_dir
        session = KernelSession(new_session_id, kernel_manager)
        
        downloaded_files = []
        errors = []
        
        # Initialize session file config
        session_config = SessionFileConfig(session_dir)
        
        # Download files from file_urls (legacy support)
        if file_urls:
            for url in file_urls:
                filename, error = await download_file(url, session_dir, timeout, verify_ssl=False)
                if error:
                    errors.append(error)
                else:
                    downloaded_files.append(filename)
        
        # Download files from files list with ID management
        if files:
            for file_item in files:
                file_id = file_item.id
                file_url = file_item.url
                
                # Check if file already exists
                if session_config.has_file(file_id):
                    existing_filename = session_config.get_filename(file_id)
                    file_path = os.path.join(session_dir, existing_filename)
                    
                    # Verify file still exists on disk
                    if os.path.exists(file_path):
                        downloaded_files.append(existing_filename)
                        logger.info(f"File {file_id} already exists: {existing_filename}")
                        continue
                    else:
                        # File was deleted, remove from config and re-download
                        session_config.remove_file(file_id)
                        logger.warning(f"File {file_id} was deleted from disk, re-downloading")
                
                # Download new file
                filename, error = await download_file(file_url, session_dir, timeout, verify_ssl=False)
                if error:
                    errors.append(f"Failed to download file {file_id}: {error}")
                else:
                    downloaded_files.append(filename)
                    session_config.add_file(file_id, filename)
                    logger.info(f"Downloaded new file {file_id}: {filename}")
        
        try:
            await session.start()
            self.sessions[new_session_id] = session
            logger.info(f"Created new kernel session: {new_session_id} with cwd: {session_dir}")
            return session, downloaded_files, errors
        except Exception as e:
            logger.error(f"Failed to create kernel session: {e}")
            await session.stop()
            raise
    
    async def get_or_create_session(self, session_id: Optional[str] = None) -> KernelSession:
        """Get existing session or create a new one."""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.update_activity()
            return session
        
        session, _, _ = await self.create_session_with_files(session_id=session_id)
        return session

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