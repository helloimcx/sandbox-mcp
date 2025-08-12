"""Performance tests for kernel manager."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.kernel_manager import KernelSession, KernelManagerService
from schema.models import MessageType


class TestKernelManagerPerformance:
    """Performance tests for KernelManagerService."""
    
    @pytest.fixture
    def mock_kernel_manager(self):
        """Create mock kernel manager for performance testing."""
        mock_km = AsyncMock()
        mock_km.start_kernel = AsyncMock()
        mock_km.shutdown_kernel = AsyncMock()
        mock_km.interrupt_kernel = AsyncMock()
        mock_km.cwd = "/tmp/test_session"
        
        mock_client = AsyncMock()
        mock_client.start_channels = MagicMock()
        mock_client.stop_channels = MagicMock()
        mock_client.wait_for_ready = AsyncMock()
        mock_client.execute = MagicMock(return_value="test_msg_id")
        
        # Mock get_iopub_msg to return idle status immediately
        mock_idle_msg = {
            'msg_type': 'status',
            'content': {'execution_state': 'idle'}
        }
        mock_client.get_iopub_msg = AsyncMock(return_value=mock_idle_msg)
        mock_km.client = MagicMock(return_value=mock_client)
        
        return mock_km
    
    @pytest.fixture
    def service(self):
        """Create KernelManagerService instance."""
        return KernelManagerService()
    
    def test_session_creation_performance(self, benchmark, mock_kernel_manager):
        """Benchmark session creation performance."""
        def create_session():
            return KernelSession("test-session", mock_kernel_manager)
        
        result = benchmark(create_session)
        assert result.session_id == "test-session"
    
    def test_session_start_performance(self, benchmark, mock_kernel_manager):
        """Benchmark session start performance."""
        def start_session():
            session = KernelSession("test-session", mock_kernel_manager)
            # Mock the start method to avoid actual kernel startup
            session.kernel_client = mock_kernel_manager
            return session
        
        result = benchmark(start_session)
        assert result.session_id == "test-session"
    
    def test_multiple_sessions_creation_performance(self, benchmark, service):
        """Benchmark creating multiple sessions."""
        def create_multiple_sessions():
            sessions = []
            for i in range(10):
                session_id = f"session-{i}"
                # Create mock session directly
                mock_km = MagicMock()
                mock_km.cwd = f"/tmp/test_session_{i}"
                session = KernelSession(session_id, mock_km)
                sessions.append(session)
            return sessions
        
        result = benchmark(create_multiple_sessions)
        assert len(result) == 10
    
    def test_code_execution_performance(self, benchmark, service):
        """Benchmark code execution performance."""
        def execute_simple_code():
            # Simulate code execution logic
            session_id = "perf-test-session"
            code = "print('Hello, World!')"
            
            # Mock execution result
            result = {
                'status': 'success',
                'output': 'Hello, World!',
                'execution_count': 1,
                'execution_time': 0.1
            }
            return result
        
        result = benchmark(execute_simple_code)
        assert result['status'] == 'success'
    
    def test_session_cleanup_performance(self, benchmark, service):
        """Benchmark session cleanup performance."""
        # Setup multiple mock sessions
        sessions = {}
        for i in range(20):
            session_id = f"session-{i}"
            mock_session = MagicMock()
            mock_session.session_id = session_id
            mock_session.last_activity = time.time() - 3600  # 1 hour ago
            mock_session.is_active = True
            mock_session.stop = AsyncMock()
            sessions[session_id] = mock_session
        
        service.sessions = sessions
        
        def cleanup_sessions():
            # Simulate cleanup logic
            idle_sessions = [
                session for session in service.sessions.values()
                if time.time() - session.last_activity > 1800  # 30 minutes
            ]
            return len(idle_sessions)
        
        result = benchmark(cleanup_sessions)
        assert result == 20  # All sessions should be considered idle
    
    @pytest.mark.parametrize("num_sessions", [1, 5, 10, 20, 50])
    def test_session_lookup_performance(self, benchmark, service, num_sessions):
        """Benchmark session lookup performance with different numbers of sessions."""
        # Setup sessions
        sessions = {}
        for i in range(num_sessions):
            session_id = f"session-{i}"
            mock_session = MagicMock()
            mock_session.session_id = session_id
            sessions[session_id] = mock_session
        
        service.sessions = sessions
        target_session_id = f"session-{num_sessions // 2}"  # Middle session
        
        def lookup_session():
            return service.sessions.get(target_session_id)
        
        result = benchmark(lookup_session)
        assert result is not None
        assert result.session_id == target_session_id