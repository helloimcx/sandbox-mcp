"""Tests for the kernel manager."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.kernel_manager import KernelSession, KernelManagerService
from schema.models import MessageType


class TestKernelSession:
    """Test KernelSession class."""
    
    @pytest.fixture
    def mock_kernel_manager(self):
        """Create mock kernel manager."""
        mock_km = AsyncMock()
        mock_km.start_kernel = AsyncMock()
        mock_km.shutdown_kernel = AsyncMock()
        mock_km.interrupt_kernel = AsyncMock()
        
        mock_client = AsyncMock()
        mock_client.start_channels = MagicMock()
        mock_client.stop_channels = MagicMock()
        mock_client.wait_for_ready = AsyncMock()
        mock_km.client = MagicMock(return_value=mock_client)
        
        return mock_km
    
    @pytest.mark.asyncio
    async def test_session_creation(self, mock_kernel_manager):
        """Test creating a kernel session."""
        session = KernelSession("test-session", mock_kernel_manager)
        
        assert session.session_id == "test-session"
        assert session.kernel_manager == mock_kernel_manager
        assert session.kernel_client is None
        assert session.execution_count == 0
        assert not session.is_busy
    
    @pytest.mark.asyncio
    async def test_session_start(self, mock_kernel_manager):
        """Test starting a kernel session."""
        session = KernelSession("test-session", mock_kernel_manager)
        
        await session.start()
        
        mock_kernel_manager.start_kernel.assert_called_once()
        mock_kernel_manager.client.assert_called_once()
        assert session.kernel_client is not None
        session.kernel_client.start_channels.assert_called_once()
        session.kernel_client.wait_for_ready.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_stop(self, mock_kernel_manager):
        """Test stopping a kernel session."""
        session = KernelSession("test-session", mock_kernel_manager)
        await session.start()
        
        await session.stop()
        
        session.kernel_client.stop_channels.assert_called_once()
        mock_kernel_manager.shutdown_kernel.assert_called_once()
    
    def test_update_activity(self, mock_kernel_manager):
        """Test updating session activity."""
        session = KernelSession("test-session", mock_kernel_manager)
        original_time = session.last_activity
        
        # Small delay to ensure time difference
        import time
        time.sleep(0.01)
        
        session.update_activity()
        assert session.last_activity > original_time
    
    def test_idle_timeout(self, mock_kernel_manager):
        """Test idle timeout detection."""
        session = KernelSession("test-session", mock_kernel_manager)
        
        # Fresh session should not be timed out
        assert not session.is_idle_timeout()
        
        # Manually set old timestamp
        session.last_activity = 0
        assert session.is_idle_timeout()


class TestKernelManagerService:
    """Test KernelManagerService class."""
    
    @pytest.fixture
    def service(self):
        """Create kernel manager service."""
        return KernelManagerService()
    
    @pytest.mark.asyncio
    async def test_service_start_stop(self, service):
        """Test starting and stopping the service."""
        await service.start()
        assert service._cleanup_task is not None
        assert not service._cleanup_task.done()
        
        await service.stop()
        assert service._cleanup_task.cancelled() or service._cleanup_task.done()
        assert len(service.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_create_session(self, service):
        """Test creating a new session."""
        with patch('sandbox_mcp.kernel_manager.AsyncKernelManager') as mock_km_class:
            mock_km = AsyncMock()
            mock_km_class.return_value = mock_km
            
            # Mock the session start method
            with patch.object(KernelSession, 'start', new_callable=AsyncMock) as mock_start:
                session = await service.get_or_create_session("test-session")
                
                assert session.session_id == "test-session"
                assert "test-session" in service.sessions
                mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reuse_existing_session(self, service):
        """Test reusing an existing session."""
        # Create a mock session
        mock_session = MagicMock()
        mock_session.update_activity = MagicMock()
        service.sessions["existing-session"] = mock_session
        
        session = await service.get_or_create_session("existing-session")
        
        assert session == mock_session
        mock_session.update_activity.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_code(self, service):
        """Test code execution."""
        # Mock session and kernel client
        mock_session = AsyncMock()
        mock_session.session_id = "test-session"
        mock_session.is_busy = False
        mock_session.execution_count = 0
        mock_session.update_activity = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.execute.return_value = "msg-id"
        mock_session.kernel_client = mock_client
        
        # Mock get_iopub_msg to return completion message
        async def mock_get_msg():
            return {
                "msg_type": "status",
                "content": {"execution_state": "idle"}
            }
        
        mock_client.get_iopub_msg = mock_get_msg
        
        with patch.object(service, 'get_or_create_session', return_value=mock_session):
            messages = []
            async for message in service.execute_code("print('test')", "test-session"):
                messages.append(message)
            
            assert len(messages) == 1
            assert messages[0].type == MessageType.STATUS
            assert mock_session.execution_count == 1
            assert not mock_session.is_busy
    
    @pytest.mark.asyncio
    async def test_execute_code_timeout(self, service):
        """Test code execution timeout."""
        mock_session = AsyncMock()
        mock_session.session_id = "test-session"
        mock_session.is_busy = False
        mock_session.execution_count = 0
        mock_session.update_activity = MagicMock()
        mock_session.kernel_manager = AsyncMock()
        
        mock_client = AsyncMock()
        mock_client.execute.return_value = "msg-id"
        mock_session.kernel_client = mock_client
        
        # Mock get_iopub_msg to timeout
        async def mock_get_msg():
            await asyncio.sleep(2)  # Longer than timeout
            return {"msg_type": "status", "content": {"execution_state": "idle"}}
        
        mock_client.get_iopub_msg = mock_get_msg
        
        with patch.object(service, 'get_or_create_session', return_value=mock_session):
            messages = []
            async for message in service.execute_code(
                "print('test')", "test-session", timeout=1
            ):
                messages.append(message)
            
            # Should get timeout error
            error_messages = [m for m in messages if m.type == MessageType.ERROR]
            assert len(error_messages) > 0
            assert "timeout" in error_messages[0].content["error"].lower()
    
    def test_get_session_info(self, service):
        """Test getting session information."""
        # Add mock sessions
        mock_session1 = MagicMock()
        mock_session1.created_at = 1234567890.0
        mock_session1.last_activity = 1234567900.0
        mock_session1.is_busy = False
        mock_session1.execution_count = 5
        
        mock_session2 = MagicMock()
        mock_session2.created_at = 1234567800.0
        mock_session2.last_activity = 1234567850.0
        mock_session2.is_busy = True
        mock_session2.execution_count = 2
        
        service.sessions = {
            "session1": mock_session1,
            "session2": mock_session2
        }
        
        info = service.get_session_info()
        
        assert len(info) == 2
        assert "session1" in info
        assert "session2" in info
        assert info["session1"]["execution_count"] == 5
        assert info["session2"]["is_busy"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_idle_sessions(self, service):
        """Test cleanup of idle sessions."""
        # Create mock sessions - one idle, one active
        idle_session = AsyncMock()
        idle_session.is_busy = False
        idle_session.is_idle_timeout.return_value = True
        idle_session.stop = AsyncMock()
        
        active_session = AsyncMock()
        active_session.is_busy = False
        active_session.is_idle_timeout.return_value = False
        
        service.sessions = {
            "idle-session": idle_session,
            "active-session": active_session
        }
        
        await service._cleanup_idle_sessions()
        
        # Idle session should be removed and stopped
        assert "idle-session" not in service.sessions
        assert "active-session" in service.sessions
        idle_session.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_oldest_session(self, service):
        """Test cleanup of oldest session when at capacity."""
        # Create mock sessions with different creation times
        old_session = AsyncMock()
        old_session.is_busy = False
        old_session.created_at = 1000.0
        old_session.stop = AsyncMock()
        
        new_session = AsyncMock()
        new_session.is_busy = False
        new_session.created_at = 2000.0
        
        busy_session = AsyncMock()
        busy_session.is_busy = True
        busy_session.created_at = 500.0  # Oldest but busy
        
        service.sessions = {
            "old-session": old_session,
            "new-session": new_session,
            "busy-session": busy_session
        }
        
        await service._cleanup_oldest_session()
        
        # Old idle session should be removed, busy session should remain
        assert "old-session" not in service.sessions
        assert "new-session" in service.sessions
        assert "busy-session" in service.sessions
        old_session.stop.assert_called_once()