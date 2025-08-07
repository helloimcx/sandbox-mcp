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
from config.session_config import SessionFileConfig

logger = logging.getLogger(__name__)


class KernelManagerService:
    """Service for managing multiple kernel sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, KernelSession] = {}
        self.session_pool: List[KernelSession] = []  # Pre-created sessions pool
        self._cleanup_task: Optional[asyncio.Task] = None
        self._pool_refill_task: Optional[asyncio.Task] = None
        self._pool_lock = asyncio.Lock()  # Lock for thread-safe pool operations
    
    async def start(self) -> None:
        """Start the kernel manager service."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._pool_refill_task = asyncio.create_task(self._pool_refill_loop())
        
        # Initialize session pool
        await self._initialize_session_pool()
        
        logger.info(f"Kernel manager service started with session pool size: {settings.session_pool_size}")
    
    async def stop(self) -> None:
        """Stop the kernel manager service."""
        # Cancel background tasks
        for task in [self._cleanup_task, self._pool_refill_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop all active sessions
        for session in list(self.sessions.values()):
            await session.stop()
        self.sessions.clear()
        
        # Stop all pooled sessions
        async with self._pool_lock:
            for session in self.session_pool:
                await session.stop()
            self.session_pool.clear()
        
        logger.info("Kernel manager service stopped")
    
    async def _initialize_session_pool(self) -> None:
        """Initialize the session pool with pre-created sessions."""
        async with self._pool_lock:
            for i in range(settings.session_pool_size):
                try:
                    session = await self._create_pool_session()
                    self.session_pool.append(session)
                    logger.info(f"Created pool session {i+1}/{settings.session_pool_size}")
                except Exception as e:
                    logger.error(f"Failed to create pool session {i+1}: {e}")
    
    async def _create_pool_session(self) -> KernelSession:
        """Create a new session for the pool."""
        session_id = f"pool_{str(uuid.uuid4())}"
        session_dir = os.path.join('/tmp/sandbox_sessions', session_id)
        
        # Create unique working directory
        os.makedirs(session_dir, exist_ok=True)
        kernel_manager = AsyncKernelManager()
        kernel_manager.cwd = session_dir
        session = KernelSession(session_id, kernel_manager)
        
        await session.start()
        return session
    
    async def _get_session_from_pool(self) -> Optional[KernelSession]:
        """Get a session from the pool if available."""
        async with self._pool_lock:
            if self.session_pool:
                session = self.session_pool.pop(0)
                logger.info(f"Retrieved session from pool: {session.session_id}")
                return session
            return None
    
    async def _return_session_to_pool(self, session: KernelSession) -> bool:
        """Return a session to the pool if there's space."""
        async with self._pool_lock:
            if len(self.session_pool) < settings.session_pool_size:
                # Reset session state
                session.execution_count = 0
                session.is_busy = False
                session.update_activity()
                
                # Clear session directory but keep the directory structure
                session_dir = session.kernel_manager.cwd
                try:
                    # Remove all files in the session directory
                    for filename in os.listdir(session_dir):
                        file_path = os.path.join(session_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    
                    # Clear session config
                    session_config = SessionFileConfig(session_dir)
                    session_config.clear_all_files()
                    
                    self.session_pool.append(session)
                    logger.info(f"Returned session to pool: {session.session_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clean session for pool return: {e}")
                    await session.stop()
                    return False
            else:
                # Pool is full, stop the session
                await session.stop()
                return False
    
    async def _pool_refill_loop(self) -> None:
        """Background task to maintain the session pool."""
        while True:
            try:
                await asyncio.sleep(settings.session_pool_refill_interval)
                await self._refill_session_pool()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pool refill loop: {e}")
    
    async def _refill_session_pool(self) -> None:
        """Refill the session pool to maintain the desired size."""
        async with self._pool_lock:
            current_size = len(self.session_pool)
            target_size = settings.session_pool_size
            
            if current_size < target_size:
                sessions_to_create = target_size - current_size
                logger.info(f"Refilling session pool: creating {sessions_to_create} sessions")
                
                for i in range(sessions_to_create):
                    try:
                        session = await self._create_pool_session()
                        self.session_pool.append(session)
                        logger.info(f"Created pool session during refill: {session.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to create session during refill: {e}")
                        break  # Stop creating more if we hit an error
    
    async def _process_existing_files(self, session_config: SessionFileConfig, session_dir: str) -> List[str]:
        """Process existing files and return list of valid files."""
        downloaded_files = []
        existing_files = session_config.get_all_files()
        
        for file_id, filename in existing_files.items():
            file_path = os.path.join(session_dir, filename)
            if os.path.exists(file_path):
                downloaded_files.append(filename)
            else:
                # File was deleted, remove from config
                session_config.remove_file(file_id)
                logger.warning(f"File {file_id} was deleted from disk: {filename}")
        
        return downloaded_files
    
    async def _process_file_urls(self, file_urls: List[str], session_dir: str, timeout: int, downloaded_files: List[str]) -> List[str]:
        """Process legacy file URLs and return errors."""
        errors = []
        for url in file_urls:
            filename, error = await download_file(url, session_dir, timeout, verify_ssl=False)
            if error:
                errors.append(error)
            else:
                if filename not in downloaded_files:
                    downloaded_files.append(filename)
        return errors
    
    async def _process_files_with_id(self, files: List[FileItem], session_config: SessionFileConfig, 
                                   session_dir: str, timeout: int, downloaded_files: List[str]) -> List[str]:
        """Process files with ID management and return errors."""
        errors = []
        for file_item in files:
            file_id = file_item.id
            file_url = file_item.url
            
            # Check if file already exists
            if session_config.has_file(file_id):
                existing_filename = session_config.get_filename(file_id)
                file_path = os.path.join(session_dir, existing_filename)
                
                # Verify file still exists on disk
                if os.path.exists(file_path):
                    if existing_filename not in downloaded_files:
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
                if filename not in downloaded_files:
                    downloaded_files.append(filename)
                session_config.add_file(file_id, filename)
                logger.info(f"Downloaded new file {file_id}: {filename}")
        
        return errors
    
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
            files: List of files with URL and ID
            timeout: Download timeout in seconds
            
        Returns:
            Tuple of (session, downloaded_files, errors)
        """
        new_session_id = session_id or str(uuid.uuid4())
        session_dir = os.path.join('/tmp/sandbox_sessions', new_session_id)
        
        # Check if session already exists
        if session_id and session_id in self.sessions:
            existing_session = self.sessions[session_id]
            existing_session.update_activity()
            logger.info(f"Session {session_id} already exists, checking for new files to download")
            
            # Use existing session directory
            session_dir = existing_session.kernel_manager.cwd
            session_config = SessionFileConfig(session_dir)
            
            # Process existing files
            downloaded_files = await self._process_existing_files(session_config, session_dir)
            
            # Process new files
            errors = []
            if file_urls:
                errors.extend(await self._process_file_urls(file_urls, session_dir, timeout, downloaded_files))
            
            if files:
                errors.extend(await self._process_files_with_id(files, session_config, session_dir, timeout, downloaded_files))
            
            return existing_session, downloaded_files, errors
        
        # Create new session if it doesn't exist
        if len(self.sessions) >= settings.max_kernels:
            await self._cleanup_oldest_session()
        
        # Try to get a session from the pool first
        session = await self._get_session_from_pool()
        if session:
            # Reuse pooled session with new ID and directory
            old_session_id = session.session_id
            session.session_id = new_session_id
            
            # Update session directory
            os.makedirs(session_dir, exist_ok=True)
            session.kernel_manager.cwd = session_dir
            
            # Change the kernel's working directory and wait for completion
            if session.kernel_client:
                chdir_code = f"import os; os.chdir('{session_dir}')"
                msg_id = session.kernel_client.execute(chdir_code, silent=True)
                
                # Wait for the chdir command to complete
                while True:
                    reply = await asyncio.wait_for(
                        session.kernel_client.get_iopub_msg(),
                        timeout=0.5
                    )
                    if reply["msg_type"] == "status" and reply["content"].get("execution_state") == "idle":
                        break
             
            
            logger.info(f"Reused pooled session {old_session_id} as {new_session_id}, changed cwd to {session_dir}")
        else:
            # Create unique working directory for the session
            os.makedirs(session_dir, exist_ok=True)
            kernel_manager = AsyncKernelManager()
            kernel_manager.cwd = session_dir
            session = KernelSession(new_session_id, kernel_manager)
            
            logger.info(f"Created new session {new_session_id} (no pooled session available)")
        
        downloaded_files = []
        session_config = SessionFileConfig(session_dir)
        
        # Process files
        errors = []
        if file_urls:
            errors.extend(await self._process_file_urls(file_urls, session_dir, timeout, downloaded_files))
        
        if files:
            errors.extend(await self._process_files_with_id(files, session_config, session_dir, timeout, downloaded_files))
        
        try:
            # Only start the session if it's not from the pool (pooled sessions are already running)
            if session.session_id == new_session_id and not session.kernel_client:
                await session.start()
            
            self.sessions[new_session_id] = session
            logger.info(f"Session ready: {new_session_id} with cwd: {session_dir}")
            return session, downloaded_files, errors
        except Exception as e:
            logger.error(f"Failed to prepare kernel session: {e}")
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
            
            # Try to return to pool first, if that fails, stop the session
            if not await self._return_session_to_pool(oldest_session):
                await oldest_session.stop()
            
            logger.info(f"Removed oldest session: {oldest_session_id}")
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a specific session.
        
        Args:
            session_id: ID of the session to terminate
            
        Returns:
            True if session was found and terminated, False otherwise
        """
        if session_id not in self.sessions:
            return False
            
        session = self.sessions.pop(session_id)
        
        # Try to return to pool first, if that fails, stop the session
        if not await self._return_session_to_pool(session):
            await session.stop()
        
        logger.info(f"Terminated session: {session_id}")
        return True
    
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
    
    def get_session_detail(self, session_id: str) -> Optional[Dict]:
        """Get detailed information about a specific session including file list."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        session_dir = session.kernel_manager.cwd
        
        # Get file list from session config
        session_config = SessionFileConfig(session_dir)
        files_info = []
        
        for file_id, filename in session_config.get_all_files().items():
            file_path = os.path.join(session_dir, filename)
            file_exists = os.path.exists(file_path)
            file_size = os.path.getsize(file_path) if file_exists else 0
            
            files_info.append({
                "id": file_id,
                "filename": filename,
                "exists": file_exists,
                "size": file_size,
                "path": file_path
            })
        
        return {
            "session_id": session_id,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "is_busy": session.is_busy,
            "execution_count": session.execution_count,
            "working_directory": session_dir,
            "files": files_info,
            "total_files": len(files_info)
        }


# Global kernel manager instance
kernel_manager = KernelManagerService()