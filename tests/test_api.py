"""Tests for the API endpoints."""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from sandbox_mcp.main import create_app
from sandbox_mcp.config import settings


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_kernel_manager():
    """Mock kernel manager."""
    with patch('sandbox_mcp.api.kernel_manager') as mock:
        mock.sessions = {}
        mock.execute_code = AsyncMock()
        mock.get_session_info = lambda: {}
        yield mock


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns correct response."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "active_sessions" in data
        assert "uptime" in data


class TestExecuteEndpoint:
    """Test code execution endpoint."""
    
    def test_execute_simple_code(self, client, mock_kernel_manager):
        """Test executing simple Python code."""
        # Mock the async generator
        async def mock_execute(*args, **kwargs):
            from sandbox_mcp.models import StreamMessage, MessageType
            yield StreamMessage(
                type=MessageType.STREAM,
                content={"text": "Hello, World!\n"},
                timestamp=1234567890.0
            )
        
        mock_kernel_manager.execute_code.return_value = mock_execute()
        
        response = client.post(
            "/api/v1/execute",
            json={"code": "print('Hello, World!')"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson; charset=utf-8"
    
    def test_execute_missing_code(self, client):
        """Test execution with missing code field."""
        response = client.post("/api/v1/execute", json={})
        assert response.status_code == 422  # Validation error
    
    def test_execute_with_session_id(self, client, mock_kernel_manager):
        """Test execution with session ID."""
        async def mock_execute(*args, **kwargs):
            from sandbox_mcp.models import StreamMessage, MessageType
            yield StreamMessage(
                type=MessageType.STREAM,
                content={"text": "Hello from session!\n"},
                timestamp=1234567890.0
            )
        
        mock_kernel_manager.execute_code.return_value = mock_execute()
        
        response = client.post(
            "/api/v1/execute",
            json={
                "code": "print('Hello from session!')",
                "session_id": "test-session"
            }
        )
        
        assert response.status_code == 200
        mock_kernel_manager.execute_code.assert_called_once()


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def test_list_sessions_empty(self, client, mock_kernel_manager):
        """Test listing sessions when none exist."""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert data["sessions"] == {}
        assert data["total"] == 0
    
    def test_list_sessions_with_data(self, client, mock_kernel_manager):
        """Test listing sessions with active sessions."""
        mock_kernel_manager.get_session_info.return_value = {
            "session-1": {
                "created_at": 1234567890.0,
                "last_activity": 1234567900.0,
                "is_busy": False,
                "execution_count": 5
            }
        }
        
        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["total"] == 1
        assert "session-1" in data["sessions"]
    
    def test_terminate_nonexistent_session(self, client, mock_kernel_manager):
        """Test terminating a session that doesn't exist."""
        response = client.delete("/api/v1/sessions/nonexistent")
        assert response.status_code == 404
    
    def test_terminate_existing_session(self, client, mock_kernel_manager):
        """Test terminating an existing session."""
        # Mock session exists
        mock_session = AsyncMock()
        mock_kernel_manager.sessions = {"test-session": mock_session}
        
        response = client.delete("/api/v1/sessions/test-session")
        assert response.status_code == 200
        
        data = response.json()
        assert "terminated" in data["message"]
    
    def test_interrupt_nonexistent_session(self, client, mock_kernel_manager):
        """Test interrupting a session that doesn't exist."""
        response = client.post("/api/v1/sessions/nonexistent/interrupt")
        assert response.status_code == 404
    
    def test_interrupt_existing_session(self, client, mock_kernel_manager):
        """Test interrupting an existing session."""
        # Mock session exists
        mock_session = AsyncMock()
        mock_session.kernel_manager = AsyncMock()
        mock_kernel_manager.sessions = {"test-session": mock_session}
        
        response = client.post("/api/v1/sessions/test-session/interrupt")
        assert response.status_code == 200
        
        data = response.json()
        assert "interrupted" in data["message"]
        mock_session.kernel_manager.interrupt_kernel.assert_called_once()


class TestAuthentication:
    """Test API key authentication."""
    
    def test_no_auth_when_disabled(self, client):
        """Test that endpoints work without auth when API key is not set."""
        # Ensure API key is not set
        original_api_key = settings.api_key
        settings.api_key = None
        
        try:
            response = client.get("/api/v1/sessions")
            assert response.status_code == 200
        finally:
            settings.api_key = original_api_key
    
    def test_auth_required_when_enabled(self, client):
        """Test that auth is required when API key is set."""
        # Set API key
        original_api_key = settings.api_key
        settings.api_key = "test-key"
        
        try:
            response = client.get("/api/v1/sessions")
            assert response.status_code == 401
        finally:
            settings.api_key = original_api_key
    
    def test_valid_auth(self, client):
        """Test that valid API key allows access."""
        # Set API key
        original_api_key = settings.api_key
        settings.api_key = "test-key"
        
        try:
            response = client.get(
                "/api/v1/sessions",
                headers={"Authorization": "Bearer test-key"}
            )
            assert response.status_code == 200
        finally:
            settings.api_key = original_api_key
    
    def test_invalid_auth(self, client):
        """Test that invalid API key is rejected."""
        # Set API key
        original_api_key = settings.api_key
        settings.api_key = "test-key"
        
        try:
            response = client.get(
                "/api/v1/sessions",
                headers={"Authorization": "Bearer wrong-key"}
            )
            assert response.status_code == 401
        finally:
            settings.api_key = original_api_key