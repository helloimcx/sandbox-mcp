import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from main import create_app
from config.config import settings

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_kernel_manager():
    with patch('services.kernel_manager.kernel_manager') as mock:
        mock.sessions = {}
        async def mock_execute_code(*args, **kwargs):
            from schema.models import StreamMessage, MessageType
            yield StreamMessage(type=MessageType.STREAM, content={'text': 'hello'}, timestamp=0)
        mock.execute_code = mock_execute_code
        mock.get_session_info = lambda: {}
        yield mock

class TestHealth:
    def test_health(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'active_sessions' in data
        assert 'uptime' in data

class TestExecute:
    def test_execute_code(self, client, mock_kernel_manager):
        async def mock_execute(*args, **kwargs):
            from schema.models import StreamMessage, MessageType
            yield StreamMessage(type=MessageType.STREAM, content={'text': 'hello'}, timestamp=0)
        mock_kernel_manager.execute_code.return_value = mock_execute()
        resp = client.post('/ai/sandbox/v1/api/execute', json={'code': "print('hello')"})
        assert resp.status_code == 200
        assert resp.headers['content-type'].startswith('application/x-ndjson')

    def test_execute_missing_code(self, client):
        resp = client.post('/ai/sandbox/v1/api/execute', json={})
        assert resp.status_code == 422

class TestSessions:
    def test_list_sessions_empty(self, client, mock_kernel_manager):
        resp = client.get('/ai/sandbox/v1/api/sessions')
        assert resp.status_code == 200
        data = resp.json()
        assert data['sessions'] == {}
        assert data['total'] == 0

    def test_terminate_nonexistent(self, client, mock_kernel_manager):
        resp = client.delete('/ai/sandbox/v1/api/sessions/none')
        assert resp.status_code == 404

class TestAuth:
    def test_no_auth(self, client):
        orig = settings.api_key
        settings.api_key = None
        try:
            resp = client.get('/ai/sandbox/v1/api/sessions')
            assert resp.status_code == 200
        finally:
            settings.api_key = orig

    def test_auth_required(self, client):
        orig = settings.api_key
        settings.api_key = 'test-key'
        try:
            resp = client.get('/ai/sandbox/v1/api/sessions')
            assert resp.status_code == 401
        finally:
            settings.api_key = orig

    def test_valid_auth(self, client):
        orig = settings.api_key
        settings.api_key = 'test-key'
        try:
            resp = client.get('/ai/sandbox/v1/api/sessions', headers={'Authorization': 'Bearer test-key'})
            assert resp.status_code == 200
        finally:
            settings.api_key = orig

    def test_invalid_auth(self, client):
        orig = settings.api_key
        settings.api_key = 'test-key'
        try:
            resp = client.get('/ai/sandbox/v1/api/sessions', headers={'Authorization': 'Bearer wrong-key'})
            assert resp.status_code == 401
        finally:
            settings.api_key = orig
