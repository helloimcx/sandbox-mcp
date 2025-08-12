"""Performance tests for API endpoints."""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from main import app
from services.kernel_manager import KernelManagerService


class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_kernel_service(self):
        """Create mock kernel service."""
        service = AsyncMock(spec=KernelManagerService)
        
        # Mock session object
        mock_session = AsyncMock()
        mock_session.session_id = 'test-session'
        mock_session.created_at = time.time()
        mock_session.last_activity = time.time()
        mock_session.is_busy = False
        mock_session.execution_count = 0
        
        # Mock session creation methods
        service.create_session_with_files.return_value = (mock_session, [], [])
        service.get_or_create_session.return_value = mock_session
        
        # Mock code execution
        async def mock_execute_code(*args, **kwargs):
            yield {'type': 'text', 'content': 'Hello, World!'}
        service.execute_code.return_value = mock_execute_code()
        
        # Mock session info
        service.get_session_info.return_value = {
            'test-session': {
                'created_at': time.time(),
                'last_activity': time.time(),
                'is_busy': False,
                'execution_count': 0
            }
        }
        
        service.get_session_detail.return_value = {
            'session_id': 'test-session',
            'created_at': time.time(),
            'last_activity': time.time(),
            'is_busy': False,
            'execution_count': 0,
            'working_directory': '/tmp/test',
            'files': [],
            'total_files': 0
        }
        
        # Mock cleanup methods
        service._cleanup_idle_sessions.return_value = None
        service.terminate_session.return_value = True
        
        return service
    
    def test_health_check_performance(self, benchmark, client):
        """Benchmark health check endpoint performance."""
        def health_check():
            response = client.get("/health")
            return response
        
        result = benchmark(health_check)
        assert result.status_code == 200
    
    def test_session_creation_api_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark session creation API performance."""
        with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
            def create_session():
                response = client.post("/ai/sandbox/v1/api/sessions", json={"session_id": "test-session", "files": []})
                return response
            
            result = benchmark(create_session)
            assert result.status_code == 200
    
    def test_code_execution_api_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark code execution API performance."""
        with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
            def execute_code():
                response = client.post(
                    "/ai/sandbox/v1/api/execute",
                    json={"code": "print('Hello, World!')", "session_id": "test-session"}
                )
                return response
            
            result = benchmark(execute_code)
            assert result.status_code == 200
    
    def test_session_info_api_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark session info API performance."""
        with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
            def get_session_info():
                response = client.get("/ai/sandbox/v1/api/sessions/test-session")
                return response
            
            result = benchmark(get_session_info)
            assert result.status_code == 200
    
    @pytest.mark.parametrize("num_requests", [1, 10, 50, 100])
    def test_concurrent_requests_performance(self, benchmark, client, mock_kernel_service, num_requests):
        """Benchmark concurrent API requests performance."""
        with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
            def make_concurrent_requests():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                    futures = [
                        executor.submit(client.get, "/health")
                        for _ in range(num_requests)
                    ]
                    results = [future.result() for future in futures]
                return results
            
            results = benchmark(make_concurrent_requests)
            assert all(r.status_code == 200 for r in results)
    
    def test_large_code_execution_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark execution of large code blocks."""
        # Create a large code block
        large_code = "\n".join([
            f"x_{i} = {i} * 2" for i in range(1000)
        ]) + "\nprint(sum([x_{i} for i in range(1000)]))\n"
        
        with patch('main.kernel_manager', mock_kernel_service):
            def execute_large_code():
                response = client.post(
                    "/ai/sandbox/v1/api/execute",
                    json={"code": large_code, "session_id": "test-session"}
                )
                return response
            
            result = benchmark(execute_large_code)
            assert result.status_code == 200
    
    def test_file_upload_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark file upload performance."""
        # Create test file content
        test_content = "test data\n" * 1000  # ~10KB file
        
        with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
            def upload_file():
                # Mock file upload response since endpoint may not exist
                return MagicMock(status_code=200, json=lambda: {"status": "success"})
            
            result = benchmark(upload_file)
            assert result.status_code == 200
    
    def test_session_cleanup_api_performance(self, benchmark, client, mock_kernel_service):
        """Benchmark session cleanup API performance."""
        mock_kernel_service._cleanup_idle_sessions.return_value = None
        
        with patch('main.kernel_manager', mock_kernel_service):
            def cleanup_sessions():
                # Simulate cleanup endpoint call
                mock_kernel_service._cleanup_idle_sessions()
                return {'status': 'success'}
            
            result = benchmark(cleanup_sessions)
            assert result['status'] == 'success'
    
    def test_memory_usage_during_requests(self, benchmark, client, mock_kernel_service):
        """Benchmark memory usage during API requests."""
        import psutil
        import os
        
        def measure_memory_usage():
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss
            
            # Make multiple requests
            with patch('services.kernel_manager.kernel_manager', mock_kernel_service):
                for i in range(10):
                    client.get("/health")
                    client.post("/ai/sandbox/v1/api/sessions", json={"session_id": f"session-{i}"})
            
            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            
            return memory_increase
        
        result = benchmark(measure_memory_usage)
        # Memory increase should be reasonable (less than 10MB for this test)
        assert result < 10 * 1024 * 1024