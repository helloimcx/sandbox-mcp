"""Memory performance tests for the sandbox MCP server."""

import pytest
import asyncio
import time
import gc
import psutil
import os
from unittest.mock import AsyncMock, MagicMock, patch
from memory_profiler import profile, memory_usage
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.kernel_manager import KernelSession, KernelManagerService
from schema.models import MessageType


class TestMemoryPerformance:
    """Memory performance tests for core components."""
    
    @pytest.fixture
    def mock_kernel_manager(self):
        """Create mock kernel manager for memory testing."""
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
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def test_session_creation_memory_usage(self, mock_kernel_manager):
        """Test memory usage during session creation."""
        def create_sessions():
            sessions = []
            for i in range(100):
                session = KernelSession(f"session-{i}", mock_kernel_manager)
                sessions.append(session)
            return sessions
        
        # Measure memory usage
        initial_memory = self.get_memory_usage()
        sessions = create_sessions()
        final_memory = self.get_memory_usage()
        
        memory_increase = final_memory - initial_memory
        memory_per_session = memory_increase / 100
        
        print(f"Memory increase: {memory_increase:.2f} MB")
        print(f"Memory per session: {memory_per_session:.4f} MB")
        
        # Each session should use less than 1MB
        assert memory_per_session < 1.0
        
        # Clean up
        del sessions
        gc.collect()
    
    @pytest.mark.asyncio
    async def test_service_memory_usage_over_time(self, service):
        """Test memory usage of service over time with multiple operations."""
        def service_operations():
            # Simulate service operations
            sessions = {}
            
            # Create sessions
            for i in range(50):
                session_id = f"session-{i}"
                mock_session = MagicMock()
                mock_session.session_id = session_id
                mock_session.last_activity = time.time()
                mock_session.is_active = True
                sessions[session_id] = mock_session
            
            service.sessions = sessions
            
            # Simulate cleanup operations
            for _ in range(10):
                # Simulate session lookup
                for session_id in list(sessions.keys())[:10]:
                    _ = sessions.get(session_id)
                
                # Simulate cleanup
                current_time = time.time()
                idle_sessions = [
                    s for s in sessions.values()
                    if current_time - s.last_activity > 1800
                ]
            
            return len(sessions)
        
        # Use memory_profiler to track memory usage
        mem_usage = memory_usage((service_operations, ()))
        
        max_memory = max(mem_usage)
        min_memory = min(mem_usage)
        memory_variation = max_memory - min_memory
        
        print(f"Memory usage range: {min_memory:.2f} - {max_memory:.2f} MB")
        print(f"Memory variation: {memory_variation:.2f} MB")
        
        # Memory variation should be reasonable (less than 50MB)
        assert memory_variation < 50
    
    def test_memory_leak_detection(self, mock_kernel_manager):
        """Test for memory leaks during repeated operations."""
        def repeated_operations():
            for iteration in range(10):
                # Create and destroy sessions
                sessions = []
                for i in range(20):
                    session = KernelSession(f"session-{iteration}-{i}", mock_kernel_manager)
                    sessions.append(session)
                
                # Simulate some operations
                for session in sessions:
                    session.update_activity()
                
                # Clean up
                del sessions
                gc.collect()
        
        # Measure memory before and after
        initial_memory = self.get_memory_usage()
        repeated_operations()
        final_memory = self.get_memory_usage()
        
        memory_increase = final_memory - initial_memory
        
        print(f"Memory increase after repeated operations: {memory_increase:.2f} MB")
        
        # Memory increase should be minimal (less than 5MB)
        assert memory_increase < 5
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_memory_usage(self, service):
        """Test memory usage with concurrent sessions."""
        async def create_concurrent_sessions():
            tasks = []
            
            with patch('services.kernel_manager.AsyncKernelManager') as mock_km_class:
                mock_km = AsyncMock()
                mock_km.start_kernel = AsyncMock()
                mock_km.cwd = "/tmp/test_session"
                
                mock_client = AsyncMock()
                mock_client.start_channels = MagicMock()
                mock_client.wait_for_ready = AsyncMock()
                mock_client.execute = MagicMock(return_value="test_msg_id")
                
                mock_idle_msg = {
                    'msg_type': 'status',
                    'content': {'execution_state': 'idle'}
                }
                mock_client.get_iopub_msg = AsyncMock(return_value=mock_idle_msg)
                mock_km.client = MagicMock(return_value=mock_client)
                mock_km_class.return_value = mock_km
                
                # Create multiple concurrent sessions
                for i in range(20):
                    task = asyncio.create_task(
                        service.create_session(f"concurrent-session-{i}")
                    )
                    tasks.append(task)
                
                # Wait for all sessions to be created
                sessions = await asyncio.gather(*tasks)
                return sessions
        
        # Measure memory usage
        mem_usage = memory_usage((lambda: asyncio.run(create_concurrent_sessions()), ()))
        
        max_memory = max(mem_usage)
        min_memory = min(mem_usage)
        memory_increase = max_memory - min_memory
        
        print(f"Memory usage during concurrent session creation: {min_memory:.2f} - {max_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable for 20 sessions
        assert memory_increase < 100  # Less than 100MB for 20 sessions
    
    def test_large_data_processing_memory(self, mock_kernel_manager):
        """Test memory usage when processing large data structures."""
        def process_large_data():
            session = KernelSession("large-data-session", mock_kernel_manager)
            
            # Simulate large data processing
            large_data = {
                'data': list(range(100000)),  # 100k integers
                'metadata': {'key': 'value'} * 1000,  # Large metadata
                'results': [{'id': i, 'value': i * 2} for i in range(10000)]  # 10k results
            }
            
            # Simulate processing
            processed_data = {
                'summary': len(large_data['data']),
                'total': sum(large_data['data'][:1000]),  # Process subset
                'metadata_size': len(large_data['metadata'])
            }
            
            return processed_data
        
        # Measure memory usage
        mem_usage = memory_usage((process_large_data, ()))
        
        max_memory = max(mem_usage)
        min_memory = min(mem_usage)
        memory_increase = max_memory - min_memory
        
        print(f"Memory usage during large data processing: {min_memory:.2f} - {max_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable for large data processing
        assert memory_increase < 200  # Less than 200MB
    
    @profile
    def test_detailed_memory_profile(self, mock_kernel_manager):
        """Detailed memory profiling of session operations."""
        # Create multiple sessions
        sessions = []
        for i in range(50):
            session = KernelSession(f"profile-session-{i}", mock_kernel_manager)
            sessions.append(session)
        
        # Perform operations
        for session in sessions:
            session.update_activity()
            # Simulate some data storage
            session._test_data = list(range(1000))
        
        # Cleanup
        for session in sessions:
            if hasattr(session, '_test_data'):
                del session._test_data
        
        del sessions
        gc.collect()
    
    def test_memory_usage_with_errors(self, mock_kernel_manager):
        """Test memory usage when handling errors."""
        def operations_with_errors():
            sessions = []
            
            for i in range(30):
                try:
                    session = KernelSession(f"error-session-{i}", mock_kernel_manager)
                    sessions.append(session)
                    
                    # Simulate error condition
                    if i % 5 == 0:
                        raise Exception(f"Simulated error for session {i}")
                        
                except Exception as e:
                    # Handle error
                    print(f"Handled error: {e}")
                    continue
            
            return len(sessions)
        
        # Measure memory usage
        initial_memory = self.get_memory_usage()
        result = operations_with_errors()
        final_memory = self.get_memory_usage()
        
        memory_increase = final_memory - initial_memory
        
        print(f"Created {result} sessions with error handling")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable even with errors
        assert memory_increase < 30
    
    def test_garbage_collection_effectiveness(self, mock_kernel_manager):
        """Test effectiveness of garbage collection."""
        def create_and_destroy_sessions():
            for cycle in range(5):
                # Create sessions
                sessions = []
                for i in range(20):
                    session = KernelSession(f"gc-session-{cycle}-{i}", mock_kernel_manager)
                    # Add some data to make sessions heavier
                    session._test_data = [list(range(1000)) for _ in range(10)]
                    sessions.append(session)
                
                # Destroy sessions
                del sessions
                
                # Force garbage collection
                collected = gc.collect()
                print(f"Cycle {cycle}: Collected {collected} objects")
        
        # Measure memory before and after
        initial_memory = self.get_memory_usage()
        create_and_destroy_sessions()
        
        # Force final garbage collection
        gc.collect()
        final_memory = self.get_memory_usage()
        
        memory_increase = final_memory - initial_memory
        
        print(f"Memory increase after GC cycles: {memory_increase:.2f} MB")
        
        # Memory should return close to initial level after GC
        assert memory_increase < 10